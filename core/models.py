from django.conf import settings
from django.db import models


class BackupLog(models.Model):
    """Yöneticinin indirdiği yedeklerin kaydı (yedek dosyasının kendisi sunucuda saklanmaz)."""

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yedek zamanı")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", verbose_name="Yedeği alan",
    )
    size_bytes = models.PositiveIntegerField(default=0, verbose_name="Dosya boyutu (bayt)")
    record_count = models.PositiveIntegerField(default=0, verbose_name="Kayıt sayısı")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Yedek kaydı"
        verbose_name_plural = "Yedek kayıtları"

    def __str__(self):
        return f"Yedek {self.created_at:%d.%m.%Y %H:%M}"
