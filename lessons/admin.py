from django.contrib import admin
from .models import LessonRecord, PerformanceHistory
from .signals import sync_lesson
from memorization.models import RevisionRecord


class RevisionRecordInline(admin.TabularInline):
    """Bir ders kaydına bağlı tekrar (has) edilen cüzleri aynı ekranda düzenlemeyi sağlar."""
    model = RevisionRecord
    extra = 1
    fields = ("start_page", "end_page")
    verbose_name = "Tekrar (Has) Cüzü"
    verbose_name_plural = "Tekrar (Has) Cüzleri"


@admin.register(LessonRecord)
class LessonRecordAdmin(admin.ModelAdmin):
    """
    Öğrencilerin günlük ders kayıtları (devam, ham ezber, has tekrar, kalite, not).
    Bir kayıt kaydedildiğinde sistem otomatik olarak Hafızlık Haritası'nı ve
    Performans Geçmişi'ni günceller (bkz. lessons/signals.py).
    """

    list_display = ("student", "date", "attendance", "ham_juz_label", "revision_juz_labels_display", "quality")
    list_filter = ("attendance", "quality", "date")
    search_fields = ("student__full_name",)
    date_hierarchy = "date"
    autocomplete_fields = ("student",)
    inlines = [RevisionRecordInline]

    fieldsets = (
        ("Ders Bilgileri", {"fields": ("student", "date", "attendance")}),
        ("Ham (Yeni Ezber)", {"fields": ("ham_start_page", "ham_end_page")}),
        ("Pişmiş", {"fields": ("pismis_done", "pismis_page_count")}),
        ("Değerlendirme", {"fields": ("quality", "notes")}),
        ("Sistem Bilgileri", {"fields": ("created_by", "created_at", "updated_at"), "classes": ("collapse",)}),
    )
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Ham (Cüz)")
    def ham_juz_label(self, obj):
        return obj.ham_juz_label or "-"

    @admin.display(description="Tekrar Edilen Cüzler")
    def revision_juz_labels_display(self, obj):
        return ", ".join(obj.revision_juz_labels) or "-"

    def save_related(self, request, form, formsets, change):
        """
        ÖNEMLİ: sync_lesson() bilinçli olarak bir post_save sinyaline bağlı değil
        (bkz. lessons/signals.py:sync_lesson docstring'i) çünkü normal akışta
        (views.py) LessonRecord kaydedilirken bağlı RevisionRecord formseti henüz
        kaydedilmemiş olur. Admin'de de aynı sıra geçerlidir: save_model() ana
        LessonRecord'u kaydeder, save_related() ise inline RevisionRecord
        formsetini kaydeder. Bu yüzden sync_lesson'ı burada -- formset(ler)
        kaydedildikten SONRA -- çağırmak gerekir; aksi halde admin panelinden
        yapılan düzenlemeler Hafızlık Haritası/JuzTurCount/Tahmin Motoru'nu
        senkron dışı bırakır.
        """
        super().save_related(request, form, formsets, change)
        sync_lesson(form.instance)


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
