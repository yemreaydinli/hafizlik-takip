from django.contrib import admin
from .models import MemorizationPage, RevisionRecord, JuzTurCount

RevisionRecord.page_count.fget.short_description = "Sayfa Sayısı"


@admin.register(MemorizationPage)
class MemorizationPageAdmin(admin.ModelAdmin):
    """
    Kur'an'ın 604 sayfasının öğrenci bazlı durumu (Görsel Hafızlık Haritası'nın
    veri kaynağıdır). Durumlar: 'Henüz Çalışılmadı' (gri), 'Tekrar Gerekiyor' (sarı),
    'Başarıyla Tamamlandı' (yeşil). Normalde ders kaydı girildiğinde otomatik güncellenir;
    öğrencinin sisteme kayıttan önceki mevcut durumunu aktarmak için elle de düzenlenebilir.
    """

    list_display = ("student", "page_number", "juz_number_display", "status", "revision_count", "first_memorized_date", "last_revised_date")
    list_filter = ("status",)
    list_editable = ("status",)
    search_fields = ("student__full_name",)
    autocomplete_fields = ("student",)
    ordering = ("student", "page_number")
    list_per_page = 50

    @admin.display(description="Cüz No")
    def juz_number_display(self, obj):
        return obj.juz_number


@admin.register(RevisionRecord)
class RevisionRecordAdmin(admin.ModelAdmin):
    """Bir ders kaydına bağlı tekrar (has) cüzleri. Genelde ders kaydı ekranından (satır içi) yönetilir.

    Bu ekrandan tek başına (LessonRecord inline'ı dışında) eklenip/silinebildiği
    için, kaydı ders kaydına bağlayan lessons/signals.py:sync_lesson burada da
    elle çağrılmalıdır -- aksi halde Hafızlık Haritası/JuzTurCount senkron dışı
    kalır (bkz. lessons/admin.py:LessonRecordAdmin.save_related ile aynı gerekçe).
    """

    list_display = ("lesson", "juz_label", "start_page", "end_page", "page_count")
    search_fields = ("lesson__student__full_name",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from lessons.signals import sync_lesson
        sync_lesson(obj.lesson)

    def delete_model(self, request, obj):
        from lessons.signals import sync_lesson
        lesson = obj.lesson
        super().delete_model(request, obj)
        sync_lesson(lesson)

    def delete_queryset(self, request, queryset):
        from lessons.signals import sync_lesson
        lessons = {obj.lesson for obj in queryset}
        super().delete_queryset(request, queryset)
        for lesson in lessons:
            sync_lesson(lesson)


@admin.register(JuzTurCount)
class JuzTurCountAdmin(admin.ModelAdmin):
    """Öğrenci başına, her cüzün kaçıncı kez tekrar (has) edildiğini gösteren sayaç. Elle düzenlenmez, otomatik hesaplanır."""

    list_display = ("student", "juz_number", "tur_count", "last_tur_date", "synced_from_lessons")
    list_filter = ("juz_number", "synced_from_lessons")
    search_fields = ("student__full_name",)
    ordering = ("student", "juz_number")

    def has_add_permission(self, request):
        return False
