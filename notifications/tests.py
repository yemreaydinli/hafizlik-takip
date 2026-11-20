from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from students.models import Student

from .models import Notification


class MarkReadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("yonetici", password="x", role=User.Role.ADMIN)
        cls.t1 = User.objects.create_user("hoca1", password="x", role=User.Role.TEACHER)
        cls.t2 = User.objects.create_user("hoca2", password="x", role=User.Role.TEACHER)
        cls.s1 = Student.objects.create(full_name="Öğrenci 1", start_date=date.today(), teacher=cls.t1)
        cls.s2 = Student.objects.create(full_name="Öğrenci 2", start_date=date.today(), teacher=cls.t2)

    def _make(self, student, teacher, n=2):
        return [
            Notification.objects.create(student=student, teacher=teacher, type=Notification.Type.PAUSE, message=f"m{i}")
            for i in range(n)
        ]

    def test_mark_all_only_affects_own_notifications(self):
        self._make(self.s1, self.t1, 3)
        self._make(self.s2, self.t2, 2)
        self.client.force_login(self.t1)
        resp = self.client.post(reverse("notifications:mark_all_read"))
        self.assertRedirects(resp, reverse("notifications:list"))
        self.assertEqual(Notification.objects.filter(teacher=self.t1, is_read=False).count(), 0)
        self.assertEqual(Notification.objects.filter(teacher=self.t2, is_read=False).count(), 2)

    def test_admin_marks_everything(self):
        self._make(self.s1, self.t1)
        self._make(self.s2, self.t2)
        self.client.force_login(self.admin)
        self.client.post(reverse("notifications:mark_all_read"))
        self.assertFalse(Notification.objects.filter(is_read=False).exists())

    def test_mark_all_requires_post_and_login(self):
        self._make(self.s1, self.t1)
        self.client.force_login(self.t1)
        self.assertEqual(self.client.get(reverse("notifications:mark_all_read")).status_code, 405)
        self.assertEqual(Notification.objects.filter(is_read=False).count(), 2)
        self.client.logout()
        resp = self.client.post(reverse("notifications:mark_all_read"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/hesap/giris/", resp["Location"])

    def test_mark_single_rejects_get_anonymous_and_foreign(self):
        n = self._make(self.s2, self.t2, 1)[0]
        url = reverse("notifications:mark_read", args=[n.pk])
        self.assertEqual(self.client.post(url).status_code, 302)  # anonim -> login
        self.client.force_login(self.t1)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 404)  # başkasının bildirimi
        n.refresh_from_db()
        self.assertFalse(n.is_read)
        self.client.force_login(self.t2)
        self.client.post(url)
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    def test_button_shown_only_when_unread_exist(self):
        self.client.force_login(self.t1)
        self.assertNotContains(self.client.get(reverse("notifications:list")), "Tümünü okundu yap")
        self._make(self.s1, self.t1, 2)
        self.assertContains(self.client.get(reverse("notifications:list")), "Tümünü okundu yap (2)")
