"""Veritabanı yedeği üretimi ve "yedek gecikti mi?" kontrolü."""
import io
import json
from datetime import timedelta

from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from .models import BackupLog

# Yedeğe girmeyen, geri yüklemede sorun çıkarabilecek veya gereksiz tablolar.
EXCLUDED = [
    "contenttypes",
    "auth.permission",
    "sessions",
    "admin.logentry",
    "core.backuplog",
]


def build_backup():
    """Tüm uygulama verisini JSON olarak döndürür: (bytes, kayıt_sayısı)."""
    buf = io.StringIO()
    call_command(
        "dumpdata",
        exclude=EXCLUDED,
        use_natural_foreign_keys=True,
        use_natural_primary_keys=True,
        indent=1,
        stdout=buf,
    )
    text = buf.getvalue()
    return text.encode("utf-8"), len(json.loads(text))


def backup_warning_days():
    return int(getattr(settings, "BACKUP_WARNING_DAYS", 7))


def get_backup_status():
    """
    Yedek durumunu döndürür:
      last        -> son BackupLog (yoksa None)
      days_since  -> son yedekten beri geçen gün (yedek yoksa None)
      has_data    -> sistemde öğrenci verisi var mı
      warn        -> uyarı gösterilmeli mi
      limit_days  -> uyarı eşiği
    Veri yokken (hiç öğrenci eklenmemişken) uyarı verilmez.
    """
    from students.models import Student

    limit = backup_warning_days()
    last = BackupLog.objects.first()
    has_data = Student.objects.exists()
    days_since = None
    if last:
        days_since = (timezone.now() - last.created_at) // timedelta(days=1)
    overdue = last is None or days_since >= limit
    return {
        "last": last,
        "days_since": days_since,
        "has_data": has_data,
        "warn": has_data and overdue,
        "limit_days": limit,
    }
