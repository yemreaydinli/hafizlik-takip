from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """Öğrenci kayıtlarının tamamını buradan görüntüleyip düzenleyebilirsiniz."""

    list_display = ("full_name", "teacher", "status", "start_date", "target_completion_date", "phone")
    list_filter = ("status", "teacher")
    list_editable = ("status",)
    search_fields = ("full_name", "phone")
    date_hierarchy = "start_date"
    autocomplete_fields = ("teacher",)
    ordering = ("full_name",)

    fieldsets = (
        ("Kimlik Bilgileri", {"fields": ("full_name", "birth_date", "phone")}),
        ("Hafızlık Süreci", {
            "fields": ("teacher", "status", "start_date", "target_completion_date"),
            "description": "Hedef Bitiş Tarihi, Akıllı Uyarı Sistemi'nin 'Hedef Sapması' uyarısı üretmesi için kullanılır.",
        }),
        ("Ek Bilgiler", {"fields": ("notes",)}),
        ("Sistem Bilgileri", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    readonly_fields = ("created_at", "updated_at")
