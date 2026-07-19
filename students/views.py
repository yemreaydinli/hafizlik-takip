from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from lessons.models import LessonRecord
from memorization.services import get_progress_summary
from notifications.models import Notification
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
    model = Student
    template_name = "students/detail.html"
    context_object_name = "student"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        student = self.object
        ctx["lessons"] = LessonRecord.objects.filter(student=student).order_by("-date")[:15]
        ctx["progress"] = get_progress_summary(student)
        ctx["notifications"] = Notification.objects.filter(student=student, is_read=False)[:5]
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
