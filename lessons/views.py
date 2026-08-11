import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import ListView

from core.quran import TOTAL_JUZ, juz_page_count
from students.models import Student
from memorization.services import get_juz_next_ham_pages, is_juz_ham_covered
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


def _juz_next_ham_pages_json(student):
    """
    Şablonda hoca bir cüz seçtiğinde, o öğrencinin bu cüzde daha önce nereye kadar
    ham (yeni ezber) aldığına bakarak bir sonraki sayfayı otomatik önermek için.
    Sadece bir öneridir; hoca formda dilediği gibi değiştirebilir.
    """
    return json.dumps({str(j): v for j, v in get_juz_next_ham_pages(student).items()})


def _validate_ham_coverage_for_revisions(student, form, formset, exclude_lesson_id=None):
    """
    Formset kaydedilmeden ÖNCE, seçilen her has (tekrar) cüzünün ham'ı gerçekten
    tamamlanmış mı diye kontrol eder ve eksikse formset'e hata ekler.

    NEDEN: Has girişi tek bir cüz seçilerek yapılıyor (bkz. lessons/forms.py:
    RevisionRecordForm) ve bu, cüzün TAMAMEN ham'ı yapılmış olduğunu varsayar.
    Bu varsayımın kendisi doğru (has gerçekten tek seferde, tam cüz olarak
    veriliyor) -- burada değiştirilen bu değil. Ama hoca yanlışlıkla (örn.
    açılır listeden yanlış cüzü seçerek) henüz ham'ı hiç/tam yapılmamış bir
    cüzü "tekrar edildi" olarak işaretlerse, sistem sessizce o sayfaları
    "pişmiş" sayar (bkz. memorization/services.py:is_juz_ham_covered
    docstring'i). Bu fonksiyon SADECE kaydetmeden önce bu tutarsızlığı
    yakalar; "tek cüz has verme" arayüzüne dokunmaz.

    Dönüş: True (kaydedilebilir) / False (formset'e hata eklendi, kaydetme).
    """
    current_ham_range = (form.cleaned_data.get("ham_start_page"), form.cleaned_data.get("ham_end_page"))
    is_valid = True
    for revision_form in formset.forms:
        if not revision_form.cleaned_data or revision_form.cleaned_data.get("DELETE"):
            continue
        juz_value = revision_form.cleaned_data.get("juz_number")
        if not juz_value:
            continue
        juz_number = int(juz_value)
        if not is_juz_ham_covered(
            student, juz_number, extra_ranges=[current_ham_range], exclude_lesson_id=exclude_lesson_id
        ):
            revision_form.add_error(
                "juz_number",
                f"{juz_number}. Cüz için ham (yeni ezber) henüz tamamlanmamış. "
                "Has (tekrar) girmeden önce bu cüzün tüm sayfalarının ham'ı tamamlanmış olmalı.",
            )
            is_valid = False
    return is_valid


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


@login_required
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
        # ÖNEMLİ: formset, LessonRecord henüz kaydedilmeden (kaydedilmemiş bir
        # instance ile) oluşturuluyor. inlineformset_factory bunu destekler:
        # formset.is_valid() sırasında henüz DB'ye yazma yapılmaz. Böylece hem
        # form hem formset geçerli olduğundan EMİN OLMADAN hiçbir şey
        # kaydedilmez -- form.is_valid() doğruysa bile formset geçersizse artık
        # yarım (tekrar bilgisi eksik) bir LessonRecord veritabanında kalmaz.
        formset = RevisionRecordFormSet(request.POST, instance=instance)
        if form.is_valid() and formset.is_valid() and _validate_ham_coverage_for_revisions(student, form, formset):
            with transaction.atomic():
                lesson = form.save()
                formset.instance = lesson
                formset.save()
                sync_lesson(lesson)
            messages.success(request, "Günlük ders kaydı eklendi.")
            return redirect(reverse("students:detail", kwargs={"pk": student.pk}))
    else:
        initial_date = today if request.GET.get("today") == "1" else None
        form = LessonRecordForm(instance=instance, initial={"date": initial_date})
        formset = RevisionRecordFormSet(instance=instance)

    return render(request, "lessons/form.html", {
        "form": form, "formset": formset, "student": student,
        "juz_page_counts_json": _juz_page_counts_json(),
        "juz_next_ham_pages_json": _juz_next_ham_pages_json(student),
    })


@login_required
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


@login_required
def lesson_update(request, pk):
    lesson = get_object_or_404(
        LessonRecord.objects.select_related("student"), pk=pk, student__in=_scoped_students(request.user)
    )
    if request.method == "POST":
        form = LessonRecordForm(request.POST, instance=lesson)
        formset = RevisionRecordFormSet(request.POST, instance=lesson)
        if form.is_valid() and formset.is_valid() and _validate_ham_coverage_for_revisions(
            lesson.student, form, formset, exclude_lesson_id=lesson.pk
        ):
            with transaction.atomic():
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
        "juz_next_ham_pages_json": _juz_next_ham_pages_json(lesson.student),
    })


@login_required
def lesson_delete(request, pk):
    lesson = get_object_or_404(LessonRecord, pk=pk, student__in=_scoped_students(request.user))
    student_pk = lesson.student.pk
    if request.method == "POST":
        lesson.delete()
        messages.success(request, "Ders kaydı silindi.")
        return redirect(reverse("students:detail", kwargs={"pk": student_pk}))
    return render(request, "lessons/confirm_delete.html", {"lesson": lesson})
