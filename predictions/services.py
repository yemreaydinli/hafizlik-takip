"""
Akıllı Tahmin Motoru
=====================
Cüz/Tur/Pişmiş sistemine geçiş sonrası GÜNCELLENDİ.

ESKİ DAVRANIŞ (artık geçerli değil): Sadece "ham" (yeni ezber) hızına bakıp
604 sayfanın ilk kez ne zaman ezberleneceğini tahmin ediyordu. Bu, gerçek
hafızlığı DEĞİL, sadece ilk geçişin bitişini gösteriyordu -- bir sayfa has
(tekrar) ile "pişmeden" hafız sayılmaz.

YENİ DAVRANIŞ: İki ayrı hat izlenir ve tahmini bitiş, bu iki hattan GEÇ
olanına göre belirlenir (bkz. calculate_prediction docstring'i):
  1) Ham hattı: 604 sayfanın tamamının en az bir kez ezberlenmesi.
  2) Has hattı: 604 sayfanın tamamının has ile "pişmiş" (MemorizationPage.
     Status.COMPLETED) hale gelmesi.
"""
import statistics
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from core.quran import TOTAL_JUZ
from memorization.models import MemorizationPage
from lessons.models import PerformanceHistory
from .models import PredictionHistory


def _ema(values, alpha, seed_window=5):
    """
    Üstel Hareketli Ortalama. Tek bir ilk değerle başlamak yerine ilk birkaç günün
    ortalamasıyla ('seed') başlar; böylece basit ortalamadan EMA'ya geçiş daha
    pürüzsüz ve tek bir uç değere karşı daha dayanıklı olur.
    """
    if not values:
        return 0.0
    seed_count = min(seed_window, len(values))
    ema_value = sum(values[:seed_count]) / seed_count
    for v in values[seed_count:]:
        ema_value = alpha * v + (1 - alpha) * ema_value
    return ema_value


def _pace(values, use_simple_average, alpha):
    """Sıfır olmayan günlük değerlerden tek bir 'günlük hız' üretir (ham ve has
    için aynı mantıkla, ayrı ayrı çağrılır). Veri yoksa 0 döner."""
    if not values:
        return 0.0
    if use_simple_average:
        return sum(values) / len(values)
    return _ema(values, alpha)


def _coefficient_of_variation(values):
    if len(values) < 2:
        return None
    try:
        mean = statistics.mean(values)
        if not mean:
            return None
        return statistics.pstdev(values) / mean
    except statistics.StatisticsError:
        return None


def _confidence_level(sample_count, has_sample_count, memorization_values, revision_values):
    """
    GÜNCELLENDİ: Artık sadece ham verisinin değil, has (tekrar) verisinin de
    yeterliliğine ve tutarlılığına bakar. Cüz/Tur sistemine geçtikten sonra
    asıl darboğaz genelde has tarafı olduğu için, has verisi az/düzensizken
    yüksek güven vermek yanıltıcı olurdu (bkz. calculate_prediction).
    """
    if sample_count < 7 or has_sample_count < 3:
        return PredictionHistory.Confidence.LOW
    if sample_count < 20 or has_sample_count < 7:
        return PredictionHistory.Confidence.MEDIUM

    ham_cv = _coefficient_of_variation(memorization_values)
    has_cv = _coefficient_of_variation(revision_values)
    cvs = [cv for cv in (ham_cv, has_cv) if cv is not None]
    if not cvs:
        return PredictionHistory.Confidence.MEDIUM
    return PredictionHistory.Confidence.HIGH if max(cvs) < 0.6 else PredictionHistory.Confidence.MEDIUM


