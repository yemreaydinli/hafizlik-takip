"""Akıllı Uyarı Sistemi: duraklama, devamsızlık, performans düşüşü, hedef sapması."""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from lessons.models import LessonRecord, PerformanceHistory
from predictions.services import calculate_prediction
from students.models import Student
from .models import Notification


def _already_alerted_recently(student, alert_type, within_days=1):
    threshold = timezone.now() - timedelta(days=within_days)
    return Notification.objects.filter(
        student=student, type=alert_type, created_at__gte=threshold
    ).exists()


def _create(student, alert_type, message):
    if _already_alerted_recently(student, alert_type):
        return None
    return Notification.objects.create(
        student=student, teacher=student.teacher, type=alert_type, message=message
    )


def _check_pause(student, today):
    last_active = LessonRecord.objects.filter(
        student=student, ham_start_page__isnull=False
    ).order_by("-date").first()
    reference_date = last_active.date if last_active else student.start_date
    idle_days = (today - reference_date).days
    if idle_days >= settings.ALERT_PAUSE_DAYS:
        _create(
            student, Notification.Type.PAUSE,
            f"{student.full_name} için {idle_days} gündür yeni ham girilmedi."
        )


def _check_absence(student):
    recent = LessonRecord.objects.filter(student=student).order_by("-date")[:10]
    consecutive = 0
    for record in recent:
        if record.attendance == LessonRecord.Attendance.ABSENT:
            consecutive += 1
        else:
            break
    if consecutive >= settings.ALERT_CONSECUTIVE_ABSENCE:
        _create(
            student, Notification.Type.ABSENCE,
            f"{student.full_name} ardışık {consecutive} gündür derse gelmedi."
        )


def _check_performance_drop(student):
    history = list(
        PerformanceHistory.objects.filter(student=student).order_by("-date")[:14]
    )
    if len(history) < 8:
        return
    recent_week = history[:7]
    previous_week = history[7:14]
    recent_avg = sum(h.daily_memorization for h in recent_week) / len(recent_week)
    previous_avg = sum(h.daily_memorization for h in previous_week) / max(len(previous_week), 1)
    if previous_avg <= 0:
        return
    drop_ratio = (previous_avg - recent_avg) / previous_avg
    if drop_ratio >= settings.ALERT_PERFORMANCE_DROP_RATIO:
        _create(
            student, Notification.Type.PERFORMANCE_DROP,
            f"{student.full_name} için son haftadaki ezber hızı %{round(drop_ratio * 100)} düştü."
        )


def _check_target_deviation(student, today):
    if not student.target_completion_date:
        return
    prediction = calculate_prediction(student, persist=False)
    if not prediction or not prediction.estimated_completion_date:
        return
    deviation_days = (prediction.estimated_completion_date - student.target_completion_date).days
    if abs(deviation_days) >= settings.ALERT_TARGET_DEVIATION_DAYS:
        direction = "gecikme" if deviation_days > 0 else "erken tamamlama"
        _create(
            student, Notification.Type.TARGET_DEVIATION,
            f"{student.full_name} için tahmini bitiş, hedeften {abs(deviation_days)} gün {direction} gösteriyor."
        )


def generate_alerts_for_student(student):
    today = timezone.localdate()
    if student.status != Student.Status.ACTIVE:
        return
    _check_pause(student, today)
    _check_absence(student)
    _check_performance_drop(student)
    _check_target_deviation(student, today)


def generate_alerts_for_all():
    for student in Student.objects.filter(status=Student.Status.ACTIVE):
        generate_alerts_for_student(student)
