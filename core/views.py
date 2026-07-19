from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.utils import timezone
from django.views.generic import TemplateView

from lessons.models import LessonRecord, PerformanceHistory
from memorization.models import MemorizationPage
from notifications.models import Notification
from predictions.models import PredictionHistory
from students.models import Student


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def _scope(self, qs, field="teacher"):
        if self.request.user.is_admin_role:
            return qs
        lookup = {field: self.request.user} if field == "teacher" else {f"student__{field}": self.request.user}
        return qs.filter(**lookup)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        students = Student.objects.all() if user.is_admin_role else Student.objects.filter(teacher=user)
        active_students = students.filter(status=Student.Status.ACTIVE)

        today_lessons = LessonRecord.objects.filter(student__in=students, date=today)
        today_present = today_lessons.filter(attendance=LessonRecord.Attendance.PRESENT).count()
        today_absent = today_lessons.filter(attendance=LessonRecord.Attendance.ABSENT).count()

        month_start = today.replace(day=1)
        month_completed_pages = MemorizationPage.objects.filter(
            student__in=students,
            status=MemorizationPage.Status.COMPLETED,
            last_revised_date__gte=month_start,
        ).count()

        upcoming = []
        for s in active_students:
            latest_pred = s.predictions.first()
            if latest_pred and latest_pred.estimated_remaining_days is not None:
                upcoming.append((s, latest_pred))
        upcoming.sort(key=lambda x: x[1].estimated_remaining_days)
        upcoming = upcoming[:5]

        alerts = Notification.objects.filter(student__in=students, is_read=False)[:8]

        ctx.update({
            "total_students": students.count(),
            "active_students": active_students.count(),
            "today_present": today_present,
            "today_absent": today_absent,
            "today_ham_total": today_lessons.aggregate(
                total=Sum("ham_end_page")
            )["total"] or 0,  # basit gösterim; detaylı hesap performans geçmişinden alınır
            "today_ham_pages": sum(l.ham_page_count for l in today_lessons),
            "today_revision_pages": sum(l.revision_page_count for l in today_lessons),
            "month_completed_pages": month_completed_pages,
            "upcoming_completions": upcoming,
            "alerts": alerts,
        })
        return ctx
