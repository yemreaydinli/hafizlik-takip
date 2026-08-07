import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import ListView

from core.quran import TOTAL_JUZ, juz_page_count
from students.models import Student
from .forms import LessonRecordForm, RevisionRecordFormSet
from .models import LessonRecord
from .signals import sync_lesson


def _scoped_students(user):
    if user.is_admin_role:
        return Student.objects.all()
    return Student.objects.filter(teacher=user)


def _juz_page_counts_json():
    """Şablonda cüz seçildiğinde 'cüz içi sayfa' alanının üst sınırını göstermek için."""
    return json.dumps({str(j): juz_page_count(j) for j in range(1, TOTAL_JUZ + 1)})


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

    # Bu öğrenci için bugüne ait bir kayıt zaten varsa, tekrar oluşturmak yerine düzenlemeye yönlendir.
    today = timezone.localdate()
    existing_today = LessonRecord.objects.filter(student=student, date=today).first()
    if existing_today and request.method == "GET" and request.GET.get("today") == "1":
        messages.info(request, "Bu öğrenci için bugüne ait bir ders kaydı zaten var, üzerinde düzenleme yapabilirsiniz.")
        return redirect(reverse("lessons:update", kwargs={"pk": existing_today.pk}))

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
        initial_date = today if request.GET.get("today") == "1" else None
        form = LessonRecordForm(instance=instance, initial={"date": initial_date})
        formset = RevisionRecordFormSet(instance=instance)

    return render(request, "lessons/form.html", {
        "form": form, "formset": formset, "student": student,
        "juz_page_counts_json": _juz_page_counts_json(),
    })


def daily_entry(request):
    """'Bugünkü Ders Gir' hızlı giriş ekranı: öğrenci seçilir, seçilince o öğrencinin
    bugünkü ders formuna (tarih otomatik dolu) yönlendirilir."""
    students = _scoped_students(request.user).filter(status=Student.Status.ACTIVE).order_by("full_name")

    if request.method == "POST":
        student_pk = request.POST.get("student")
        if student_pk:
            return redirect(f"{reverse('lessons:create', kwargs={'student_pk': student_pk})}?today=1")
        messages.error(request, "Lütfen bir öğrenci seçin.")

    return render(request, "lessons/daily_entry.html", {"students": students, "today": timezone.localdate()})


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
        "juz_page_counts_json": _juz_page_counts_json(),
    })


def lesson_delete(request, pk):
    lesson = get_object_or_404(LessonRecord, pk=pk, student__in=_scoped_students(request.user))
    student_pk = lesson.student.pk
    if request.method == "POST":
        lesson.delete()
        messages.success(request, "Ders kaydı silindi.")
        return redirect(reverse("students:detail", kwargs={"pk": student_pk}))
    return render(request, "lessons/confirm_delete.html", {"lesson": lesson})
