from django.db import models
from django.utils import timezone


class PredictionHistory(models.Model):
    """Öğrenci için hesaplanan hafızlık bitiş tahmini geçmişi."""

    class Method(models.TextChoices):
        SIMPLE_AVERAGE = "simple_average", "Basit Ortalama"
        EMA = "ema", "Üstel Hareketli Ortalama (EMA)"

    class Confidence(models.TextChoices):
        LOW = "low", "Düşük"
        MEDIUM = "medium", "Orta"
        HIGH = "high", "Yüksek"

    class Bottleneck(models.TextChoices):
        """
        Cüz/Tur/Pişmiş sistemine geçişle birlikte tahmin artık iki ayrı hattı
        (ham ve has) izliyor; bu alan nihai tahmini hangi hattın belirlediğini
        gösterir (bkz. predictions/services.py:calculate_prediction docstring'i).
        Boş ('') değer, hiçbir hat için tahmin üretilemediği (pace verisi yok)
        durumunu ifade eder.
        """
        HAM = "ham", "Ham (Yeni Ezber)"
        HAS = "has", "Has (Pişirme/Tekrar)"

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="predictions", verbose_name="Öğrenci")
    # NOT: Bilerek auto_now_add KULLANILMIYOR. Django'nun DateField.auto_now_add
    # implementasyonu tarih için timezone.localdate() (TIME_ZONE=Europe/Istanbul'a göre
    # "bugün") DEĞİL, sunucu işletim sisteminin yerel saatine bağlı datetime.date.today()
    # kullanır. Render gibi konteynerler genelde UTC ile çalıştığından, İstanbul saatiyle
    # 00:00-03:00 arası çağrılarda auto_now_add "dün"ün tarihini yazabilir; bu da
    # predictions/services.py:calculate_prediction()'daki update_or_create(calculated_date=today, ...)
    # eşleştirmesini bozup her çağrıda yeni (yanlış tarihli) satır oluşturulmasına yol açar.
    # Bunun yerine tarih HER ZAMAN calculate_prediction() içinde timezone.localdate() ile
    # açıkça hesaplanıp buraya geçirilir.
    calculated_date = models.DateField(default=timezone.localdate, verbose_name="Hesaplama Tarihi")
    estimated_completion_date = models.DateField(null=True, blank=True, verbose_name="Tahmini Bitiş Tarihi")
    estimated_remaining_days = models.PositiveIntegerField(null=True, blank=True, verbose_name="Tahmini Kalan Gün")
    confidence_level = models.CharField(max_length=10, choices=Confidence.choices, default=Confidence.LOW, verbose_name="Güven Seviyesi")
    method_used = models.CharField(max_length=20, choices=Method.choices, default=Method.SIMPLE_AVERAGE, verbose_name="Hesaplama Yöntemi")

    # ÖNEMLİ: remaining_pages/daily_pace alanları artık HAS (pişirme) bazlı --
    # yani gerçek "hafız olma" darboğazını yansıtır. Eskiden (sadece ham
    # bazlıyken) bu alanlar öğrencinin ilk geçişi ne zaman bitireceğini
    # gösteriyordu; şimdi asıl soruyu ("ne zaman gerçekten hafız olur")
    # cevaplıyor. Ham/has kırılımı için aşağıdaki yeni alanlara bakın.
    remaining_pages = models.PositiveSmallIntegerField(default=0, verbose_name="Kalan Sayfa (Has/Pişirme Bazlı)")
    daily_pace = models.FloatField(default=0, verbose_name="Günlük İlerleme (Belirleyici Faz, Sayfa)")

    remaining_ham_pages = models.PositiveSmallIntegerField(default=0, verbose_name="Kalan Ham Sayfa")
    remaining_has_pages = models.PositiveSmallIntegerField(default=0, verbose_name="Kalan Has (Pişirme) Sayfa")
    ham_daily_pace = models.FloatField(default=0, verbose_name="Günlük Ham Hızı (Sayfa)")
    has_daily_pace = models.FloatField(default=0, verbose_name="Günlük Has Hızı (Sayfa)")
    bottleneck_phase = models.CharField(
        max_length=10, choices=Bottleneck.choices, blank=True, default="",
        verbose_name="Belirleyici Faz",
        help_text="Tahmini bitiş tarihini hangi hattın (ham/has) belirlediğini gösterir.",
    )

    class Meta:
        verbose_name = "Tahmin Geçmişi"
        verbose_name_plural = "Tahmin Geçmişleri"
        ordering = ["-calculated_date", "-id"]

    def __str__(self):
        return f"{self.student} - {self.calculated_date}"
