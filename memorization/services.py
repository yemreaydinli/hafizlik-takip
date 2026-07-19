from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from .models import MemorizationPage


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
        result.append({"page_number": page.page_number, "days_waiting": days_waiting})
    return result
