from django.contrib import admin

from .models import BackupLog


@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "created_by", "record_count", "size_bytes")
    readonly_fields = ("created_at", "created_by", "size_bytes", "record_count")
