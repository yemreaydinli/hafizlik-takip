from datetime import date

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from accounts.models import User
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


CONFIRM_PHRASE = "SİSTEMİ SIFIRLA"


class SystemResetView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Kabuk (shell) erişimi olmadan, tamamen web üzerinden tüm deneme/demo verilerini
    (öğrenciler, ders kayıtları, hafızlık haritaları, tahminler, uyarılar ve TÜM
    kullanıcılar) silip yerine tek bir gerçek yönetici hesabı oluşturur.

    Yalnızca 'admin' rolündeki kullanıcılar erişebilir. Geri alınamaz bir işlemdir;
    bu yüzden hem onay metninin birebir yazılmasını hem de yeni yönetici bilgilerinin
    aynı formda girilmesini zorunlu kılar.
    """

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin_role

    def get(self, request):
        return render(request, "core/system_reset.html", {"confirm_phrase": CONFIRM_PHRASE})

    def post(self, request):
        confirm_text = request.POST.get("confirm_text", "").strip()
        new_username = request.POST.get("new_username", "").strip()
        new_password = request.POST.get("new_password", "")
        new_password_repeat = request.POST.get("new_password_repeat", "")
        new_email = request.POST.get("new_email", "").strip()

        errors = []
        if confirm_text != CONFIRM_PHRASE:
            errors.append(f"Onay metnini birebir '{CONFIRM_PHRASE}' şeklinde yazmalısınız.")
        if not new_username:
            errors.append("Yeni yönetici kullanıcı adı zorunludur.")
        if len(new_password) < 8:
            errors.append("Yeni şifre en az 8 karakter olmalıdır.")
        if new_password != new_password_repeat:
            errors.append("Şifreler birbiriyle eşleşmiyor.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "core/system_reset.html", {
                "confirm_phrase": CONFIRM_PHRASE,
                "new_username": new_username,
                "new_email": new_email,
            })

        # 1) Tüm öğrenci verilerini sil (ders kayıtları, hafızlık haritası, tahminler,
        #    uyarılar student FK'sinde CASCADE olduğu için otomatik silinir).
        Student.objects.all().delete()

        # 2) Tüm kullanıcıları (demo yönetici/öğretici dahil) sil.
        User.objects.all().delete()

        # 3) Yeni, gerçek yönetici hesabını oluştur.
        new_admin = User.objects.create_superuser(
            username=new_username,
            email=new_email,
            password=new_password,
        )
        new_admin.role = User.Role.ADMIN
        new_admin.save(update_fields=["role"])

        # Mevcut oturum artık silinmiş bir kullanıcıya ait; güvenli şekilde çıkış yaptır.
        logout(request)
        messages.success(
            request,
            f"Sistem başarıyla sıfırlandı. '{new_username}' kullanıcı adıyla giriş yapabilirsiniz.",
        )
        return redirect(reverse("accounts:login"))
