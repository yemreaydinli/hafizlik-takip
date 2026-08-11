from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from core.quran import TOTAL_JUZ, juz_page_range, juz_of_page, absolute_to_local_page, juz_page_count
from .models import MemorizationPage, JuzTurCount


def get_page_map(student):
    """
    Öğrencinin 604 sayfalık hafızlık haritasını döndürür.
    Henüz DB kaydı olmayan sayfalar 'gray' (çalışılmadı) kabul edilir.
    """
    total_pages = settings.TOTAL_QURAN_PAGES
    existing = {p.page_number: p for p in MemorizationPage.objects.filter(student=student)}

    page_map = []
    for page_no in range(1, total_pages + 1):
        page = existing.get(page_no)
        status = page.status if page else MemorizationPage.Status.NOT_STUDIED
        page_map.append({"page_number": page_no, "status": status})
    return page_map


def get_juz_map(student):
    """
    Öğrencinin 30 cüzlük hafızlık haritasını döndürür. Her cüz için:
    - status: cüzün genel durumu (tamamı yeşilse yeşil, hiç çalışılmadıysa gri, aksi halde sarı)
    - tur_count: o cüzün kaçıncı kez tekrar (has) edildiği
    - progress_percent: cüz içinde tamamlanan sayfa yüzdesi
    """
    pages = {p.page_number: p for p in MemorizationPage.objects.filter(student=student)}
    turs = {t.juz_number: t for t in JuzTurCount.objects.filter(student=student)}

    juz_map = []
    for juz_number in range(1, TOTAL_JUZ + 1):
        start, end = juz_page_range(juz_number)
        statuses = [
            pages[p].status if p in pages else MemorizationPage.Status.NOT_STUDIED
            for p in range(start, end + 1)
        ]
        total_in_juz = len(statuses)
        completed = statuses.count(MemorizationPage.Status.COMPLETED)
        started = sum(1 for s in statuses if s != MemorizationPage.Status.NOT_STUDIED)

        if total_in_juz and completed == total_in_juz:
            juz_status = MemorizationPage.Status.COMPLETED
        elif started > 0:
            juz_status = MemorizationPage.Status.NEEDS_REVISION
        else:
            juz_status = MemorizationPage.Status.NOT_STUDIED

        tur = turs.get(juz_number)
        juz_map.append({
            "juz_number": juz_number,
            "status": juz_status,
            "tur_count": tur.tur_count if tur else 0,
            "last_tur_date": tur.last_tur_date if tur else None,
            "page_range": f"{start}-{end}",
            "progress_percent": round((completed / total_in_juz) * 100, 1) if total_in_juz else 0,
        })
    return juz_map


def get_juz_progress_summary(student):
    """Cüz bazında özet: kaç cüz tamamlandı, kaç cüz tekrar bekliyor, kaç cüz hiç çalışılmadı."""
    juz_map = get_juz_map(student)
    completed = sum(1 for j in juz_map if j["status"] == MemorizationPage.Status.COMPLETED)
    needs_revision = sum(1 for j in juz_map if j["status"] == MemorizationPage.Status.NEEDS_REVISION)
    return {
        "total_juz": TOTAL_JUZ,
        "completed_juz": completed,
        "needs_revision_juz": needs_revision,
        "not_studied_juz": TOTAL_JUZ - completed - needs_revision,
    }


def is_juz_ham_covered(student, juz_number, extra_ranges=(), exclude_lesson_id=None):
    """
    Bir cüzün TÜM sayfalarının en az bir kez ham (yeni ezber) olarak ders
    kaydına girilip girilmediğini kontrol eder.

    NEDEN: Has (tekrar) girişi kullanıcı arayüzünde tek bir cüz seçilerek
    yapılıyor (bkz. lessons/forms.py:RevisionRecordForm) -- bu, cüzün TAMAMININ
    o oturumda tekrar edildiğini varsayar. Bu varsayımın kendisi doğru ve
    değiştirilmedi (has gerçekten tek seferde, tam cüz olarak veriliyor).
    Ancak bu formda hiçbir kontrol olmadan hoca YANLIŞLIKLA (örn. açılır
    listeden yanlış cüzü seçerek) henüz ham'ı hiç/tam yapılmamış bir cüzü
    "tekrar edildi" olarak işaretleyebilir. Bunun sonucu sessiz ama ciddidir:
    lessons/signals.py:recompute_student_memorization() bu durumda ilgili
    sayfaları ham hiç yapılmamış olsa bile doğrudan COMPLETED (pişmiş/yeşil)
    işaretler -- hem Hafızlık Haritası hem JuzTurCount hem de Akıllı Tahmin
    Motoru'nun "kalan ham/has sayfa" sayıları bozulur. Bu fonksiyon, "tek cüz
    has verme" arayüzünü DEĞİŞTİRMEDEN, kaydetmeden önce bu tutarsızlığı
    yakalayıp engellemek için kullanılır (bkz. lessons/views.py).

    extra_ranges: henüz veritabanına kaydedilmemiş, aynı form gönderiminde
    girilen ek ham aralıkları -- (mutlak_başlangıç, mutlak_bitiş) çiftleri.
    Böylece "bu dersin ham'ı + bu dersteki has aynı cüz" gibi tek oturumluk
    girişler de doğru değerlendirilir.

    exclude_lesson_id: bir ders kaydı DÜZENLENİRKEN, o dersin veritabanındaki
    ESKİ (henüz kaydedilmemiş değişiklikten önceki) ham aralığının iki kez
    sayılmasını/yanıltmasını önlemek için o dersin id'si dışarıda bırakılır;
    güncel değeri zaten extra_ranges ile ayrıca geçirilmelidir.
    """
    start, end = juz_page_range(juz_number)
    covered = set()

    from lessons.models import LessonRecord

    qs = LessonRecord.objects.filter(
        student=student, ham_start_page__isnull=False, ham_end_page__isnull=False,
        ham_start_page__lte=end, ham_end_page__gte=start,
    )
    if exclude_lesson_id:
        qs = qs.exclude(pk=exclude_lesson_id)
    qs = qs.values_list("ham_start_page", "ham_end_page")

    for h_start, h_end in qs:
        for page_no in range(max(h_start, start), min(h_end, end) + 1):
            covered.add(page_no)

    for extra in extra_ranges:
        if not extra:
            continue
        e_start, e_end = extra
        if e_start is None or e_end is None:
            continue
        for page_no in range(max(e_start, start), min(e_end, end) + 1):
            covered.add(page_no)

    return len(covered) == (end - start + 1)


