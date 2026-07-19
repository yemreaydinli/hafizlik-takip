from django.contrib import admin
from .models import PredictionHistory


@admin.register(PredictionHistory)
class PredictionHistoryAdmin(admin.ModelAdmin):
    """
    Akıllı Tahmin Motoru'nun ürettiği geçmiş tahminler. Her öğrenci detay/tahmin
    sayfası ziyaret edildiğinde yeni bir kayıt otomatik oluşur; bu tablo yalnızca
    görüntüleme ve geçmiş analizi içindir, elle yeni kayıt eklenmez.
    """

    list_display = ("student", "calculated_date", "estimated_completion_date", "estimated_remaining_days", "method_used", "confidence_level")
    list_filter = ("method_used", "confidence_level")
    search_fields = ("student__full_name",)
    date_hierarchy = "calculated_date"

    def has_add_permission(self, request):
        return False
