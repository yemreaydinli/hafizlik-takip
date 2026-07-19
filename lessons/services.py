"""Devam/Yoklama istatistikleri servisleri."""
from datetime import timedelta

from django.utils import timezone

from .models import LessonRecord


def get_attendance_summary(student):
    qs = LessonRecord.objects.filter(student=student)
    total = qs.count()
    present = qs.filter(attendance=LessonRecord.Attendance.PRESENT).count()
    absent = qs.filter(attendance=LessonRecord.Attendance.ABSENT).count()
    excused = qs.filter(attendance=LessonRecord.Attendance.EXCUSED).count()

    today = timezone.localdate()
    monthly_absent = qs.filter(
        attendance=LessonRecord.Attendance.ABSENT,
        date__year=today.year,
        date__month=today.month,
    ).count()

    consecutive_absent = 0
    for record in qs.order_by("-date")[:15]:
        if record.attendance == LessonRecord.Attendance.ABSENT:
            consecutive_absent += 1
        else:
            break

    attendance_percent = round((present / total) * 100, 1) if total else 0

    return {
        "total": total,
        "present": present,
        "absent": absent,
        "excused": excused,
        "monthly_absent": monthly_absent,
        "consecutive_absent": consecutive_absent,
        "attendance_percent": attendance_percent,
    }


def get_recent_performance_series(student, days=30):
    """Grafik için son N güne ait günlük ham/tekrar sayfa sayılarını döndürür."""
    from .models import PerformanceHistory

    since = timezone.localdate() - timedelta(days=days)
    records = PerformanceHistory.objects.filter(student=student, date__gte=since).order_by("date")
    return [
        {
            "date": r.date.strftime("%d.%m"),
            "memorization": r.daily_memorization,
            "revision": r.daily_revision,
        }
        for r in records
    ]