def get_juz_next_ham_pages(student):
    """
    Her cüz için, öğrencinin o cüzde daha önce ham (yeni ezber) olarak verilmiş
    en son (en ileri) yerel sayfasına bakarak bir sonraki ders için önerilen
    başlangıç/bitiş sayfasını (cüz içi yerel sayfa numarası) hesaplar.

    Örn: öğrenciye bu cüzden daha önce en son 16. sayfaya kadar ders verilmişse,
    önerilen sayfa 17'dir. Bu fonksiyon salt bir ÖNERİDİR; hoca formda dilediği
    gibi değiştirebilir, sistem hiçbir şeyi zorunlu kılmaz.

    Dönüş: {juz_number: {"suggested_page": int|None, "last_local_page": int|None}}
    - suggested_page None ise: cüzün tamamı (1..juz_page_count) zaten ham olarak
      verilmiş demektir; yeni sayfa önerilecek bir şey kalmamıştır (sadece has/tekrar
      girilebilir).
    """
    from lessons.models import LessonRecord

    furthest_local = {}
    lessons = LessonRecord.objects.filter(
        student=student, ham_start_page__isnull=False, ham_end_page__isnull=False
    ).values("ham_start_page", "ham_end_page")
    for l in lessons:
        j = juz_of_page(l["ham_start_page"])
        if not j:
            continue
        local_end = absolute_to_local_page(l["ham_end_page"])
        if local_end is None:
            continue
        if j not in furthest_local or local_end > furthest_local[j]:
            furthest_local[j] = local_end

    suggestions = {}
    for juz_number in range(1, TOTAL_JUZ + 1):
        max_local = juz_page_count(juz_number)
        last_local = furthest_local.get(juz_number)
        if last_local is None:
            suggestions[juz_number] = {"suggested_page": 1, "last_local_page": None}
        elif last_local >= max_local:
            suggestions[juz_number] = {"suggested_page": None, "last_local_page": last_local}
        else:
            suggestions[juz_number] = {"suggested_page": last_local + 1, "last_local_page": last_local}
    return suggestions


def bulk_apply_range(student, start_page, end_page, status):
    """
    Bir sayfa aralığını topluca belirli bir duruma getirir.
    Özellikle öğrenci sisteme kaydedilmeden ÖNCE zaten ezberlemiş olduğu sayfaları
    (Başlangıç Durumu Aktarımı) tek seferde işaretlemek için kullanılır; bu sayede
    Akıllı Tahmin Motoru "kalan sayfa" hesabını gerçek duruma göre yapar.
    """
    today = timezone.localdate()
    start_page, end_page = min(start_page, end_page), max(start_page, end_page)
    updated = 0
    for page_no in range(start_page, end_page + 1):
        page, _ = MemorizationPage.objects.get_or_create(student=student, page_number=page_no)
        page.status = status
        # Elle (ders kaydı olmadan) yapılan bu atama, ders senkronizasyonu tarafından
        # geri alınmamalı/sıfırlanmamalıdır -- bkz. lessons/signals.py:recompute_student_memorization
        page.synced_from_lessons = False
        if status == MemorizationPage.Status.COMPLETED:
            page.last_revised_date = page.last_revised_date or today
            page.first_memorized_date = page.first_memorized_date or today
            page.revision_count = max(page.revision_count, 1)
        elif status == MemorizationPage.Status.NEEDS_REVISION:
            page.first_memorized_date = page.first_memorized_date or today
        page.save()
        updated += 1
    return updated


def get_progress_summary(student):
    qs = MemorizationPage.objects.filter(student=student)
    completed = qs.filter(status=MemorizationPage.Status.COMPLETED).count()
    needs_revision = qs.filter(status=MemorizationPage.Status.NEEDS_REVISION).count()
    total = settings.TOTAL_QURAN_PAGES
    memorized = completed + needs_revision
    return {
        "total_pages": total,
        "completed": completed,
        "needs_revision": needs_revision,
        "not_studied": total - memorized,
        "memorized_total": memorized,
        "progress_percent": round((memorized / total) * 100, 1) if total else 0,
    }


def get_stale_pages(student, days_threshold=14, limit=10):
    """
    Ezberlendiği halde uzun süredir hiç tekrar edilmemiş (durumu hâlâ 'sarı' olan)
    sayfaları döndürür. Öğretmenin "buraya odaklan" diyebileceği risk listesidir.
    """
    today = timezone.localdate()
    cutoff = today - timedelta(days=days_threshold)
    stale = (
        MemorizationPage.objects.filter(
            student=student,
            status=MemorizationPage.Status.NEEDS_REVISION,
            first_memorized_date__lte=cutoff,
        )
        .order_by("first_memorized_date")[:limit]
    )
    result = []
    for page in stale:
        days_waiting = (today - page.first_memorized_date).days if page.first_memorized_date else None
        result.append({
            "page_number": page.page_number,
            "juz_number": juz_of_page(page.page_number),
            "days_waiting": days_waiting,
        })
    return result
