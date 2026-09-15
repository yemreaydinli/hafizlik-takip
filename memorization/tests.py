"""
memorization app testleri.

Bu dosya özellikle memorization/services.py:is_juz_ham_covered() fonksiyonunu
doğrular -- has (tekrar) girişinin, ham'ı henüz tamamlanmamış bir cüz için
yanlışlıkla kabul edilmesini engelleyen kontrol. "Ham yapılmış" bilgisi
MemorizationPage.status üzerinden okunur; bu yüzden hem normal ders kaydı
hem de Başlangıç Durumu Aktarımı (bulk_apply_range) üzerinden gelen veriyi
doğru tanıması ayrıca test edilir (bkz. is_juz_ham_covered docstring'i).
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.quran import juz_page_range
from lessons.models import LessonRecord
from lessons.signals import sync_lesson
from students.models import Student

from .models import MemorizationPage
from .services import bulk_apply_range, is_juz_ham_covered

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


def make_ham_lesson(student, ham_start, ham_end, day_offset=5):
    """Gerçek akışta olduğu gibi (view -> sync_lesson) bir ham dersi oluşturur
    ve MemorizationPage'e senkronize eder."""
    lesson = LessonRecord.objects.create(
        student=student, date=date.today() - timedelta(days=day_offset),
        ham_start_page=ham_start, ham_end_page=ham_end,
    )
    sync_lesson(lesson)
    return lesson


class IsJuzHamCoveredTests(TestCase):
    def test_no_ham_at_all_returns_false(self):
        student = make_student()
        self.assertFalse(is_juz_ham_covered(student, juz_number=3))

    def test_partial_ham_returns_false(self):
        """Cüzün sadece bir kısmı ham olarak girilmişse (örn. 20 sayfalık cüzden
        sadece 10 sayfa) tam kapsanmış sayılmamalı."""
        student = make_student()
        start, _ = juz_page_range(3)
        make_ham_lesson(student, start, start + 9)
        self.assertFalse(is_juz_ham_covered(student, juz_number=3))

    def test_full_ham_across_multiple_lessons_returns_true(self):
        """Cüzün ham'ı birden fazla derste parça parça tamamlanmış olabilir --
        toplamda tüm sayfaları kapsıyorsa True dönmeli."""
        student = make_student()
        start, end = juz_page_range(3)
        mid = start + (end - start) // 2
        make_ham_lesson(student, start, mid, day_offset=10)
        make_ham_lesson(student, mid + 1, end, day_offset=5)
        self.assertTrue(is_juz_ham_covered(student, juz_number=3))

    def test_gap_in_middle_returns_false(self):
        """Baş ve son kısımlar ham yapılmış ama ortada bir boşluk varsa
        (örn. 1-5 ve 15-20 yapılmış ama 6-14 hiç yapılmamışsa) tam
        kapsanmamış sayılmalı -- salt 'en ileri sayfa' mantığının gözden
        kaçırdığı senaryo."""
        student = make_student()
        start, end = juz_page_range(3)
        make_ham_lesson(student, start, start + 4, day_offset=10)
        make_ham_lesson(student, end - 5, end, day_offset=2)
        self.assertFalse(is_juz_ham_covered(student, juz_number=3))

    def test_extra_ranges_covers_same_session_ham(self):
        """Aynı ders gönderiminde hem son ham sayfası hem o cüzün has'ı birlikte
        girilirse (henüz veritabanına/MemorizationPage'e yansımadan), bu da
        extra_ranges ile hesaba katılmalı."""
        student = make_student()
        start, end = juz_page_range(3)
        make_ham_lesson(student, start, end - 1)
        self.assertFalse(is_juz_ham_covered(student, juz_number=3))
        self.assertTrue(
            is_juz_ham_covered(student, juz_number=3, extra_ranges=[(end, end)])
        )

    def test_bulk_transferred_pages_count_as_ham_covered(self):
        """
        Regresyon: Öğrenci sisteme kaydedilmeden ÖNCE zaten ezberlediği cüzler
        "Başlangıç Durumu Aktarımı" (bkz. memorization/views.py:
        MemorizationMapView.post, bulk_apply_range()) ile TOPLU olarak
        işaretlenir -- bilerek hiçbir LessonRecord oluşturmadan (aksi halde
        büyük miktarda geçmiş ezber, tahmin motorunun günlük ham hızını yapay
        şekilde şişirirdi). is_juz_ham_covered bu durumda hâlâ True dönmeli;
        aksi halde bu öğrenciler için normal ders formundan has girmek
        yanlışlıkla HER ZAMAN engellenir.
        """
        student = make_student()
        bulk_apply_range(
            student, *juz_page_range(4), status=MemorizationPage.Status.NEEDS_REVISION
        )
        # Hiç LessonRecord oluşturulmadı:
        self.assertFalse(LessonRecord.objects.filter(student=student).exists())
        self.assertTrue(is_juz_ham_covered(student, juz_number=4))

    def test_bulk_transfer_with_completed_status_also_covered(self):
        student = make_student()
        bulk_apply_range(
            student, *juz_page_range(2), status=MemorizationPage.Status.COMPLETED
        )
        self.assertTrue(is_juz_ham_covered(student, juz_number=2))
