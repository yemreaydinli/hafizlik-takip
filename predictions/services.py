"""
Akıllı Tahmin Motoru
=====================
İlk PREDICTION_SIMPLE_AVG_DAYS gün boyunca basit ortalama, sonrasında
Üstel Hareketli Ortalama (EMA) kullanarak öğrencinin hafızlığı tamamlama
tarihini tahmin eder.
"""
import statistics
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from memorization.models import MemorizationPage
from lessons.models import PerformanceHistory
from .models import PredictionHistory


def _ema(values, alpha):
    if not values:
        return 0.0
    ema_value = values[0]
    for v in values[1:]:
        ema_value = alpha * v + (1 - alpha) * ema_value
    return ema_value


def _confidence_level(sample_count, values):
    if sample_count < 7:
        return PredictionHistory.Confidence.LOW
    if sample_count < 20:
        return PredictionHistory.Confidence.MEDIUM
    try:
        cv = statistics.pstdev(values) / (statistics.mean(values) or 1)
    except statistics.StatisticsError:
        return PredictionHistory.Confidence.MEDIUM
    return PredictionHistory.Confidence.HIGH if cv < 0.6 else PredictionHistory.Confidence.MEDIUM


def calculate_prediction(student, persist=True):
    """
    Öğrenci için tahmini bitiş tarihini hesaplar.
    Dönüş: PredictionHistory instance (kaydedilmiş veya kaydedilmemiş) ya da None
    (öğrenci hafızlığını tamamladıysa ya da hiç veri yoksa).
    """
    total_pages = settings.TOTAL_QURAN_PAGES
    memorized = MemorizationPage.objects.filter(student=student).exclude(
        status=MemorizationPage.Status.NOT_STUDIED
    ).count()
    remaining_pages = max(total_pages - memorized, 0)

    today = timezone.localdate()

    if remaining_pages == 0:
        return None

    history_qs = PerformanceHistory.objects.filter(student=student).order_by("date")
    history = list(history_qs)

    if not history:
        return None

    days_elapsed = max((today - student.start_date).days, 1)
    attended_days = [h for h in history if h.attended]
    attendance_rate = len(attended_days) / len(history) if history else 1
    attendance_rate = max(attendance_rate, 0.2)  # aşırı düşük tahminleri engellemek için taban

    memorization_values = [h.daily_memorization for h in history if h.daily_memorization > 0]

    use_simple_average = days_elapsed <= settings.PREDICTION_SIMPLE_AVG_DAYS or len(history) < 5

    if use_simple_average:
        method = PredictionHistory.Method.SIMPLE_AVERAGE
        pace_per_active_day = (sum(memorization_values) / len(memorization_values)) if memorization_values else 0
    else:
        method = PredictionHistory.Method.EMA
        pace_per_active_day = _ema(memorization_values, settings.PREDICTION_EMA_ALPHA) if memorization_values else 0

    effective_daily_pace = pace_per_active_day * attendance_rate

    if effective_daily_pace <= 0:
        estimated_completion_date = None
        estimated_remaining_days = None
    else:
        estimated_remaining_days = int(round(remaining_pages / effective_daily_pace))
        estimated_completion_date = today + timedelta(days=estimated_remaining_days)

    confidence = _confidence_level(len(history), memorization_values)

    prediction = PredictionHistory(
        student=student,
        estimated_completion_date=estimated_completion_date,
        estimated_remaining_days=estimated_remaining_days,
        confidence_level=confidence,
        method_used=method,
        remaining_pages=remaining_pages,
        daily_pace=round(effective_daily_pace, 2),
    )
    if persist:
        prediction.save()
    return prediction
