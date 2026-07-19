from django.contrib import admin
from .models import MemorizationPage, RevisionRecord

RevisionRecord.page_count.fget.short_description = "Sayfa Sayısı"


@admin.register(MemorizationPage)
class MemorizationPageAdmin(admin.ModelAdmin):
    """
    Kur'an'ın 604 sayfasının öğrenci bazlı durumu (Görsel Hafızlık Haritası'nın
    veri kaynağıdır). Durumlar: 'Henüz Çalışılmadı' (gri), 'Tekrar Gerekiyor' (sarı),
    'Başarıyla Tamamlandı' (yeşil). Normalde ders kaydı girildiğinde otomatik güncellenir;
    öğrencinin sisteme kayıttan önceki mevcut durumunu aktarmak için elle de düzenlenebilir.
    """

    list_display = ("student", "page_number", "status", "revision_count", "first_memorized_date", "last_revised_date")
    list_filter = ("status",)
    list_editable = ("status",)
    search_fields = ("student__full_name",)
    autocomplete_fields = ("student",)
    ordering = ("student", "page_number")
    list_per_page = 50


@admin.register(RevisionRecord)
class RevisionRecordAdmin(admin.ModelAdmin):
    """Bir ders kaydına bağlı tekrar (has) sayfa aralıkları. Genelde ders kaydı ekranından (satır içi) yönetilir."""

    list_display = ("lesson", "start_page", "end_page", "page_count")
    search_fields = ("lesson__student__full_name",)
