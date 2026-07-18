from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

from lessons.models import LessonRecord
from students.models import Student
from . import services


def _scoped_students(user):
    return Student.objects.all() if user.is_admin_role else Student.objects.filter(teacher=user)


class ReportIndexView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "reports/index.html")


REPORT_BUILDERS = {
    "daily": ("Günlük Rapor", lambda user, start, end: services.lesson_rows_and_headers(
        LessonRecord.objects.filter(student__in=_scoped_students(user), date=start)
    )),
    "weekly": ("Haftalık Rapor", lambda user, start, end: services.lesson_rows_and_headers(
        LessonRecord.objects.filter(student__in=_scoped_students(user), date__range=[start, end])
    )),
    "monthly": ("Aylık Rapor", lambda user, start, end: services.lesson_rows_and_headers(
        LessonRecord.objects.filter(student__in=_scoped_students(user), date__range=[start, end])
    )),
    "attendance": ("Devamsızlık Raporu", lambda user, start, end: services.attendance_rows_and_headers(
        _scoped_students(user)
    )),
    "progress": ("Hafızlık İlerleme Raporu", lambda user, start, end: services.progress_rows_and_headers(
        _scoped_students(user)
    )),
    "prediction": ("Tahmini Bitiş Raporu", lambda user, start, end: services.prediction_rows_and_headers(
        _scoped_students(user)
    )),
}


class GenerateReportView(LoginRequiredMixin, View):
    def get(self, request):
        report_type = request.GET.get("type", "daily")
        fmt = request.GET.get("format", "pdf")
        start_str = request.GET.get("start")
        end_str = request.GET.get("end")

        today = date.today()
        start = date.fromisoformat(start_str) if start_str else today
        end = date.fromisoformat(end_str) if end_str else today

        if report_type not in REPORT_BUILDERS:
            return HttpResponse("Geçersiz rapor türü", status=400)

        title, builder = REPORT_BUILDERS[report_type]
        headers, rows = builder(request.user, start, end)
        subtitle = f"{start.strftime('%d.%m.%Y')} - {end.strftime('%d.%m.%Y')}" if report_type in ("weekly", "monthly", "daily") else None

        filename = f"{report_type}_rapor"
        if fmt == "excel":
            buffer = services.build_excel_table(title, headers, rows)
            response = HttpResponse(
                buffer.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f"attachment; filename={filename}.xlsx"
        else:
            buffer = services.build_pdf_table(title, headers, rows, subtitle=subtitle)
            response = HttpResponse(buffer.read(), content_type="application/pdf")
            response["Content-Disposition"] = f"attachment; filename={filename}.pdf"
        return response
