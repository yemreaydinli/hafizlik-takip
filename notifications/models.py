from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Akıllı uyarı sistemi tarafından üretilen bildirimler."""

    class Type(models.TextChoices):
        PAUSE = "pause", "Duraklama Uyarısı"
        ABSENCE = "absence", "Devamsızlık Uyarısı"
        PERFORMANCE_DROP = "performance_drop", "Performans Düşüşü"
        TARGET_DEVIATION = "target_deviation", "Hedef Sapması"

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="notifications")
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=20, choices=Type.choices)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bildirim"
        verbose_name_plural = "Bildirimler"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_type_display()}] {self.student} - {self.message}"
