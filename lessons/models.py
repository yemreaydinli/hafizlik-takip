from django.conf import settings
from django.db import models


class LessonRecord(models.Model):
    """Bir öğrencinin bir günkü ders kaydı (devam, ham ezber, has tekrar, kalite, not)."""

    class Attendance(models.TextChoices):
        PRESENT = "present", "Geldi"
        ABSENT = "absent", "Gelmedi"
        EXCUSED = "excused", "İzinli"

    class Quality(models.TextChoices):
        EXCELLENT = "excellent", "Çok İyi"
        GOOD = "good", "İyi"
        AVERAGE = "average", "Orta"
        WEAK = "weak", "Zayıf"

    QUALITY_SCORES = {
        Quality.EXCELLENT: 100,
        Quality.GOOD: 80,
        Quality.AVERAGE: 60,
        Quality.WEAK: 35,
    }

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="lesson_records", verbose_name="Öğrenci")
    date = models.DateField(verbose_name="Ders Tarihi")
    attendance = models.CharField(max_length=10, choices=Attendance.choices, default=Attendance.PRESENT, verbose_name="Devam Durumu")

    ham_start_page = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Ham Ders Başlangıç Sayfası")
    ham_end_page = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Ham Ders Bitiş Sayfası")

    quality = models.CharField(max_length=10, choices=Quality.choices, null=True, blank=True, verbose_name="Ders Kalitesi")
    notes = models.TextField(blank=True, verbose_name="Günlük Notlar")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="lesson_records_created", verbose_name="Kaydı Giren")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Tarihi")

    class Meta:
        verbose_name = "Günlük Ders Kaydı"
        verbose_name_plural = "Günlük Ders Kayıtları"
        ordering = ["-date"]
        unique_together = ("student", "date")

    def __str__(self):
        return f"{self.student} - {self.date}"

    @property
    def ham_page_count(self):
        if self.ham_start_page and self.ham_end_page and self.ham_end_page >= self.ham_start_page:
            return self.ham_end_page - self.ham_start_page + 1
        return 0

    @property
    def revision_page_count(self):
        return sum(r.page_count for r in self.revision_ranges.all())

    @property
    def quality_score(self):
        if not self.quality:
            return None
        return self.QUALITY_SCORES.get(self.quality)


class PerformanceHistory(models.Model):
    """
    Öğrenci bazlı günlük özet performans geçmişi.
    Tahmin motoru ve uyarı sistemi bu tablo üzerinden çalışır; LessonRecord kaydedildiğinde
    sinyal (signals.py) aracılığıyla otomatik güncellenir.
    """

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="performance_history", verbose_name="Öğrenci")
    date = models.DateField(verbose_name="Tarih")
    daily_memorization = models.PositiveSmallIntegerField(default=0, verbose_name="Günlük Toplam Ezber")
    daily_revision = models.PositiveSmallIntegerField(default=0, verbose_name="Günlük Toplam Tekrar")
    quality_score = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Kalite Puanı")
    attended = models.BooleanField(default=True, verbose_name="Derse Geldi mi")
    cumulative_memorized_pages = models.PositiveSmallIntegerField(default=0, verbose_name="Kümülatif Ezberlenen Sayfa")

    class Meta:
        verbose_name = "Performans Geçmişi"
        verbose_name_plural = "Performans Geçmişleri"
        unique_together = ("student", "date")
        ordering = ["date"]

    def __str__(self):
        return f"{self.student} - {self.date}"
