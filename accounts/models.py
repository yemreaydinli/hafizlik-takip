from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Sistem kullanıcısı. İki rol vardır:
    - admin: Sistem yöneticisi (tam yetki)
    - teacher: Hafız yetiştiricisi (kendi öğrencileri üzerinde yetki)
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Yönetici"
        TEACHER = "teacher", "Hafız Yetiştiricisi"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.TEACHER)
    phone = models.CharField(max_length=20, blank=True, verbose_name="Telefon")

    class Meta:
        verbose_name = "Kullanıcı"
        verbose_name_plural = "Kullanıcılar"

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_teacher_role(self):
        return self.role == self.Role.TEACHER
