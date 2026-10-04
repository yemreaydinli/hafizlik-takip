from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import User


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "class": "input",
            "autocomplete": "username",
            "placeholder": "Kullanıcı adı",
        })
        self.fields["password"].widget.attrs.update({
            "class": "input",
            "autocomplete": "current-password",
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
