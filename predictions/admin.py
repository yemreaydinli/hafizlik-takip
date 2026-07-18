from django.contrib import admin
from .models import PredictionHistory


@admin.register(PredictionHistory)
class PredictionHistoryAdmin(admin.ModelAdmin):
    list_display = ("student", "calculated_date", "estimated_completion_date", "method_used", "confidence_level")
    list_filter = ("method_used", "confidence_level")
