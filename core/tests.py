import json
from datetime import date, timedelta

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core.backup import get_backup_status
from core.models import BackupLog
from students.models import Student


class BackupTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("yonetici", password="x", role=User.Role.ADMIN)
        cls.teacher = User.objects.create_user("hoca", password="x", role=User.Role.TEACHER)

    def add_student(self):
        return Student.objects.create(full_name="Test Öğrenci", start_date=date.today(), teacher=self.teacher)

    def make_old_backup(self, days):
        log = BackupLog.objects.create(created_by=self.admin)
        BackupLog.objects.filter(pk=log.pk).update(created_at=timezone.now() - timedelta(days=days))


class BackupStatusTests(BackupTestBase):
    def test_no_warning_when_no_data(self):
        self.assertFalse(get_backup_status()["warn"])

    def test_warning_when_data_exists_and_never_backed_up(self):
        self.add_student()
        s = get_backup_status()
        self.assertTrue(s["warn"])
        self.assertIsNone(s["last"])

    def test_no_warning_with_recent_backup(self):
        self.add_student()
        self.make_old_backup(2)
        self.assertFalse(get_backup_status()["warn"])

    @override_settings(BACKUP_WARNING_DAYS=7)
    def test_warning_when_backup_too_old(self):
        self.add_student()
        self.make_old_backup(8)
        s = get_backup_status()
        self.assertTrue(s["warn"])
        self.assertEqual(s["days_since"], 8)

    @override_settings(BACKUP_WARNING_DAYS=3)
    def test_threshold_is_configurable(self):
        self.add_student()
        self.make_old_backup(4)
        self.assertTrue(get_backup_status()["warn"])


class BackupViewTests(BackupTestBase):
    def test_anonymous_redirected_to_login(self):
        r = self.client.get(reverse("core:backup"))
        self.assertEqual(r.status_code, 302)
        r = self.client.post(reverse("core:backup"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(BackupLog.objects.count(), 0)

    def test_teacher_forbidden(self):
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(reverse("core:backup")).status_code, 403)
        self.assertEqual(self.client.post(reverse("core:backup")).status_code, 403)
        self.assertEqual(BackupLog.objects.count(), 0)

    def test_get_does_not_create_backup(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("core:backup")).status_code, 200)
        self.assertEqual(BackupLog.objects.count(), 0)

    def test_post_downloads_valid_json_and_logs(self):
        self.add_student()
        self.client.force_login(self.admin)
        r = self.client.post(reverse("core:backup"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r["Content-Disposition"])
        self.assertIn("hafizlik-yedek-", r["Content-Disposition"])
        data = json.loads(r.content)
        models_in_backup = {row["model"] for row in data}
        self.assertIn("students.student", models_in_backup)
        self.assertIn("accounts.user", models_in_backup)
        self.assertNotIn("sessions.session", models_in_backup)
        self.assertNotIn("core.backuplog", models_in_backup)
        log = BackupLog.objects.get()
        self.assertEqual(log.created_by, self.admin)
        self.assertEqual(log.record_count, len(data))

    def test_backup_can_be_restored(self):
        student = self.add_student()
        self.client.force_login(self.admin)
        data = self.client.post(reverse("core:backup")).content
        Student.objects.all().delete()
        self.assertEqual(Student.objects.count(), 0)
        import tempfile, os
        with tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False) as f:
            f.write(data)
            path = f.name
        try:
            call_command("loaddata", path, verbosity=0)
        finally:
            os.unlink(path)
        restored = Student.objects.get()
        self.assertEqual(restored.pk, student.pk)
        self.assertEqual(restored.full_name, "Test Öğrenci")


class BackupBannerTests(BackupTestBase):
    def test_banner_shown_to_admin_when_overdue(self):
        self.add_student()
        self.client.force_login(self.admin)
        r = self.client.get(reverse("core:dashboard"))
        self.assertContains(r, "YEDEK ALINMADI")

    def test_banner_hidden_from_teacher(self):
        self.add_student()
        self.client.force_login(self.teacher)
        r = self.client.get(reverse("core:dashboard"))
        self.assertNotContains(r, "YEDEK ALINMADI")

    def test_banner_gone_after_backup(self):
        self.add_student()
        self.client.force_login(self.admin)
        self.client.post(reverse("core:backup"))
        r = self.client.get(reverse("core:dashboard"))
        self.assertNotContains(r, "YEDEK ALINMADI")
