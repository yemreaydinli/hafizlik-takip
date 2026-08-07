from django.conf import settings
from django.db import models


class MemorizationPage(models.Model):
    """
    Kur'an-ı Kerim'in her sayfası için öğrenci bazlı durum kaydı.
    Görsel Hafızlık Haritası bu tablo üzerinden oluşturulur.
    """

    class Status(models.TextChoices):
        NOT_STUDIED = "gray", "Henüz Çalışılmadı"
        NEEDS_REVISION = "yellow", "Ezberlendi, Tekrar Gerekiyor"
        COMPLETED = "green", "Başarıyla Tamamlandı"

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="pages", verbose_name="Öğrenci"
    )
    page_number = models.PositiveSmallIntegerField(verbose_name="Sayfa No")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NOT_STUDIED, verbose_name="Durum")
    first_memorized_date = models.DateField(null=True, blank=True, verbose_name="İlk Ezberlenme Tarihi")
    last_revised_date = models.DateField(null=True, blank=True, verbose_name="Son Tekrar Tarihi")
    revision_count = models.PositiveIntegerField(default=0, verbose_name="Tekrar Sayısı")
    synced_from_lessons = models.BooleanField(
        default=False,
        verbose_name="Ders Kaydından Senkronize",
        help_text=(
            "True ise bu sayfanın durumu günlük ders kayıtlarından (ham/has) otomatik "
            "hesaplanmıştır ve ders kaydı silinip/düzenlendiğinde yeniden hesaplanabilir. "
            "False ise 'Başlangıç Durumu Aktarımı' (bulk_apply_range) ile elle işaretlenmiştir "
            "ve ders senkronizasyonu bu sayfaları geri almaz/sıfırlamaz."
        ),
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Tarihi")

    class Meta:
        verbose_name = "Hafızlık Sayfası"
        verbose_name_plural = "Hafızlık Sayfaları"
        unique_together = ("student", "page_number")
        ordering = ["page_number"]

    def __str__(self):
        return f"{self.student} - Sayfa {self.page_number} ({self.get_status_display()})"

    @property
    def juz_number(self):
        from core.quran import juz_of_page
        return juz_of_page(self.page_number)


class RevisionRecord(models.Model):
    """Bir günlük ders kaydına bağlı tekrar (has) sayfa aralığı.
    Artık kullanıcı arayüzünden sayfa değil, cüz seçilerek girilir (bkz. lessons/forms.py);
    start_page/end_page seçilen cüzün mutlak sayfa aralığına eşitlenir."""

    lesson = models.ForeignKey(
        "lessons.LessonRecord", on_delete=models.CASCADE, related_name="revision_ranges", verbose_name="Ders Kaydı"
    )
    start_page = models.PositiveSmallIntegerField(verbose_name="Tekrar Başlangıç Sayfası")
    end_page = models.PositiveSmallIntegerField(verbose_name="Tekrar Bitiş Sayfası")

    class Meta:
        verbose_name = "Tekrar (Has) Kaydı"
        verbose_name_plural = "Tekrar (Has) Kayıtları"

    @property
    def page_count(self):
        return max(self.end_page - self.start_page + 1, 0)

    @property
    def juz_number(self):
        from core.quran import juz_of_page
        return juz_of_page(self.start_page)

    @property
    def juz_label(self):
        j = self.juz_number
        return f"{j}. Cüz" if j else "-"

    def __str__(self):
        return f"{self.lesson.student} - {self.juz_label}"


class JuzTurCount(models.Model):
    """
    Bir öğrencinin her cüzü kaçıncı kez has olarak tekrar ettiğini tutan sayaç
    ("has tekrar sayacı"). Bu, ham derste ilerlenen "tur" kavramından farklıdır --
    has tekrar, tamamlanmış bir cüzün baştan sona tekrar dinletilme sayısıdır.
    Ders kaydı kaydedildiğinde lessons/signals.py:sync_lesson() aracılığıyla
    sıfırdan yeniden hesaplanır; elle düzenlenmesi gerekmez.
    """

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="juz_tur_counts", verbose_name="Öğrenci"
    )
    juz_number = models.PositiveSmallIntegerField(verbose_name="Cüz No")
    tur_count = models.PositiveIntegerField(default=0, verbose_name="Has Tekrar Sayısı")
    last_tur_date = models.DateField(null=True, blank=True, verbose_name="Son Has Tekrar Tarihi")

    class Meta:
        verbose_name = "Cüz Has Tekrar Sayacı"
        verbose_name_plural = "Cüz Has Tekrar Sayaçları"
        unique_together = ("student", "juz_number")
        ordering = ["juz_number"]

    def __str__(self):
        return f"{self.student} - {self.juz_number}. Cüz ({self.tur_count}. has tekrar)"
