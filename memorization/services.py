from django.conf import settings
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
