from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import User


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "class": "w-full rounded-lg border border-slate-300 px-4 py-2.5 focus:border-emerald-500 focus:ring-emerald-500",
            "placeholder": "Kullanıcı adı",
        })
        self.fields["password"].widget.attrs.update({
            "class": "w-full rounded-lg border border-slate-300 px-4 py-2.5 focus:border-emerald-500 focus:ring-emerald-500",
            "placeholder": "Şifre",
        })


class TeacherCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.TEACHER
        if commit:
            user.save()
        return user
