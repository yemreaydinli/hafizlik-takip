from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "get_full_name", "email", "role", "phone", "is_active")
    list_filter = ("role", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Hafızlık Sistemi", {"fields": ("role", "phone")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Hafızlık Sistemi", {"fields": ("role", "phone", "email", "first_name", "last_name")}),
    )