def calculate_prediction(student, persist=True):
    """
    Öğrenci için tahmini HAFIZLIK bitiş tarihini hesaplar.

    Bir sayfanın sadece HAM'ı okunması onu "bitmiş" yapmaz -- gerçek hafızlık,
    sayfanın HAS (tekrar) ile "pişmiş" hale gelmesini gerektirir (bkz.
    memorization/models.py:MemorizationPage.Status.COMPLETED,
    lessons/signals.py:recompute_student_memorization). Bu yüzden algoritma
    İKİ AYRI hat izler:

      1) Ham hattı: 604 sayfanın tamamının en az bir kez ezberlenmesi
         (status NEEDS_REVISION veya COMPLETED).
      2) Has hattı: 604 sayfanın tamamının has ile "pişmiş" olması
         (status COMPLETED -- yani her sayfayı kapsayan en az bir
         RevisionRecord girilmiş olması).

    Bir sayfa has ile pişmeden önce ham'ı yapılmış olmalıdır. Bu yüzden:
      - Ham zaten bittiyse (remaining_ham_pages == 0): tahmin doğrudan has
        hattının hızına göre yapılır.
      - Ham henüz bitmediyse: ham hattının bitiş süresine, "son turun
        pişmesi" için bir tampon eklenir (ortalama bir cüzün -- 604/30 sayfa
        -- has hızıyla pişme süresi). Nihai tahmin, bu iki hattan (has hattı
        tek başına vs. ham+tampon) GEÇ olanıdır -- öğrenci hangi tarafta
        gerçekten geride kalıyorsa tahmini o belirler.

    'Tur' hedefi olarak şu an her sayfanın en az BİR kez pişmesi (has
    verilmesi) yeterli sayılıyor (MemorizationPage.Status.COMPLETED ile
    birebir eşleşir). Kursunuzun usulü daha fazla tur gerektiriyorsa,
    JuzTurCount.tur_count üzerinden bir hedef tur sayısı eklenerek bu eşik
    kolayca genelleştirilebilir -- şu an için bu MVP eşiği hiçbir yeni alan
    gerektirmiyor.

    Dönüş: PredictionHistory instance (kaydedilmiş veya kaydedilmemiş) ya da
    None (öğrenci hem ham hem has'ı tamamladıysa -- yani gerçekten hafızsa --
    ya da hiç veri yoksa).
    """
    total_pages = settings.TOTAL_QURAN_PAGES
    today = timezone.localdate()

    pages_qs = MemorizationPage.objects.filter(student=student)
    ham_done = pages_qs.exclude(status=MemorizationPage.Status.NOT_STUDIED).count()
    has_done = pages_qs.filter(status=MemorizationPage.Status.COMPLETED).count()

    remaining_ham_pages = max(total_pages - ham_done, 0)
    remaining_has_pages = max(total_pages - has_done, 0)

    if remaining_has_pages == 0:
        # Hem ham hem has tamamlanmış: öğrenci gerçekten hafız.
        return None

    history_qs = PerformanceHistory.objects.filter(student=student).order_by("date")
    history = list(history_qs)

    if not history:
        return None

    # ÖNEMLİ: Isınma dönemi (basit ortalama → EMA geçişi) öğrencinin GERÇEK hafızlığa
    # başlama tarihine göre değil, sisteme ders kaydı girilmeye BAŞLANDIĞI tarihe göre
    # hesaplanır. Aksi halde önceden ilerlemiş (örn. 2 yıldır hafız olan) bir öğrenci
    # sisteme yeni eklendiğinde, "start_date" çok eskide kaldığı için sistem onu yanlışlıkla
    # ısınma dönemini çoktan bitirmiş sayar ve sadece birkaç günlük veriyle EMA'ya geçer.
    # Bu da yepyeni bir öğrenciyle (tam 30 gün basit ortalama alan) tutarsızlık yaratır.
    tracking_start_date = history[0].date
    days_tracked = max((today - tracking_start_date).days, 1)

    attended_days = [h for h in history if h.attended]
    attendance_rate = len(attended_days) / len(history) if history else 1
    attendance_rate = max(attendance_rate, 0.2)  # aşırı düşük tahminleri engellemek için taban

    memorization_values = [h.daily_memorization for h in history if h.daily_memorization > 0]
    revision_values = [h.daily_revision for h in history if h.daily_revision > 0]

    use_simple_average = days_tracked <= settings.PREDICTION_SIMPLE_AVG_DAYS or len(history) < 5
    method = PredictionHistory.Method.SIMPLE_AVERAGE if use_simple_average else PredictionHistory.Method.EMA

    ham_pace = _pace(memorization_values, use_simple_average, settings.PREDICTION_EMA_ALPHA)
    has_pace = _pace(revision_values, use_simple_average, settings.PREDICTION_EMA_ALPHA)

    effective_ham_pace = ham_pace * attendance_rate
    effective_has_pace = has_pace * attendance_rate

    # Son turun pişmesi için tampon: ham bittiğinde geriye "pişmemiş" kalacak
    # son kısmın (yaklaşık bir cüz büyüklüğünde) has'ının verilmesi için gereken
    # ek süre. Sabit "30 gün" yerine gerçek ortalama cüz boyutu kullanılır.
    avg_juz_pages = total_pages / TOTAL_JUZ

    tracks = {}
    if effective_has_pace > 0:
        tracks[PredictionHistory.Bottleneck.HAS] = remaining_has_pages / effective_has_pace
    if remaining_ham_pages > 0 and effective_ham_pace > 0:
        ham_days = remaining_ham_pages / effective_ham_pace
        if effective_has_pace > 0:
            ham_days += avg_juz_pages / effective_has_pace
        tracks[PredictionHistory.Bottleneck.HAM] = ham_days

    if tracks:
        bottleneck_phase, total_remaining_days = max(tracks.items(), key=lambda item: item[1])
        estimated_remaining_days = int(round(total_remaining_days))
        estimated_completion_date = today + timedelta(days=estimated_remaining_days)
        legacy_daily_pace = (
            effective_ham_pace if bottleneck_phase == PredictionHistory.Bottleneck.HAM else effective_has_pace
        )
    else:
        # Ne ham ne has için pace verisi var (örn. öğrenci hiç has almamış VE
        # ham hızı da 0) -- güvenilir bir tahmin üretilemez.
        bottleneck_phase = ""
        estimated_remaining_days = None
        estimated_completion_date = None
        legacy_daily_pace = 0.0

    confidence = _confidence_level(len(history), len(revision_values), memorization_values, revision_values)

    defaults = {
        "estimated_completion_date": estimated_completion_date,
        "estimated_remaining_days": estimated_remaining_days,
        "confidence_level": confidence,
        "method_used": method,
        "remaining_pages": remaining_has_pages,
        "daily_pace": round(legacy_daily_pace, 2),
        "remaining_ham_pages": remaining_ham_pages,
        "remaining_has_pages": remaining_has_pages,
        "ham_daily_pace": round(effective_ham_pace, 2),
        "has_daily_pace": round(effective_has_pace, 2),
        "bottleneck_phase": bottleneck_phase,
    }

    if persist:
        # Aynı gün içinde (örn. öğrenci sayfası birden çok kez açıldığında) her seferinde
        # yeni bir PredictionHistory satırı oluşturmak yerine, o güne ait kaydı güncelle.
        # Böylece "history" tablosu günlük bazda anlamlı kalır ve
        # PredictionHistory.Meta.ordering = ["-calculated_date"] (gün hassasiyetli)
        # ile student.predictions.first() her zaman deterministik biçimde en güncel
        # (bugünkü) tahmini döner -- aynı güne ait birden fazla satır arasında
        # belirsiz bir sıralamaya düşmez.
        prediction, _ = PredictionHistory.objects.update_or_create(
            student=student, calculated_date=today, defaults=defaults,
        )
    else:
        prediction = PredictionHistory(student=student, calculated_date=today, **defaults)
    return prediction


