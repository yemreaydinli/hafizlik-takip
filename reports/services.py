"""PDF (reportlab) ve Excel (openpyxl) rapor üretim servisleri."""
import io

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


def build_pdf_table(title, headers, rows, subtitle=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Title"])]
    if subtitle:
        elements.append(Paragraph(subtitle, styles["Normal"]))
    elements.append(Spacer(1, 0.5 * cm))

    data = [headers] + rows if rows else [headers, ["Kayıt bulunamadı"] + [""] * (len(headers) - 1)]
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065f46")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer


def build_excel_table(title, headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31] if title else "Rapor"

    ws.append(headers)
    header_fill = PatternFill(start_color="065F46", end_color="065F46", fill_type="solid")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill

    for row in rows:
        ws.append(row)

    for column_cells in ws.columns:
        length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = min(max(length + 2, 12), 40)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def lesson_rows_and_headers(lessons):
    headers = ["Öğrenci", "Tarih", "Devam", "Ham Sayfa Sayısı", "Tekrar Sayfa Sayısı", "Kalite", "Not"]
    rows = []
    for lesson in lessons:
        rows.append([
            lesson.student.full_name,
            lesson.date.strftime("%d.%m.%Y"),
            lesson.get_attendance_display(),
            lesson.ham_page_count,
            lesson.revision_page_count,
            lesson.get_quality_display() if lesson.quality else "-",
            (lesson.notes or "")[:60],
        ])
    return headers, rows


def attendance_rows_and_headers(students):
    from lessons.models import LessonRecord
    headers = ["Öğrenci", "Toplam Ders", "Geldi", "Gelmedi", "İzinli", "Devam Yüzdesi (%)"]
    rows = []
    for s in students:
        qs = LessonRecord.objects.filter(student=s)
        total = qs.count()
        present = qs.filter(attendance=LessonRecord.Attendance.PRESENT).count()
        absent = qs.filter(attendance=LessonRecord.Attendance.ABSENT).count()
        excused = qs.filter(attendance=LessonRecord.Attendance.EXCUSED).count()
        pct = round((present / total) * 100, 1) if total else 0
        rows.append([s.full_name, total, present, absent, excused, pct])
    return headers, rows


def progress_rows_and_headers(students):
    from memorization.services import get_progress_summary
    headers = ["Öğrenci", "Toplam Sayfa", "Tamamlanan", "Tekrar Bekleyen", "Çalışılmadı", "İlerleme (%)"]
    rows = []
    for s in students:
        summary = get_progress_summary(s)
        rows.append([
            s.full_name, summary["total_pages"], summary["completed"],
            summary["needs_revision"], summary["not_studied"], summary["progress_percent"],
        ])
    return headers, rows


def prediction_rows_and_headers(students):
    headers = ["Öğrenci", "Kalan Sayfa", "Tahmini Kalan Gün", "Tahmini Bitiş Tarihi", "Güven Seviyesi", "Yöntem"]
    rows = []
    for s in students:
        pred = s.predictions.first()
        if not pred:
            rows.append([s.full_name, "-", "-", "-", "-", "-"])
            continue
        rows.append([
            s.full_name, pred.remaining_pages, pred.estimated_remaining_days or "-",
            pred.estimated_completion_date.strftime("%d.%m.%Y") if pred.estimated_completion_date else "-",
            pred.get_confidence_level_display(), pred.get_method_used_display(),
        ])
    return headers, rows
