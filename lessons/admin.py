from django.contrib import admin
from .models import LessonRecord, PerformanceHistory
from memorization.models import RevisionRecord


class RevisionRecordInline(admin.TabularInline):
    """Bir ders kaydına bağlı tekrar (has) sayfa aralıklarını aynı ekranda düzenlemeyi sağlar."""
    model = RevisionRecord
    extra = 1
    verbose_name = "Tekrar (Has) Aralığı"
    verbose_name_plural = "Tekrar (Has) Aralıkları"


@admin.register(LessonRecord)
class LessonRecordAdmin(admin.ModelAdmin):
    """
    Öğrencilerin günlük ders kayıtları (devam, ham ezber, has tekrar, kalite, not).
    Bir kayıt kaydedildiğinde sistem otomatik olarak Hafızlık Haritası'nı ve
    Performans Geçmişi'ni günceller (bkz. lessons/signals.py).
    """

    list_display = ("student", "date", "attendance", "ham_page_count_display", "revision_page_count_display", "quality")
    list_filter = ("attendance", "quality", "date")
    search_fields = ("student__full_name",)
    date_hierarchy = "date"
    autocomplete_fields = ("student",)
    inlines = [RevisionRecordInline]

    fieldsets = (
        ("Ders Bilgileri", {"fields": ("student", "date", "attendance")}),
        ("Ham (Yeni Ezber)", {"fields": ("ham_start_page", "ham_end_page")}),
        ("Değerlendirme", {"fields": ("quality", "notes")}),
        ("Sistem Bilgileri", {"fields": ("created_by", "created_at", "updated_at"), "classes": ("collapse",)}),
    )
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Ham Sayfa Sayısı")
    def ham_page_count_display(self, obj):
        return obj.ham_page_count

    @admin.display(description="Tekrar Sayfa Sayısı")
    def revision_page_count_display(self, obj):
        return obj.revision_page_count


@admin.register(PerformanceHistory)
class PerformanceHistoryAdmin(admin.ModelAdmin):
    """
    Öğrenci bazlı otomatik oluşturulan günlük performans özeti.
    Bu tablo elle düzenlenmez; Akıllı Tahmin Motoru ve Akıllı Uyarı Sistemi
    hesaplamalarını buradaki veriler üzerinden yapar.
    """

    list_display = ("student", "date", "daily_memorization", "daily_revision", "quality_score", "attended")
    list_filter = ("attended", "date")
    search_fields = ("student__full_name",)
    date_hierarchy = "date"

    def has_add_permission(self, request):
        # Bu tablo yalnızca sistem tarafından (ders kaydı sinyaliyle) otomatik doldurulur.
        return False
