from django.db import models


class PredictionHistory(models.Model):
    """Öğrenci için hesaplanan hafızlık bitiş tahmini geçmişi."""

    class Method(models.TextChoices):
        SIMPLE_AVERAGE = "simple_average", "Basit Ortalama"
        EMA = "ema", "Üstel Hareketli Ortalama (EMA)"

    class Confidence(models.TextChoices):
        LOW = "low", "Düşük"
        MEDIUM = "medium", "Orta"
        HIGH = "high", "Yüksek"

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="predictions")
    calculated_date = models.DateField(auto_now_add=True)
    estimated_completion_date = models.DateField(null=True, blank=True)
    estimated_remaining_days = models.PositiveIntegerField(null=True, blank=True)
    confidence_level = models.CharField(max_length=10, choices=Confidence.choices, default=Confidence.LOW)
    method_used = models.CharField(max_length=20, choices=Method.choices, default=Method.SIMPLE_AVERAGE)
    remaining_pages = models.PositiveSmallIntegerField(default=0)
    daily_pace = models.FloatField(default=0)

    class Meta:
        verbose_name = "Tahmin Geçmişi"
        verbose_name_plural = "Tahmin Geçmişleri"
        ordering = ["-calculated_date"]

    def __str__(self):
        return f"{self.student} - {self.calculated_date}"
