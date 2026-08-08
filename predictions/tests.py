"""
predictions app testleri.

Bu dosya, Cüz/Tur/Pişmiş sistemine geçiş sonrası güncellenen
predictions/services.py:calculate_prediction() algoritmasının iki hatlı
(ham/has) mantığını doğrular:
  - Has tamamlanmadan tahmin bitmemeli (eski davranış: sadece ham bakardı).
  - Doğru koşullarda ham VEYA has darboğaz (bottleneck) olarak seçilebilmeli.
  - Güven seviyesi artık has verisinin yeterliliğine de bakmalı.
"""
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from core.quran import TOTAL_JUZ
from lessons.models import PerformanceHistory
from memorization.models import MemorizationPage
from students.models import Student

from .models import PredictionHistory
from .services import calculate_prediction

User = get_user_model()


def make_student():
    teacher = User.objects.create_user(
        username="hoca-pred-test", password="test-pass-12345", role=User.Role.TEACHER
    )
    return Student.objects.create(
        full_name="Tahmin Test Öğrenci",
        start_date=date.today() - timedelta(days=200),
        teacher=teacher,
    )


def make_pages(student, needs_revision_count, completed_count):
    """page_number 1'den başlayarak sırayla `completed_count` kadar COMPLETED,
    ardından `needs_revision_count` kadar NEEDS_REVISION sayfa oluşturur."""
    pages = []
    page_no = 1
    for _ in range(completed_count):
        pages.append(MemorizationPage(
            student=student, page_number=page_no, status=MemorizationPage.Status.COMPLETED,
            synced_from_lessons=True,
        ))
        page_no += 1
    for _ in range(needs_revision_count):
        pages.append(MemorizationPage(
            student=student, page_number=page_no, status=MemorizationPage.Status.NEEDS_REVISION,
            synced_from_lessons=True,
        ))
        page_no += 1
    MemorizationPage.objects.bulk_create(pages)


def make_history(student, days, daily_memorization=0, daily_revision=0, attended=True):
    """`days` günlük eşit değerli PerformanceHistory kaydı üretir."""
    records = []
    for i in range(days):
        records.append(PerformanceHistory(
            student=student,
            date=date.today() - timedelta(days=days - i),
            daily_memorization=daily_memorization,
            daily_revision=daily_revision,
            attended=attended,
            quality_score=80,
        ))
    PerformanceHistory.objects.bulk_create(records)


