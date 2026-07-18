from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import ListView

from students.models import Student
from .forms import LessonRecordForm, RevisionRecordFormSet
from .models import LessonRecord
from .signals import sync_lesson


def _scoped_students(user):
    if user.is_admin_role:
        return Student.objects.all()
    return Student.objects.filter(teacher=user)


class LessonListView(LoginRequiredMixin, ListView):
    model = LessonRecord
    template_name = "lessons/list.html"
    context_object_name = "lessons"
    paginate_by = 25

    def get_queryset(self):
        qs = LessonRecord.objects.select_related("student").filter(
            student__in=_scoped_students(self.request.user)
        )
        student_id = self.request.GET.get("student")
        if student_id:
            qs = qs.filter(student_id=student_id)
        return qs


def lesson_create(request, student_pk):
    student = get_object_or_404(_scoped_students(request.user), pk=student_pk)
    instance = LessonRecord(student=student, created_by=request.user)

    if request.method == "POST":
        form = LessonRecordForm(request.POST, instance=instance)
        if form.is_valid():
            lesson = form.save()
            formset = RevisionRecordFormSet(request.POST, instance=lesson)
            if formset.is_valid():
                formset.save()
                sync_lesson(lesson)
                messages.success(request, "Günlük ders kaydı eklendi.")
                return redirect(reverse("students:detail", kwargs={"pk": student.pk}))
        else:
            formset = RevisionRecordFormSet(request.POST, instance=instance)
    else:
        form = LessonRecordForm(instance=instance, initial={"date": None})
        formset = RevisionRecordFormSet(instance=instance)

    return render(request, "lessons/form.html", {
        "form": form, "formset": formset, "student": student,
    })


def lesson_update(request, pk):
    lesson = get_object_or_404(
        LessonRecord.objects.select_related("student"), pk=pk, student__in=_scoped_students(request.user)
    )
    if request.method == "POST":
        form = LessonRecordForm(request.POST, instance=lesson)
        formset = RevisionRecordFormSet(request.POST, instance=lesson)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            sync_lesson(lesson)
            messages.success(request, "Ders kaydı güncellendi.")
            return redirect(reverse("students:detail", kwargs={"pk": lesson.student.pk}))
    else:
        form = LessonRecordForm(instance=lesson)
        formset = RevisionRecordFormSet(instance=lesson)

    return render(request, "lessons/form.html", {
        "form": form, "formset": formset, "student": lesson.student, "lesson": lesson,
    })


def lesson_delete(request, pk):
    lesson = get_object_or_404(LessonRecord, pk=pk, student__in=_scoped_students(request.user))
    student_pk = lesson.student.pk
    if request.method == "POST":
        lesson.delete()
        messages.success(request, "Ders kaydı silindi.")
        return redirect(reverse("students:detail", kwargs={"pk": student_pk}))
    return render(request, "lessons/confirm_delete.html", {"lesson": lesson})
