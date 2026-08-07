from collections import defaultdict

from django.db.models import Count, Max
from django.db.models.signals import post_delete
from django.dispatch import receiver

from core.quran import TOTAL_JUZ, juz_page_range
from .models import LessonRecord, PerformanceHistory
from memorization.models import MemorizationPage, RevisionRecord, JuzTurCount


def recompute_student_memorization(student):
    """
    Öğrencinin TÜM ders (LessonRecord) ve tekrar (RevisionRecord) geçmişinden,
    'synced_from_lessons=True' olan sayfaların durumunu SIFIRDAN yeniden hesaplar.

    Bu fonksiyon idempotenttir: art arda kaç kez çağrılırsa çağrılsın aynı (doğru)
    sonucu üretir. Böylece:
      - Bir ders kaydı silindiğinde veya düzenlenip ham/tekrar aralığı daraltıldığında,
        artık hiçbir ders tarafından kapsanmayan sayfalar otomatik olarak eski
        durumuna (gri/sarı) döner -- eskiden bu geri alma hiç yapılmıyordu.
      - revision_count, tek bir olayı iki kez saymak yerine, o sayfayı kapsayan
        FARKLI ders tarihlerinin sayısı olarak hesaplanır -- eskiden her çağrıda
        +1 arttığı için aynı düzenleme birden fazla kez sayılabiliyordu.

    'synced_from_lessons=False' olan (memorization.services.bulk_apply_range ile
    elle "Başlangıç Durumu Aktarımı" yapılmış) sayfalara dokunulmaz.
    """
    lessons = list(
        LessonRecord.objects.filter(student=student).prefetch_related("revision_ranges")
    )

    ham_first_date = {}
    revision_dates = defaultdict(set)

    for lesson in lessons:
        if lesson.ham_start_page and lesson.ham_end_page:
            for page_no in range(lesson.ham_start_page, lesson.ham_end_page + 1):
                if page_no not in ham_first_date or lesson.date < ham_first_date[page_no]:
                    ham_first_date[page_no] = lesson.date
        for rev in lesson.revision_ranges.all():
            for page_no in range(rev.start_page, rev.end_page + 1):
                revision_dates[page_no].add(lesson.date)

    touched_pages = set(ham_first_date) | set(revision_dates)

    lesson_synced_existing = {
        p.page_number: p
        for p in MemorizationPage.objects.filter(student=student, synced_from_lessons=True)
    }

    for page_no in touched_pages:
        page = lesson_synced_existing.get(page_no) or MemorizationPage.objects.filter(
            student=student, page_number=page_no
        ).first() or MemorizationPage(student=student, page_number=page_no)

        page.synced_from_lessons = True
        if page_no in revision_dates:
            dates = revision_dates[page_no]
            page.status = MemorizationPage.Status.COMPLETED
            page.last_revised_date = max(dates)
            page.revision_count = len(dates)
            page.first_memorized_date = ham_first_date.get(page_no) or min(dates)
        else:
            page.status = MemorizationPage.Status.NEEDS_REVISION
            page.first_memorized_date = ham_first_date[page_no]
            page.last_revised_date = None
            page.revision_count = 0
        page.save()

    # Artık hiçbir ders/tekrar tarafından kapsanmayan (ders silinmiş/aralık daraltılmış)
    # ama daha önce ders senkronizasyonuyla işaretlenmiş sayfaları eski (gri) hale döndür.
    stale_page_numbers = set(lesson_synced_existing) - touched_pages
    if stale_page_numbers:
        MemorizationPage.objects.filter(
            student=student, page_number__in=stale_page_numbers, synced_from_lessons=True
        ).update(
            status=MemorizationPage.Status.NOT_STUDIED,
            first_memorized_date=None,
            last_revised_date=None,
            revision_count=0,
        )


def _sync_juz_tur_counts(student):
    """
    Öğrencinin 30 cüzü için 'has tekrar' sayaçlarını (bir cüzün kaçıncı kez has
    olarak tekrar edildiği -- HAM'daki yeni ezber turlarıyla karıştırılmamalıdır)
    RevisionRecord kayıtlarından yeniden hesaplar. Sayaç, o cüz için tam aralığı
    (start_page/end_page cüz sınırlarıyla birebir eşleşen) kapsayan farklı ders
    tarihlerinin sayısıdır; bu fonksiyon her çağrıldığında sıfırdan yeniden
    hesaplandığı (idempotent) için ders kaydı düzenleme/silme durumunda çift
    sayım oluşmaz.
    """
    for juz_number in range(1, TOTAL_JUZ + 1):
        start, end = juz_page_range(juz_number)
        agg = (
            RevisionRecord.objects.filter(
                lesson__student=student, start_page=start, end_page=end
            ).aggregate(cnt=Count("lesson_id", distinct=True), last=Max("lesson__date"))
        )
        if agg["cnt"]:
            JuzTurCount.objects.update_or_create(
                student=student, juz_number=juz_number,
                defaults={"tur_count": agg["cnt"], "last_tur_date": agg["last"]},
            )
        else:
            JuzTurCount.objects.filter(student=student, juz_number=juz_number).update(tur_count=0, last_tur_date=None)


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
    """
    Ders kaydı VE bağlı tekrar (has) formseti kaydedildikten SONRA bir kez
    çağrılması gereken genel senkronizasyon fonksiyonu.

    ÖNEMLİ: Bu fonksiyon kasıtlı olarak bir Django sinyaline (post_save) bağlı
    DEĞİLDİR. Sebep: LessonRecord kaydedilirken bağlı RevisionRecord formseti
    henüz kaydedilmemiş olur (bkz. lessons/views.py -- form.save() formset.save()'den
    önce çalışır). Sinyal kullanılsaydı, sync eksik/eski tekrar verisiyle bir kez,
    sonra formset kaydedilince tekrar (view içinde elle) çağrılması gerekirdi --
    bu da örn. revision_count gibi alanların her düzenlemede çift sayılmasına yol
    açıyordu. Bu yüzden sync_lesson SADECE ilgili view'larda, formset.save()'den
    SONRA çağrılmalıdır.
    """
    recompute_student_memorization(lesson.student)
    _sync_juz_tur_counts(lesson.student)
    _sync_performance_history(lesson)


@receiver(post_delete, sender=LessonRecord)
def on_lesson_record_deleted(sender, instance: LessonRecord, **kwargs):
    PerformanceHistory.objects.filter(student=instance.student, date=instance.date).delete()
    # Silinen dersin kapsadığı sayfalar artık hiçbir ders tarafından desteklenmiyorsa
    # Hafızlık Haritası'nda eski (gri/sarı) durumuna otomatik döner.
    recompute_student_memorization(instance.student)
    _sync_juz_tur_counts(instance.student)
