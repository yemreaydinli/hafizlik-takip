"""Hızlı test için örnek yönetici, öğretici ve öğrenci verisi oluşturur."""
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from students.models import Student
from lessons.models import LessonRecord
from memorization.models import RevisionRecord
from predictions.services import calculate_prediction


class Command(BaseCommand):
    help = "Demo amaçlı yönetici, öğretici ve öğrenci verisi oluşturur (admin/admin123, ogretici/ogretici123)."

    @transaction.atomic
    def handle(self, *args, **options):
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin", email="admin@example.com", password="admin123", role=User.Role.ADMIN
            )
            self.stdout.write(self.style.SUCCESS("Yönetici oluşturuldu: admin / admin123"))

        teacher, created = User.objects.get_or_create(
            username="ogretici", defaults={
                "email": "ogretici@example.com", "role": User.Role.TEACHER,
                "first_name": "Ahmet", "last_name": "Hoca",
            }
        )
        if created:
            teacher.set_password("ogretici123")
            teacher.save()
            self.stdout.write(self.style.SUCCESS("Öğretici oluşturuldu: ogretici / ogretici123"))

        if not Student.objects.filter(teacher=teacher).exists():
            student = Student.objects.create(
                full_name="Yusuf Emre",
                start_date=date.today() - timedelta(days=45),
                status=Student.Status.ACTIVE,
                teacher=teacher,
                target_completion_date=date.today() + timedelta(days=900),
            )
            page = 1
            for i in range(45, 0, -1):
                lesson_date = date.today() - timedelta(days=i)
                attended = random.random() > 0.15
                lesson = LessonRecord.objects.create(
                    student=student,
                    date=lesson_date,
                    attendance=LessonRecord.Attendance.PRESENT if attended else LessonRecord.Attendance.ABSENT,
                    ham_start_page=page if attended else None,
                    ham_end_page=(page + random.randint(0, 1)) if attended else None,
                    quality=random.choice(["excellent", "good", "average"]) if attended else None,
                )
                if attended:
                    if lesson.ham_end_page:
                        page = lesson.ham_end_page + 1
                    if i % 5 == 0 and page > 5:
                        RevisionRecord.objects.create(lesson=lesson, start_page=max(page - 6, 1), end_page=page - 2)
            calculate_prediction(student)
            self.stdout.write(self.style.SUCCESS(f"Örnek öğrenci oluşturuldu: {student.full_name}"))

        self.stdout.write(self.style.SUCCESS("Demo veri kurulumu tamamlandı."))
