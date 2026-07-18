from django import forms
from .models import Student

TAILWIND_INPUT = "w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-emerald-500 focus:ring-emerald-500 text-sm"


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ["full_name", "birth_date", "phone", "start_date", "status", "target_completion_date", "notes"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": TAILWIND_INPUT, "placeholder": "Ad Soyad"}),
            "birth_date": forms.DateInput(attrs={"type": "date", "class": TAILWIND_INPUT}),
            "phone": forms.TextInput(attrs={"class": TAILWIND_INPUT, "placeholder": "05xx xxx xx xx"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": TAILWIND_INPUT}),
            "status": forms.Select(attrs={"class": TAILWIND_INPUT}),
            "target_completion_date": forms.DateInput(attrs={"type": "date", "class": TAILWIND_INPUT}),
            "notes": forms.Textarea(attrs={"class": TAILWIND_INPUT, "rows": 3}),
        }
