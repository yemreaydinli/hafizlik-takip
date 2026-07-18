from django.conf import settings
from django.db import models


class MemorizationPage(models.Model):
    """
    Kur'an-ı Kerim'in her sayfası için öğrenci bazlı durum kaydı.
    Görsel Hafızlık Haritası bu tablo üzerinden oluşturulur.
    """

    class Status(models.TextChoices):
        NOT_STUDIED = "gray", "Henüz Çalışılmadı"
        NEEDS_REVISION = "yellow", "Ezberlendi, Tekrar Gerekiyor"
        COMPLETED = "green", "Başarıyla Tamamlandı"

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="pages"
    )
    page_number = models.PositiveSmallIntegerField(verbose_name="Sayfa No")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NOT_STUDIED)
    first_memorized_date = models.DateField(null=True, blank=True)
    last_revised_date = models.DateField(null=True, blank=True)
    revision_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Hafızlık Sayfası"
        verbose_name_plural = "Hafızlık Sayfaları"
        unique_together = ("student", "page_number")
        ordering = ["page_number"]

    def __str__(self):
        return f"{self.student} - Sayfa {self.page_number} ({self.get_status_display()})"


class RevisionRecord(models.Model):
    """Bir günlük ders kaydına bağlı tekrar (has) sayfa aralığı."""

    lesson = models.ForeignKey(
        "lessons.LessonRecord", on_delete=models.CASCADE, related_name="revision_ranges"
    )
    start_page = models.PositiveSmallIntegerField(verbose_name="Tekrar Başlangıç Sayfası")
    end_page = models.PositiveSmallIntegerField(verbose_name="Tekrar Bitiş Sayfası")

    class Meta:
        verbose_name = "Tekrar (Has) Kaydı"
        verbose_name_plural = "Tekrar (Has) Kayıtları"

    @property
    def page_count(self):
        return max(self.end_page - self.start_page + 1, 0)

    def __str__(self):
        return f"{self.lesson.student} - {self.start_page}-{self.end_page}"
