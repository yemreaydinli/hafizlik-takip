from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import LessonRecord, PerformanceHistory
from memorization.models import MemorizationPage, RevisionRecord


def _sync_memorization_pages(lesson: LessonRecord):
    """Ham (yeni ezber) aralığındaki sayfaları 'sarı' (tekrar bekliyor) yapar."""
    if lesson.ham_start_page and lesson.ham_end_page:
        for page_no in range(lesson.ham_start_page, lesson.ham_end_page + 1):
            page, _ = MemorizationPage.objects.get_or_create(
                student=lesson.student, page_number=page_no
            )
            if page.status == MemorizationPage.Status.NOT_STUDIED:
                page.status = MemorizationPage.Status.NEEDS_REVISION
                page.first_memorized_date = lesson.date
                page.save(update_fields=["status", "first_memorized_date", "updated_at"])

    # Tekrar edilen (has) sayfaları 'yeşil' (tamamlandı) yapar.
    for rev in lesson.revision_ranges.all():
        for page_no in range(rev.start_page, rev.end_page + 1):
            page, _ = MemorizationPage.objects.get_or_create(
                student=lesson.student, page_number=page_no
            )
            page.status = MemorizationPage.Status.COMPLETED
            page.last_revised_date = lesson.date
            page.revision_count = page.revision_count + 1
            page.save(update_fields=["status", "last_revised_date", "revision_count", "updated_at"])


def _sync_performance_history(lesson: LessonRecord):
    cumulative = MemorizationPage.objects.filter(
        student=lesson.student
    ).exclude(status=MemorizationPage.Status.NOT_STUDIED).count()

    PerformanceHistory.objects.update_or_create(
        student=lesson.student,
        date=lesson.date,
        defaults={
            "daily_memorization": lesson.ham_page_count,
            "daily_revision": lesson.revision_page_count,
            "quality_score": lesson.quality_score,
            "attended": lesson.attendance == LessonRecord.Attendance.PRESENT,
            "cumulative_memorized_pages": cumulative,
        },
    )


def sync_lesson(lesson: LessonRecord):
    """Ders kaydı ve bağlı tekrar formseti kaydedildikten sonra çağrılabilecek genel senkronizasyon fonksiyonu."""
    _sync_memorization_pages(lesson)
    _sync_performance_history(lesson)


@receiver(post_save, sender=LessonRecord)
def on_lesson_record_saved(sender, instance: LessonRecord, **kwargs):
    sync_lesson(instance)


@receiver(post_delete, sender=LessonRecord)
def on_lesson_record_deleted(sender, instance: LessonRecord, **kwargs):
    PerformanceHistory.objects.filter(student=instance.student, date=instance.date).delete()
