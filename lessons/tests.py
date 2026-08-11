"""
lessons app testleri.

Bu dosya özellikle şu regresyonları bir daha yaşamamak için yazıldı:
  - JuzTurCount'un ilgisiz bir cüz senkronize edildiğinde sıfırlanması,
  - seed_demo_data'nın sync_lesson'ı hiç çağırmaması,
  - Django admin panelinden ders/tekrar kaydı düzenlemenin sync_lesson'ı
    tetiklememesi.
sync_lesson() ve recompute_student_memorization()/_sync_juz_tur_counts()
idempotent olmak ZORUNDA olan, uygulamanın tek doğruluk kaynağı olan
fonksiyonlardır; buradaki testler bu sözleşmeyi korur.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from core.quran import juz_page_range
from memorization.models import JuzTurCount, MemorizationPage, RevisionRecord
from students.models import Student

from .models import LessonRecord, PerformanceHistory
from .signals import sync_lesson

User = get_user_model()


def make_teacher_and_student():
    teacher = User.objects.create_user(
        username="hoca-test", password="test-pass-12345", role=User.Role.TEACHER
    )
    student = Student.objects.create(
        full_name="Test Öğrenci",
        start_date=date.today() - timedelta(days=100),
        teacher=teacher,
    )
    return teacher, student


class SyncLessonTests(TestCase):
    """lessons/signals.py:sync_lesson ve yardımcılarının temel davranışları."""

    def setUp(self):
        self.teacher, self.student = make_teacher_and_student()

    def _create_lesson(self, day_offset, ham_start=None, ham_end=None):
        return LessonRecord.objects.create(
            student=self.student,
            date=date.today() - timedelta(days=day_offset),
            ham_start_page=ham_start,
            ham_end_page=ham_end,
        )

    def test_ham_only_lesson_marks_pages_needs_revision(self):
        lesson = self._create_lesson(5, 1, 5)
        sync_lesson(lesson)

        pages = MemorizationPage.objects.filter(student=self.student).order_by("page_number")
        self.assertEqual(pages.count(), 5)
        for page in pages:
            self.assertEqual(page.status, MemorizationPage.Status.NEEDS_REVISION)
            self.assertTrue(page.synced_from_lessons)

    def test_revision_marks_pages_completed_and_sets_juz_tur_count(self):
        lesson = self._create_lesson(5, 1, 20)  # 1. cüzün tamamı ham
        sync_lesson(lesson)

        start, end = juz_page_range(1)
        RevisionRecord.objects.create(lesson=lesson, start_page=start, end_page=end)
        sync_lesson(lesson)

        pages = MemorizationPage.objects.filter(student=self.student, page_number__range=(start, end))
        for page in pages:
            self.assertEqual(page.status, MemorizationPage.Status.COMPLETED)

        tur = JuzTurCount.objects.get(student=self.student, juz_number=1)
        self.assertEqual(tur.tur_count, 1)
        self.assertTrue(tur.synced_from_lessons)

    def test_recompute_is_idempotent(self):
        """Aynı senkronizasyon art arda çağrılırsa sayaçlar her seferinde
        artmamalı (eski davranışta revision_count her çağrıda +1 artıyordu)."""
        lesson = self._create_lesson(3, 1, 20)
        start, end = juz_page_range(1)
        RevisionRecord.objects.create(lesson=lesson, start_page=start, end_page=end)
        sync_lesson(lesson)

        first_tur_count = JuzTurCount.objects.get(student=self.student, juz_number=1).tur_count
        first_revision_count = MemorizationPage.objects.get(
            student=self.student, page_number=start
        ).revision_count

        sync_lesson(lesson)
        sync_lesson(lesson)

        self.assertEqual(
            JuzTurCount.objects.get(student=self.student, juz_number=1).tur_count, first_tur_count
        )
        self.assertEqual(
            MemorizationPage.objects.get(student=self.student, page_number=start).revision_count,
            first_revision_count,
        )

    def test_narrowing_ham_range_reverts_stale_pages(self):
        lesson = self._create_lesson(4, 1, 10)
        sync_lesson(lesson)
        self.assertEqual(
            MemorizationPage.objects.filter(
                student=self.student, status=MemorizationPage.Status.NEEDS_REVISION
            ).count(),
            10,
        )

        lesson.ham_end_page = 5
        lesson.save()
        sync_lesson(lesson)

        for page in MemorizationPage.objects.filter(student=self.student, page_number__range=(6, 10)):
            self.assertEqual(page.status, MemorizationPage.Status.NOT_STUDIED)
            self.assertIsNone(page.first_memorized_date)

    def test_deleting_lesson_reverts_pages_and_performance_history(self):
        lesson = self._create_lesson(2, 1, 5)
        sync_lesson(lesson)
        self.assertTrue(PerformanceHistory.objects.filter(student=self.student, date=lesson.date).exists())

        lesson.delete()

        for page in MemorizationPage.objects.filter(student=self.student, page_number__range=(1, 5)):
            self.assertEqual(page.status, MemorizationPage.Status.NOT_STUDIED)
        self.assertFalse(PerformanceHistory.objects.filter(student=self.student, date=lesson.date).exists())

    def test_manual_juz_tur_count_untouched_by_unrelated_juz_sync(self):
        """Regresyon: elle ('Başlangıç Durumu Aktarımı') ayarlanmış bir cüzün
        has-tekrar sayacı, İLGİSİZ bir cüz için ders eklenip senkronize
        edildiğinde sıfırlanmamalı (JuzTurCount sıfırlanması regresyonu)."""
        JuzTurCount.objects.create(
            student=self.student, juz_number=7, tur_count=3, synced_from_lessons=False
        )

        lesson = self._create_lesson(1, 21, 40)  # 2. cüz ham
        start, end = juz_page_range(2)
        RevisionRecord.objects.create(lesson=lesson, start_page=start, end_page=end)
        sync_lesson(lesson)

        manual = JuzTurCount.objects.get(student=self.student, juz_number=7)
        self.assertEqual(manual.tur_count, 3)
        self.assertFalse(manual.synced_from_lessons)

    def test_manual_juz_tur_count_reset_once_real_revision_recorded(self):
        """Aynı cüz için gerçek bir RevisionRecord girilince, elle ayarlanmış
        sayaç artık sync_lesson tarafından devralınıp yeniden hesaplanmalı."""
        JuzTurCount.objects.create(
            student=self.student, juz_number=2, tur_count=9, synced_from_lessons=False
        )
        lesson = self._create_lesson(1, 21, 40)
        start, end = juz_page_range(2)
        RevisionRecord.objects.create(lesson=lesson, start_page=start, end_page=end)
        sync_lesson(lesson)

        tur = JuzTurCount.objects.get(student=self.student, juz_number=2)
        self.assertTrue(tur.synced_from_lessons)
        self.assertEqual(tur.tur_count, 1)


class SeedDemoDataTests(TestCase):
    """Regresyon: seed_demo_data sync_lesson'ı çağırmıyordu, bu yüzden demo
    öğrencisi için Hafızlık Haritası/JuzTurCount hiç dolmuyor, tahmin motoru
    veri bulamıyordu."""

    def test_command_produces_synced_data(self):
        call_command("seed_demo_data")

        student = Student.objects.get(full_name="Yusuf Emre")
        self.assertTrue(MemorizationPage.objects.filter(student=student).exists())

        from predictions.models import PredictionHistory

        self.assertTrue(PredictionHistory.objects.filter(student=student).exists())


class AdminSyncTests(TestCase):
    """Regresyon: Django admin'den LessonRecord/RevisionRecord düzenlemek
    sync_lesson()'ı tetiklemiyordu (post_save sinyaline bağlı olmadığı için).
    lessons/admin.py:LessonRecordAdmin.save_related ve
    memorization/admin.py:RevisionRecordAdmin.save_model/delete_model bu
    testlerle korunur."""

    def setUp(self):
        self.teacher, self.student = make_teacher_and_student()
        self.admin_user = User.objects.create_superuser(
            username="admin-test", email="admin-test@example.com", password="admin-pass-12345"
        )
        self.client = Client()
        self.client.force_login(self.admin_user)

    def _lesson_admin_post_data(self, **overrides):
        data = {
            "student": self.student.pk,
            "date": (date.today() - timedelta(days=1)).isoformat(),
            "attendance": LessonRecord.Attendance.PRESENT,
            "ham_start_page": 1,
            "ham_end_page": 20,
            "pismis_done": "",
            "quality": "",
            "notes": "",
            "created_by": self.admin_user.pk,
            # RevisionRecordInline formset yönetim verisi (extra=1, boş satır)
            "revision_ranges-TOTAL_FORMS": "1",
            "revision_ranges-INITIAL_FORMS": "0",
            "revision_ranges-MIN_NUM_FORMS": "0",
            "revision_ranges-MAX_NUM_FORMS": "1000",
            "revision_ranges-0-start_page": "",
            "revision_ranges-0-end_page": "",
            "revision_ranges-0-id": "",
            "revision_ranges-0-lesson": "",
        }
        data.update(overrides)
        return data

    def test_admin_add_lesson_with_inline_revision_triggers_sync(self):
        start, end = juz_page_range(1)
        data = self._lesson_admin_post_data(**{
            "revision_ranges-0-start_page": str(start),
            "revision_ranges-0-end_page": str(end),
        })
        response = self.client.post(reverse("admin:lessons_lessonrecord_add"), data)
        self.assertEqual(
            response.status_code, 302,
            response.context["adminform"].form.errors if response.status_code == 200 else "",
        )

        lesson = LessonRecord.objects.get(student=self.student)
        self.assertTrue(RevisionRecord.objects.filter(lesson=lesson).exists())

        # sync_lesson admin tarafından tetiklenmiş olmalı: JuzTurCount ve
        # MemorizationPage(COMPLETED) admin akışından sonra elle sync_lesson
        # çağırmadan burada zaten var olmalı.
        self.assertTrue(JuzTurCount.objects.filter(student=self.student, juz_number=1, tur_count=1).exists())
        self.assertTrue(
            MemorizationPage.objects.filter(
                student=self.student, page_number__range=(start, end), status=MemorizationPage.Status.COMPLETED
            ).exists()
        )

    def test_admin_edit_lesson_narrowing_ham_range_reverts_pages(self):
        lesson = LessonRecord.objects.create(
            student=self.student, date=date.today() - timedelta(days=2), ham_start_page=1, ham_end_page=10
        )
        sync_lesson(lesson)
        self.assertTrue(
            MemorizationPage.objects.filter(
                student=self.student, page_number=10, status=MemorizationPage.Status.NEEDS_REVISION
            ).exists()
        )

        data = self._lesson_admin_post_data(
            date=lesson.date.isoformat(), ham_start_page=1, ham_end_page=5
        )
        response = self.client.post(
            reverse("admin:lessons_lessonrecord_change", args=[lesson.pk]), data
        )
        self.assertEqual(
            response.status_code, 302,
            response.context["adminform"].form.errors if response.status_code == 200 else "",
        )

        page10 = MemorizationPage.objects.get(student=self.student, page_number=10)
        self.assertEqual(page10.status, MemorizationPage.Status.NOT_STUDIED)

    def test_admin_standalone_revision_record_add_triggers_sync(self):
        lesson = LessonRecord.objects.create(
            student=self.student, date=date.today() - timedelta(days=1), ham_start_page=1, ham_end_page=20
        )
        sync_lesson(lesson)
        start, end = juz_page_range(1)

        response = self.client.post(
            reverse("admin:memorization_revisionrecord_add"),
            {"lesson": lesson.pk, "start_page": start, "end_page": end},
        )
        self.assertEqual(response.status_code, 302)

        self.assertTrue(JuzTurCount.objects.filter(student=self.student, juz_number=1, tur_count=1).exists())

    def test_admin_standalone_revision_record_delete_triggers_sync(self):
        lesson = LessonRecord.objects.create(
            student=self.student, date=date.today() - timedelta(days=1), ham_start_page=1, ham_end_page=20
        )
        start, end = juz_page_range(1)
        revision = RevisionRecord.objects.create(lesson=lesson, start_page=start, end_page=end)
        sync_lesson(lesson)
        self.assertTrue(JuzTurCount.objects.filter(student=self.student, juz_number=1, tur_count=1).exists())

        self.client.post(
            reverse("admin:memorization_revisionrecord_delete", args=[revision.pk]),
            {"post": "yes"},
        )

        tur = JuzTurCount.objects.get(student=self.student, juz_number=1)
        self.assertEqual(tur.tur_count, 0)


class PismisPageCountTests(TestCase):
    """Yeni eklenen pismis_page_count alanının kaydedilip formda gösterildiğini
    doğrular (düşük riskli ek alan)."""

    def setUp(self):
        self.teacher, self.student = make_teacher_and_student()

    def test_pismis_page_count_saved_and_optional(self):
        lesson = LessonRecord.objects.create(
            student=self.student,
            date=date.today(),
            pismis_done=True,
            pismis_page_count=7,
        )
        lesson.refresh_from_db()
        self.assertEqual(lesson.pismis_page_count, 7)

    def test_pismis_page_count_defaults_to_none(self):
        lesson = LessonRecord.objects.create(student=self.student, date=date.today())
        self.assertIsNone(lesson.pismis_page_count)

    def test_lesson_form_accepts_pismis_page_count(self):
        from .forms import LessonRecordForm

        form = LessonRecordForm(
            data={
                "date": date.today().isoformat(),
                "attendance": LessonRecord.Attendance.PRESENT,
                "ham_juz": "",
                "ham_start_page": "",
                "ham_end_page": "",
                "pismis_done": "on",
                "pismis_page_count": "4",
                "quality": "",
                "notes": "",
            },
            instance=LessonRecord(student=self.student),
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["pismis_page_count"], 4)


class HamCoverageGuardTests(TestCase):
    """
    lessons/views.py:_validate_ham_coverage_for_revisions() view-seviyesi
    testleri. Has (tekrar) girişi hâlâ tek bir cüz seçilerek yapılıyor
    (arayüz değiştirilmedi) -- bu testler sadece, ham'ı tamamlanmamış bir
    cüz için has girilmeye çalışıldığında kaydın ENGELLENDİĞİNİ ve
    tamamlanmış bir cüz için normal şekilde kaydedildiğini doğrular.
    """

    def setUp(self):
        self.teacher, self.student = make_teacher_and_student()
        self.client = Client()
        self.client.force_login(self.teacher)

    def _lesson_post_data(self, **overrides):
        data = {
            "date": date.today().isoformat(),
            "attendance": LessonRecord.Attendance.PRESENT,
            "ham_juz": "",
            "ham_start_page": "",
            "ham_end_page": "",
            "pismis_done": "",
            "pismis_page_count": "",
            "quality": "",
            "notes": "",
            "revision_ranges-TOTAL_FORMS": "1",
            "revision_ranges-INITIAL_FORMS": "0",
            "revision_ranges-MIN_NUM_FORMS": "0",
            "revision_ranges-MAX_NUM_FORMS": "1000",
            "revision_ranges-0-juz_number": "",
            "revision_ranges-0-start_page": "",
            "revision_ranges-0-end_page": "",
            "revision_ranges-0-id": "",
            "revision_ranges-0-lesson": "",
        }
        data.update(overrides)
        return data

    def test_has_blocked_when_juz_ham_never_entered(self):
        data = self._lesson_post_data(**{"revision_ranges-0-juz_number": "5"})
        response = self.client.post(
            reverse("lessons:create", kwargs={"student_pk": self.student.pk}), data
        )
        # Kaydedilmemeli -- formla aynı sayfada 200 dönmeli (redirect yok).
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LessonRecord.objects.filter(student=self.student).exists())
        self.assertIn(
            "ham",
            "".join(response.context["formset"].forms[0].errors.get("juz_number", [])).lower(),
        )

    def test_has_blocked_when_juz_ham_only_partially_entered(self):
        start, _ = juz_page_range(5)
        LessonRecord.objects.create(
            student=self.student, date=date.today() - timedelta(days=3),
            ham_start_page=start, ham_end_page=start + 9,  # cüzün sadece yarısı
        )
        data = self._lesson_post_data(**{"revision_ranges-0-juz_number": "5"})
        response = self.client.post(
            reverse("lessons:create", kwargs={"student_pk": self.student.pk}), data
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LessonRecord.objects.filter(student=self.student, date=date.today()).exists())

    def test_has_allowed_when_juz_ham_fully_covered_from_prior_lesson(self):
        start, end = juz_page_range(5)
        LessonRecord.objects.create(
            student=self.student, date=date.today() - timedelta(days=3),
            ham_start_page=start, ham_end_page=end,
        )
        data = self._lesson_post_data(**{"revision_ranges-0-juz_number": "5"})
        response = self.client.post(
            reverse("lessons:create", kwargs={"student_pk": self.student.pk}), data
        )
        self.assertEqual(response.status_code, 302)
        lesson = LessonRecord.objects.get(student=self.student, date=date.today())
        self.assertTrue(RevisionRecord.objects.filter(lesson=lesson).exists())

    def test_has_allowed_when_ham_completes_juz_in_same_submission(self):
        """Aynı dersin ham'ı, cüzün son eksik parçasını tamamlıyorsa (aynı
        gönderimde), has girişi de kabul edilmeli."""
        juz = 6
        start, end = juz_page_range(juz)
        LessonRecord.objects.create(
            student=self.student, date=date.today() - timedelta(days=1),
            ham_start_page=start, ham_end_page=end - 1,  # son sayfa hariç
        )
        from core.quran import absolute_to_local_page
        data = self._lesson_post_data(**{
            "ham_juz": str(juz),
            "ham_start_page": str(absolute_to_local_page(end)),
            "ham_end_page": str(absolute_to_local_page(end)),
            "revision_ranges-0-juz_number": str(juz),
        })
        response = self.client.post(
            reverse("lessons:create", kwargs={"student_pk": self.student.pk}), data
        )
        self.assertEqual(response.status_code, 302)

    def test_editing_lesson_does_not_falsely_block_its_own_prior_has(self):
        """Zaten kayıtlı, geçerli bir has kaydını (ham'ı tam olan bir cüz için)
        düzenlerken exclude_lesson_id yanlış pozitif üretmemeli."""
        start, end = juz_page_range(7)
        ham_lesson = LessonRecord.objects.create(
            student=self.student, date=date.today() - timedelta(days=5),
            ham_start_page=start, ham_end_page=end,
        )
        has_lesson = LessonRecord.objects.create(
            student=self.student, date=date.today() - timedelta(days=1),
        )
        RevisionRecord.objects.create(lesson=has_lesson, start_page=start, end_page=end)

        data = self._lesson_post_data(
            date=has_lesson.date.isoformat(),
            **{
                "revision_ranges-INITIAL_FORMS": "1",
                "revision_ranges-0-juz_number": "7",
                "revision_ranges-0-id": str(RevisionRecord.objects.get(lesson=has_lesson).pk),
                "revision_ranges-0-lesson": str(has_lesson.pk),
            },
        )
        response = self.client.post(reverse("lessons:update", kwargs={"pk": has_lesson.pk}), data)
        self.assertEqual(response.status_code, 302)