def calculate_target_progress(student):
    """
    Hedef bitiş tarihine göre "bugün itibarıyla olması gereken" sayfa sayısı ile
    gerçek ezberlenen (completed + needs_revision) sayfa sayısını karşılaştırır.

    calculate_prediction()'dan farkı: o fonksiyon geçmiş temponun ORTALAMASINI alıp
    ileriye dönük bir tahmin üretir (gün bazlı sapma verir). Bu fonksiyon ise haftalık
    ders temposu dalgalı olsa bile (bazı hafta 2 sayfa/1 cüz, bazı hafta 5 sayfa gibi)
    doğru çalışır; çünkü "olması gereken"i haftalık ortalamaya değil, başlangıçtan
    bugüne GEÇEN SÜRENİN ORANINA göre hesaplar. Böylece dalgalanmalara karşı dayanıklı,
    sayfa/yüzde bazlı bir "yolunda mı gidiyor" göstergesi elde edilir.

    Dönüş: dict ya da None (hedef tarih ya da başlangıç tarihi tanımlı değilse).
    """
    from core.quran import juz_of_page

    if not student.target_completion_date or not student.start_date:
        return None

    total_days = (student.target_completion_date - student.start_date).days
    if total_days <= 0:
        return None

    total_pages = settings.TOTAL_QURAN_PAGES
    today = timezone.localdate()

    elapsed_days = max(0, min((today - student.start_date).days, total_days))
    expected_pages_by_now = round(total_pages * elapsed_days / total_days)

    actual_pages = MemorizationPage.objects.filter(student=student).exclude(
        status=MemorizationPage.Status.NOT_STUDIED
    ).count()

    pages_ahead_behind = actual_pages - expected_pages_by_now
    if expected_pages_by_now > 0:
        target_progress_percent = round((actual_pages / expected_pages_by_now) * 100, 1)
    else:
        # Henüz hedef sürecin başındayız (elapsed_days == 0); beklenen 0 sayfa,
        # yapılan her sayfa hedefin önünde sayılır.
        target_progress_percent = 100.0 if actual_pages == 0 else 200.0

    remaining_pages = max(total_pages - actual_pages, 0)
    remaining_days = (student.target_completion_date - today).days
    remaining_weeks = remaining_days / 7 if remaining_days > 0 else 0
    required_weekly_pace = round(remaining_pages / remaining_weeks, 1) if remaining_weeks > 0 else None

    return {
        "expected_pages_by_now": expected_pages_by_now,
        "expected_juz_by_now": juz_of_page(expected_pages_by_now) if expected_pages_by_now > 0 else 0,
        "actual_pages": actual_pages,
        "pages_ahead_behind": pages_ahead_behind,
        "pages_ahead_behind_abs": abs(pages_ahead_behind),
        "target_progress_percent": target_progress_percent,
        "remaining_pages": remaining_pages,
        "remaining_days": max(remaining_days, 0),
        "required_weekly_pace": required_weekly_pace,
        "target_date_passed": remaining_days <= 0 and remaining_pages > 0,
    }
