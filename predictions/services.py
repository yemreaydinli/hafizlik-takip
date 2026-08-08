"""
Akıllı Tahmin Motoru
=====================
İlk PREDICTION_SIMPLE_AVG_DAYS gün boyunca basit ortalama, sonrasında
Üstel Hareketli Ortalama (EMA) kullanarak öğrencinin hafızlığı tamamlama
tarihini tahmin eder.
"""
import statistics
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

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


def _confidence_level(sample_count, values):
    if sample_count < 7:
        return PredictionHistory.Confidence.LOW
    if sample_count < 20:
        return PredictionHistory.Confidence.MEDIUM
    try:
        cv = statistics.pstdev(values) / (statistics.mean(values) or 1)
    except statistics.StatisticsError:
        return PredictionHistory.Confidence.MEDIUM
    return PredictionHistory.Confidence.HIGH if cv < 0.6 else PredictionHistory.Confidence.MEDIUM


def calculate_prediction(student, persist=True):
    """
    Öğrenci için tahmini bitiş tarihini hesaplar.
    Dönüş: PredictionHistory instance (kaydedilmiş veya kaydedilmemiş) ya da None
    (öğrenci hafızlığını tamamladıysa ya da hiç veri yoksa).
    """
    total_pages = settings.TOTAL_QURAN_PAGES
    memorized = MemorizationPage.objects.filter(student=student).exclude(
        status=MemorizationPage.Status.NOT_STUDIED
    ).count()
    remaining_pages = max(total_pages - memorized, 0)

    today = timezone.localdate()

    if remaining_pages == 0:
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

    use_simple_average = days_tracked <= settings.PREDICTION_SIMPLE_AVG_DAYS or len(history) < 5

    if use_simple_average:
        method = PredictionHistory.Method.SIMPLE_AVERAGE
        pace_per_active_day = (sum(memorization_values) / len(memorization_values)) if memorization_values else 0
    else:
        method = PredictionHistory.Method.EMA
        pace_per_active_day = _ema(memorization_values, settings.PREDICTION_EMA_ALPHA) if memorization_values else 0

    effective_daily_pace = pace_per_active_day * attendance_rate

    if effective_daily_pace <= 0:
        estimated_completion_date = None
        estimated_remaining_days = None
    else:
        estimated_remaining_days = int(round(remaining_pages / effective_daily_pace))
        estimated_completion_date = today + timedelta(days=estimated_remaining_days)

    confidence = _confidence_level(len(history), memorization_values)

    if persist:
        # Aynı gün içinde (örn. öğrenci sayfası birden çok kez açıldığında) her seferinde
        # yeni bir PredictionHistory satırı oluşturmak yerine, o güne ait kaydı güncelle.
        # Böylece "history" tablosu günlük bazda anlamlı kalır ve
        # PredictionHistory.Meta.ordering = ["-calculated_date"] (gün hassasiyetli)
        # ile student.predictions.first() her zaman deterministik biçimde en güncel
        # (bugünkü) tahmini döner -- aynı güne ait birden fazla satır arasında
        # belirsiz bir sıralamaya düşmez.
        prediction, _ = PredictionHistory.objects.update_or_create(
            student=student,
            calculated_date=today,
            defaults={
                "estimated_completion_date": estimated_completion_date,
                "estimated_remaining_days": estimated_remaining_days,
                "confidence_level": confidence,
                "method_used": method,
                "remaining_pages": remaining_pages,
                "daily_pace": round(effective_daily_pace, 2),
            },
        )
    else:
        prediction = PredictionHistory(
            student=student,
            calculated_date=today,
            estimated_completion_date=estimated_completion_date,
            estimated_remaining_days=estimated_remaining_days,
            confidence_level=confidence,
            method_used=method,
            remaining_pages=remaining_pages,
            daily_pace=round(effective_daily_pace, 2),
        )
    return prediction
