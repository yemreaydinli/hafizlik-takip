"""
memorization app testleri.

Bu dosya özellikle memorization/services.py:is_juz_ham_covered() fonksiyonunu
doğrular -- has (tekrar) girişinin, ham'ı henüz tamamlanmamış bir cüz için
yanlışlıkla kabul edilmesini engelleyen kontrol.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.quran import juz_page_range
from lessons.models import LessonRecord
from students.models import Student

from .services import is_juz_ham_covered

User = get_user_model()


def make_student():
    teacher = User.objects.create_user(
        username="hoca-mem-test", password="test-pass-12345", role=User.Role.TEACHER
    )
    return Student.objects.create(
        full_name="Kontrol Test Öğrenci",
        start_date=date.today() - timedelta(days=50),
        teacher=teacher,
    )


class IsJuzHamCoveredTests(TestCase):
    def test_no_ham_at_all_returns_false(self):
        student = make_student()
        self.assertFalse(is_juz_ham_covered(student, juz_number=3))

    def test_partial_ham_returns_false(self):
        """Cüzün sadece bir kısmı ham olarak girilmişse (örn. 20 sayfalık cüzden
        sadece 10 sayfa) tam kapsanmış sayılmamalı."""
        student = make_student()
        start, _ = juz_page_range(3)
        LessonRecord.objects.create(
            student=student, date=date.today() - timedelta(days=5),
            ham_start_page=start, ham_end_page=start + 9,
        )
        self.assertFalse(is_juz_ham_covered(student, juz_number=3))

    def test_full_ham_across_multiple_lessons_returns_true(self):
        """Cüzün ham'ı birden fazla derste parça parça tamamlanmış olabilir --
        toplamda tüm sayfaları kapsıyorsa True dönmeli."""
        student = make_student()
        start, end = juz_page_range(3)
        mid = start + (end - start) // 2
        LessonRecord.objects.create(
            student=student, date=date.today() - timedelta(days=10),
            ham_start_page=start, ham_end_page=mid,
        )
        LessonRecord.objects.create(
            student=student, date=date.today() - timedelta(days=5),
            ham_start_page=mid + 1, ham_end_page=end,
        )
        self.assertTrue(is_juz_ham_covered(student, juz_number=3))

    def test_gap_in_middle_returns_false(self):
        """Baş ve son kısımlar ham yapılmış ama ortada bir boşluk varsa
        (örn. 1-5 ve 15-20 yapılmış ama 6-14 hiç yapılmamışsa) tam
        kapsanmamış sayılmalı -- salt 'en ileri sayfa' mantığının gözden
        kaçırdığı senaryo."""
        student = make_student()
        start, end = juz_page_range(3)
        LessonRecord.objects.create(
            student=student, date=date.today() - timedelta(days=10),
            ham_start_page=start, ham_end_page=start + 4,
        )
        LessonRecord.objects.create(
            student=student, date=date.today() - timedelta(days=2),
            ham_start_page=end - 5, ham_end_page=end,
        )
        self.assertFalse(is_juz_ham_covered(student, juz_number=3))

    def test_extra_ranges_covers_same_session_ham(self):
        """Aynı ders gönderiminde hem son ham sayfası hem o cüzün has'ı birlikte
        girilirse (henüz veritabanına kaydedilmeden), extra_ranges ile bu da
        hesaba katılmalı."""
        student = make_student()
        start, end = juz_page_range(3)
        LessonRecord.objects.create(
            student=student, date=date.today() - timedelta(days=5),
            ham_start_page=start, ham_end_page=end - 1,
        )
        self.assertFalse(is_juz_ham_covered(student, juz_number=3))
        self.assertTrue(
            is_juz_ham_covered(student, juz_number=3, extra_ranges=[(end, end)])
        )

    def test_exclude_lesson_id_avoids_double_counting_on_edit(self):
        """Bir ders düzenlenirken, o dersin ESKİ ham aralığı extra_ranges ile
        güncel değer olarak zaten geçirildiği için ayrıca DB sorgusuna
        dahil edilmemeli (aksi halde eski + yeni karışabilir)."""
        student = make_student()
        start, end = juz_page_range(3)
        lesson = LessonRecord.objects.create(
            student=student, date=date.today() - timedelta(days=1),
            ham_start_page=start, ham_end_page=start + 9,  # sadece yarısı
        )
        # exclude_lesson_id olmadan: DB'deki eski (yarım) değer sayılır -> False
        self.assertFalse(is_juz_ham_covered(student, juz_number=3, exclude_lesson_id=lesson.pk))
        # Kullanıcı formda aralığı tam cüzü kapsayacak şekilde genişletti (henüz kaydedilmedi):
        self.assertTrue(
            is_juz_ham_covered(
                student, juz_number=3, extra_ranges=[(start, end)], exclude_lesson_id=lesson.pk
            )
        )
