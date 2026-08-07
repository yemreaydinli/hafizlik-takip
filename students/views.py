import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from lessons.models import LessonRecord
from lessons.services import get_attendance_summary, get_recent_performance_series
from memorization.services import get_progress_summary, get_juz_map, get_stale_pages
from notifications.models import Notification
from predictions.services import calculate_prediction
from .forms import StudentForm
from .models import Student


class StudentScopedMixin(LoginRequiredMixin):
    def get_queryset(self):
        qs = Student.objects.all()
        if not self.request.user.is_admin_role:
            qs = qs.filter(teacher=self.request.user)
        return qs


class StudentListView(StudentScopedMixin, ListView):
    model = Student
    template_name = "students/list.html"
    context_object_name = "students"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.GET.get("q")
        status = self.request.GET.get("status")
        if query:
            qs = qs.filter(Q(full_name__icontains=query) | Q(phone__icontains=query))
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Student.Status.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["query"] = self.request.GET.get("q", "")
        return ctx


class StudentDetailView(StudentScopedMixin, DetailView):
    """
    Öğrenci Genel Bakış sayfası: ilerleme, tahmin, devam istatistikleri,
    performans grafiği, zayıf (uzun süredir tekrar bekleyen) sayfalar ve
    ders/uyarı zaman çizelgesini tek ekranda birleştirir.
    """
    model = Student
    template_name = "students/detail.html"
    context_object_name = "student"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        student = self.object

        recent_lessons = list(LessonRecord.objects.filter(student=student).order_by("-date")[:15])
        recent_notifications = list(Notification.objects.filter(student=student).order_by("-created_at")[:10])

        # Ders kayıtları ve uyarıları tek bir zaman çizelgesinde birleştir.
        timeline = []
        for lesson in recent_lessons[:10]:
            timeline.append({
                "date": lesson.date,
                "kind": "lesson",
                "attendance": lesson.attendance,
                "ham": lesson.ham_page_count,
                "ham_juz_label": lesson.ham_juz_label,
                "revision": lesson.revision_page_count,
                "revision_juz_labels": lesson.revision_juz_labels,
                "quality": lesson.get_quality_display() if lesson.quality else None,
                "notes": lesson.notes,
            })
        for n in recent_notifications:
            timeline.append({
                "date": n.created_at.date(),
                "kind": "alert",
                "type_label": n.get_type_display(),
                "message": n.message,
            })
        timeline.sort(key=lambda x: x["date"], reverse=True)

        prediction = calculate_prediction(student, persist=True)
        target_deviation_days = None
        target_deviation_abs = None
        if prediction and prediction.estimated_completion_date and student.target_completion_date:
            target_deviation_days = (prediction.estimated_completion_date - student.target_completion_date).days
            target_deviation_abs = abs(target_deviation_days)

        performance_series = get_recent_performance_series(student, days=30)

        ctx.update({
            "lessons": recent_lessons,
            "progress": get_progress_summary(student),
            "notifications": Notification.objects.filter(student=student, is_read=False)[:5],
            "attendance": get_attendance_summary(student),
            "prediction": prediction,
            "target_deviation_days": target_deviation_days,
            "target_deviation_abs": target_deviation_abs,
            "mini_juz_map": get_juz_map(student),
            "stale_pages": get_stale_pages(student),
            "performance_series_json": json.dumps(performance_series, cls=DjangoJSONEncoder),
            "timeline": timeline[:12],
        })
        return ctx


class StudentCreateView(StudentScopedMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = "students/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if self.request.user.is_admin_role:
            form.instance.teacher = form.cleaned_data["teacher"]
        else:
            form.instance.teacher = self.request.user
        messages.success(self.request, "Öğrenci eklendi.")
        return super().form_valid(form)


class StudentUpdateView(StudentScopedMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = "students/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if self.request.user.is_admin_role and "teacher" in form.cleaned_data:
            form.instance.teacher = form.cleaned_data["teacher"]
        messages.success(self.request, "Öğrenci bilgileri güncellendi.")
        return super().form_valid(form)


class StudentDeleteView(StudentScopedMixin, DeleteView):
    model = Student
    template_name = "students/confirm_delete.html"
    success_url = reverse_lazy("students:list")

    def form_valid(self, form):
        messages.success(self.request, "Öğrenci kaydı silindi.")
        return super().form_valid(form)
