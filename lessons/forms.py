from django import forms
from django.forms import inlineformset_factory

from .models import LessonRecord
from memorization.models import RevisionRecord

TAILWIND_INPUT = "w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-emerald-500 focus:ring-emerald-500 text-sm"


class LessonRecordForm(forms.ModelForm):
    class Meta:
        model = LessonRecord
        fields = ["date", "attendance", "ham_start_page", "ham_end_page", "quality", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": TAILWIND_INPUT}),
            "attendance": forms.Select(attrs={"class": TAILWIND_INPUT, "id": "id_attendance"}),
            "ham_start_page": forms.NumberInput(attrs={"class": TAILWIND_INPUT, "min": 1, "max": 604}),
            "ham_end_page": forms.NumberInput(attrs={"class": TAILWIND_INPUT, "min": 1, "max": 604}),
            "quality": forms.Select(attrs={"class": TAILWIND_INPUT}),
            "notes": forms.Textarea(attrs={"class": TAILWIND_INPUT, "rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date_value = cleaned_data.get("date")
        student = self.instance.student
        if date_value and student:
            qs = LessonRecord.objects.filter(student=student, date=date_value)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("date", "Bu öğrenci için bu tarihte zaten bir ders kaydı mevcut.")
        start = cleaned_data.get("ham_start_page")
        end = cleaned_data.get("ham_end_page")
        if start and end and end < start:
            self.add_error("ham_end_page", "Bitiş sayfası başlangıç sayfasından küçük olamaz.")
        return cleaned_data


RevisionRecordFormSet = inlineformset_factory(
    LessonRecord,
    RevisionRecord,
    fields=["start_page", "end_page"],
    extra=1,
    can_delete=True,
    widgets={
        "start_page": forms.NumberInput(attrs={"class": TAILWIND_INPUT, "min": 1, "max": 604, "placeholder": "Baş."}),
        "end_page": forms.NumberInput(attrs={"class": TAILWIND_INPUT, "min": 1, "max": 604, "placeholder": "Bit."}),
    },
)
