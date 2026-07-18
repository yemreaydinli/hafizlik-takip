from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from students.models import Student
from .services import calculate_prediction
from .models import PredictionHistory


class PredictionDetailView(LoginRequiredMixin, View):
    def get(self, request, student_pk):
        if request.user.is_admin_role:
            student = get_object_or_404(Student, pk=student_pk)
        else:
            student = get_object_or_404(Student, pk=student_pk, teacher=request.user)

        prediction = calculate_prediction(student, persist=True)
        history = student.predictions.all()[:10]

        return render(request, "predictions/detail.html", {
            "student": student,
            "prediction": prediction,
            "history": history,
        })
