from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("full_name", "teacher", "status", "start_date", "phone")
    list_filter = ("status", "teacher")
    search_fields = ("full_name", "phone")
