from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Akıllı Uyarı Sistemi'nin ürettiği bildirimler (Duraklama, Devamsızlık,
    Performans Düşüşü, Hedef Sapması). `generate_alerts` komutu her çalıştığında
    yeni uyarılar otomatik oluşturulur; elle yeni uyarı eklemeye gerek yoktur.
    """

    list_display = ("student", "type", "teacher", "is_read", "created_at")
    list_filter = ("type", "is_read")
    list_editable = ("is_read",)
    search_fields = ("student__full_name", "message")
    date_hierarchy = "created_at"
    autocomplete_fields = ("student", "teacher")

    def has_add_permission(self, request):
        return False
