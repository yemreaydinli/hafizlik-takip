from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from students.models import Student
from .services import get_page_map, get_progress_summary


class MemorizationMapView(LoginRequiredMixin, View):
    def get(self, request, student_pk):
        if request.user.is_admin_role:
            student = get_object_or_404(Student, pk=student_pk)
        else:
            student = get_object_or_404(Student, pk=student_pk, teacher=request.user)

        context = {
            "student": student,
            "page_map": get_page_map(student),
            "summary": get_progress_summary(student),
        }
        return render(request, "memorization/map.html", context)
