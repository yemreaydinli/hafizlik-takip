from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .forms import StyledAuthenticationForm, TeacherCreateForm
from .models import User


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    next_page = "accounts:login"


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin_role


class TeacherListView(AdminRequiredMixin, ListView):
    model = User
    template_name = "accounts/teacher_list.html"
    context_object_name = "teachers"

    def get_queryset(self):
        return User.objects.filter(role=User.Role.TEACHER).order_by("first_name", "last_name")


class TeacherCreateView(AdminRequiredMixin, CreateView):
    model = User
    form_class = TeacherCreateForm
    template_name = "accounts/teacher_form.html"
    success_url = reverse_lazy("accounts:teacher_list")

    def form_valid(self, form):
        messages.success(self.request, "Öğretici hesabı oluşturuldu.")
        return super().form_valid(form)


class TeacherUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    fields = ["first_name", "last_name", "email", "phone", "is_active"]
    template_name = "accounts/teacher_form.html"
    success_url = reverse_lazy("accounts:teacher_list")

    def form_valid(self, form):
        messages.success(self.request, "Öğretici bilgileri güncellendi.")
        return super().form_valid(form)


class TeacherDeleteView(AdminRequiredMixin, DeleteView):
    model = User
    template_name = "accounts/teacher_confirm_delete.html"
    success_url = reverse_lazy("accounts:teacher_list")

    def form_valid(self, form):
        messages.success(self.request, "Öğretici hesabı silindi.")
        return super().form_valid(form)
