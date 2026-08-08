from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from core.quran import TOTAL_JUZ, juz_page_range
from predictions.services import calculate_prediction
from students.models import Student
from .models import MemorizationPage, JuzTurCount
from .services import get_juz_map, get_progress_summary, bulk_apply_range


class MemorizationMapView(LoginRequiredMixin, View):
    def _get_student(self, request, student_pk):
        if request.user.is_admin_role:
            return get_object_or_404(Student, pk=student_pk)
        return get_object_or_404(Student, pk=student_pk, teacher=request.user)

    def get(self, request, student_pk):
        student = self._get_student(request, student_pk)
        context = {
            "student": student,
            "juz_map": get_juz_map(student),
            "summary": get_progress_summary(student),
            "status_choices": MemorizationPage.Status.choices,
            "total_juz": TOTAL_JUZ,
        }
        return render(request, "memorization/map.html", context)

    def post(self, request, student_pk):
        """Başlangıç Durumu Aktarımı: sisteme kayıttan önce ezberlenmiş/tekrar edilmiş
        cüzleri toplu olarak işaretler. Böylece Akıllı Tahmin Motoru
        'kalan sayfa' hesabını öğrencinin gerçek mevcut durumuna göre yapar."""
        student = self._get_student(request, student_pk)
        try:
            start_juz = int(request.POST.get("start_juz"))
            end_juz = int(request.POST.get("end_juz"))
            status = request.POST.get("status")
        except (TypeError, ValueError):
            messages.error(request, "Geçerli bir cüz aralığı girin.")
            return redirect(reverse("memorization:map", kwargs={"student_pk": student.pk}))

        valid_statuses = dict(MemorizationPage.Status.choices)
        if status not in valid_statuses or not (1 <= start_juz <= TOTAL_JUZ and 1 <= end_juz <= TOTAL_JUZ):
            messages.error(request, "Geçersiz cüz aralığı veya durum.")
            return redirect(reverse("memorization:map", kwargs={"student_pk": student.pk}))

        start_juz, end_juz = min(start_juz, end_juz), max(start_juz, end_juz)
        start_page, _ = juz_page_range(start_juz)
        _, end_page = juz_page_range(end_juz)

        updated = bulk_apply_range(student, start_page, end_page, status)

        # Bu cüz aralığı için has tekrar sayacını (JuzTurCount) da elle güncelle.
        # synced_from_lessons=False olarak işaretlenir ki lessons/signals.py:_sync_juz_tur_counts
        # bu manuel değeri, o cüz için gerçek bir ders/Has kaydı girilmeden ÜZERİNE YAZMASIN
        # (bkz. memorization/models.py:JuzTurCount.synced_from_lessons).
        today = timezone.localdate()
        for juz_number in range(start_juz, end_juz + 1):
            tur, _ = JuzTurCount.objects.get_or_create(student=student, juz_number=juz_number)
            if status == MemorizationPage.Status.COMPLETED:
                if tur.tur_count < 1:
                    tur.tur_count = 1
                    tur.last_tur_date = tur.last_tur_date or today
            else:
                # 'Tekrar Gerekiyor' veya 'Çalışılmadı (sıfırla)' seçildiğinde, bu cüz artık
                # baştan sona tamamlanmış sayılmadığından elle konmuş has tekrar rozeti de kaldırılır.
                tur.tur_count = 0
                tur.last_tur_date = None
            tur.synced_from_lessons = False
            tur.save()

        # Tahmin motorunu güncel duruma göre yeniden hesapla.
        calculate_prediction(student, persist=True)
        messages.success(
            request,
            f"{start_juz}. Cüz - {end_juz}. Cüz arası ({updated} sayfa) '{valid_statuses[status]}' olarak güncellendi.",
        )
        return redirect(reverse("memorization:map", kwargs={"student_pk": student.pk}))