class DualPhasePredictionTests(TestCase):
    def test_fully_hafiz_returns_none(self):
        student = make_student()
        make_pages(student, needs_revision_count=0, completed_count=settings.TOTAL_QURAN_PAGES)
        make_history(student, days=10, daily_memorization=5, daily_revision=20)

        self.assertIsNone(calculate_prediction(student, persist=False))

    def test_ham_finished_only_has_remaining_uses_has_track(self):
        """Ham tamamen bitmiş (remaining_ham_pages=0), sadece has kaldıysa,
        tahmin doğrudan has hızına göre yapılmalı (eski algoritma bu durumda
        pace=0 bulup hiç tahmin veremezdi)."""
        student = make_student()
        make_pages(
            student,
            needs_revision_count=100,  # ham yapılmış ama henüz pişmemiş
            completed_count=settings.TOTAL_QURAN_PAGES - 100,
        )
        make_history(student, days=10, daily_memorization=0, daily_revision=10)

        prediction = calculate_prediction(student, persist=False)
        self.assertIsNotNone(prediction)
        self.assertEqual(prediction.remaining_ham_pages, 0)
        self.assertEqual(prediction.remaining_has_pages, 100)
        self.assertEqual(prediction.bottleneck_phase, PredictionHistory.Bottleneck.HAS)
        self.assertIsNotNone(prediction.estimated_completion_date)
        # 100 sayfa / 10 sayfa-gün (attendance_rate=1) = 10 gün
        self.assertEqual(prediction.estimated_remaining_days, 10)

    def test_has_is_bottleneck_even_though_ham_incomplete(self):
        """Has hızı ham hızından çok daha yavaşsa, ham henüz bitmemiş olsa
        bile nihai tahmini has hattı belirlemeli (gerçek darboğaz odur)."""
        student = make_student()
        make_pages(student, needs_revision_count=50, completed_count=4)  # 54 ham yapılmış, 600 kalan ham
        make_history(student, days=10, daily_memorization=5, daily_revision=1)

        prediction = calculate_prediction(student, persist=False)
        self.assertEqual(prediction.remaining_ham_pages, settings.TOTAL_QURAN_PAGES - 54)
        self.assertEqual(prediction.remaining_has_pages, settings.TOTAL_QURAN_PAGES - 4)
        self.assertEqual(prediction.bottleneck_phase, PredictionHistory.Bottleneck.HAS)

    def test_ham_is_bottleneck_when_has_pace_is_much_faster(self):
        """Öğrenci hızlı has yapıyor (örn. cüz bazlı toplu tekrar) ama yeni ham
        alma hızı çok düşükse, nihai tahmini ham hattı belirlemeli."""
        student = make_student()
        make_pages(student, needs_revision_count=20, completed_count=4)  # 24 ham yapılmış
        make_history(student, days=10, daily_memorization=1, daily_revision=20)

        prediction = calculate_prediction(student, persist=False)
        self.assertEqual(prediction.bottleneck_phase, PredictionHistory.Bottleneck.HAM)
        # ham_track = remaining_ham/ham_pace + avg_juz_pages/has_pace
        remaining_ham = settings.TOTAL_QURAN_PAGES - 24
        avg_juz_pages = settings.TOTAL_QURAN_PAGES / TOTAL_JUZ
        expected_days = remaining_ham / 1 + avg_juz_pages / 20
        self.assertEqual(prediction.estimated_remaining_days, int(round(expected_days)))

    def test_no_pace_data_returns_no_date_but_keeps_remaining_counts(self):
        student = make_student()
        make_pages(student, needs_revision_count=10, completed_count=0)
        # Hiç ham/has verisi olmayan (0 değerli) geçmiş -- pace hesaplanamaz.
        make_history(student, days=10, daily_memorization=0, daily_revision=0)

        prediction = calculate_prediction(student, persist=False)
        self.assertIsNotNone(prediction)
        self.assertIsNone(prediction.estimated_completion_date)
        self.assertIsNone(prediction.estimated_remaining_days)
        self.assertEqual(prediction.bottleneck_phase, "")
        self.assertEqual(prediction.remaining_has_pages, settings.TOTAL_QURAN_PAGES)

    def test_confidence_requires_has_samples_not_just_ham_samples(self):
        """Regresyon: eskiden güven seviyesi sadece ham örnek sayısına
        bakıyordu. Bol ham verisi olsa bile has verisi çok azsa (<3 gün)
        güven LOW kalmalı."""
        student = make_student()
        make_pages(student, needs_revision_count=100, completed_count=4)

        records = []
        base_day = date.today() - timedelta(days=25)
        for i in range(25):
            records.append(PerformanceHistory(
                student=student,
                date=base_day + timedelta(days=i),
                daily_memorization=5,
                daily_revision=20 if i < 2 else 0,  # sadece 2 gün has verisi
                attended=True,
                quality_score=80,
            ))
        PerformanceHistory.objects.bulk_create(records)

        prediction = calculate_prediction(student, persist=False)
        self.assertEqual(prediction.confidence_level, PredictionHistory.Confidence.LOW)

    def test_persist_updates_same_day_row(self):
        student = make_student()
        make_pages(student, needs_revision_count=10, completed_count=0)
        make_history(student, days=8, daily_memorization=3, daily_revision=5)

        calculate_prediction(student, persist=True)
        calculate_prediction(student, persist=True)

        self.assertEqual(PredictionHistory.objects.filter(student=student).count(), 1)
