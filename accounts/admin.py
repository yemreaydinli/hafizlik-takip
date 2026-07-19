from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Kullanıcı yönetimi: Yönetici (admin) ve Hafız Yetiştiricisi (teacher) rolündeki
    hesapları buradan görebilir, ekleyebilir ve düzenleyebilirsiniz.
    'Rol' alanı sistemdeki yetkiyi belirler: Yönetici tüm öğrencileri görür,
    Öğretici yalnızca kendi öğrencilerini görür.
    """

    list_display = ("username", "get_full_name", "email", "role", "phone", "is_active")
    list_filter = ("role", "is_active")
    list_editable = ()
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("role", "first_name")

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Hafızlık Sistemi Bilgileri", {
            "fields": ("role", "phone"),
            "description": "Rol, kullanıcının sistemde neler görebileceğini belirler.",
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Hafızlık Sistemi Bilgileri", {"fields": ("role", "phone", "email", "first_name", "last_name")}),
    )

    @admin.display(description="Ad Soyad")
    def get_full_name(self, obj):
        return obj.get_full_name() or "—"
