from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from predictions.services import calculate_prediction
from students.models import Student
from .models import MemorizationPage
from .services import get_page_map, get_progress_summary, bulk_apply_range


class MemorizationMapView(LoginRequiredMixin, View):
    def _get_student(self, request, student_pk):
        if request.user.is_admin_role:
            return get_object_or_404(Student, pk=student_pk)
        return get_object_or_404(Student, pk=student_pk, teacher=request.user)

    def get(self, request, student_pk):
        student = self._get_student(request, student_pk)
        context = {
            "student": student,
            "page_map": get_page_map(student),
            "summary": get_progress_summary(student),
            "status_choices": MemorizationPage.Status.choices,
        }
        return render(request, "memorization/map.html", context)

    def post(self, request, student_pk):
        """Başlangıç Durumu Aktarımı: sisteme kayıttan önce ezberlenmiş/tekrar edilmiş
        sayfa aralıklarını toplu olarak işaretler. Böylece Akıllı Tahmin Motoru
        'kalan sayfa' hesabını öğrencinin gerçek mevcut durumuna göre yapar."""
        student = self._get_student(request, student_pk)
        try:
            start_page = int(request.POST.get("start_page"))
            end_page = int(request.POST.get("end_page"))
            status = request.POST.get("status")
        except (TypeError, ValueError):
            messages.error(request, "Geçerli bir sayfa aralığı girin.")
            return redirect(reverse("memorization:map", kwargs={"student_pk": student.pk}))

        valid_statuses = dict(MemorizationPage.Status.choices)
        if status not in valid_statuses or not (1 <= start_page <= 604 and 1 <= end_page <= 604):
            messages.error(request, "Geçersiz sayfa aralığı veya durum.")
            return redirect(reverse("memorization:map", kwargs={"student_pk": student.pk}))

        updated = bulk_apply_range(student, start_page, end_page, status)
        # Tahmin motorunu güncel duruma göre yeniden hesapla.
        calculate_prediction(student, persist=True)
        messages.success(request, f"{updated} sayfa '{valid_statuses[status]}' olarak güncellendi.")
        return redirect(reverse("memorization:map", kwargs={"student_pk": student.pk}))
