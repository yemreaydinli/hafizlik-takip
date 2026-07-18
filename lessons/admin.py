from django.contrib import admin
from .models import LessonRecord, PerformanceHistory


@admin.register(LessonRecord)
class LessonRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "date", "attendance", "ham_page_count", "quality")
    list_filter = ("attendance", "quality", "date")
    search_fields = ("student__full_name",)
    date_hierarchy = "date"


@admin.register(PerformanceHistory)
class PerformanceHistoryAdmin(admin.ModelAdmin):
    list_display = ("student", "date", "daily_memorization", "daily_revision", "quality_score", "attended")
    list_filter = ("attended", "date")
    search_fields = ("student__full_name",)
