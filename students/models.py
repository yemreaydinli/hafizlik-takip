from django.conf import settings
from django.db import models
from django.urls import reverse


class Student(models.Model):
    """Hafızlık öğrencisi."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Aktif"
        PAUSED = "paused", "Ara Verdi"
        COMPLETED = "completed", "Hafızlığını Tamamladı"

    full_name = models.CharField(max_length=150, verbose_name="Ad Soyad")
    birth_date = models.DateField(verbose_name="Doğum Tarihi", null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, verbose_name="Telefon")
    start_date = models.DateField(verbose_name="Hafızlığa Başlama Tarihi")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, verbose_name="Aktiflik Durumu")
    notes = models.TextField(blank=True, verbose_name="Açıklamalar")
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="students",
        limit_choices_to={"role": "teacher"},
        verbose_name="Öğretici",
    )
    target_completion_date = models.DateField(
        null=True, blank=True, verbose_name="Hedef Bitiş Tarihi",
        help_text="Öğretici tarafından belirlenen hedef tarih (Hedef Sapması uyarısı için kullanılır)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Öğrenci"
        verbose_name_plural = "Öğrenciler"
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse("students:detail", kwargs={"pk": self.pk})
