from django import forms
from core.widgets import ISODateInput
from .models import Student
from accounts.models import User

TAILWIND_INPUT = "w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-emerald-500 focus:ring-emerald-500 text-sm"


class StudentForm(forms.ModelForm):
    teacher = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Role.TEACHER),
        required=True,
        label="Öğretici",
        widget=forms.Select(attrs={"class": TAILWIND_INPUT}),
        help_text="Bu öğrenciden sorumlu olacak hafız yetiştiricisini seçin.",
    )

    class Meta:
        model = Student
        fields = ["full_name", "birth_date", "phone", "start_date", "status", "target_completion_date", "notes"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": TAILWIND_INPUT, "placeholder": "Ad Soyad"}),
            "birth_date": ISODateInput(attrs={"class": TAILWIND_INPUT}),
            "phone": forms.TextInput(attrs={"class": TAILWIND_INPUT, "placeholder": "05xx xxx xx xx"}),
            "start_date": ISODateInput(attrs={"class": TAILWIND_INPUT}),
            "status": forms.Select(attrs={"class": TAILWIND_INPUT}),
            "target_completion_date": ISODateInput(attrs={"class": TAILWIND_INPUT}),
            "notes": forms.Textarea(attrs={"class": TAILWIND_INPUT, "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # Sadece yöneticiler öğretici atayabilir; öğreticiler bu alanı görmez.
        if not self.user or not self.user.is_admin_role:
            self.fields.pop("teacher", None)
        elif self.instance and self.instance.pk:
            self.fields["teacher"].initial = self.instance.teacher_id
