from django.contrib import admin
from .models import MemorizationPage, RevisionRecord


@admin.register(MemorizationPage)
class MemorizationPageAdmin(admin.ModelAdmin):
    list_display = ("student", "page_number", "status", "revision_count", "last_revised_date")
    list_filter = ("status",)
    search_fields = ("student__full_name",)


@admin.register(RevisionRecord)
class RevisionRecordAdmin(admin.ModelAdmin):
    list_display = ("lesson", "start_page", "end_page", "page_count")
