from django.core.management.base import BaseCommand
from notifications.services import generate_alerts_for_all


class Command(BaseCommand):
    help = "Tüm aktif öğrenciler için akıllı uyarı sistemini çalıştırır (duraklama, devamsızlık, performans düşüşü, hedef sapması)."

    def handle(self, *args, **options):
        generate_alerts_for_all()
        self.stdout.write(self.style.SUCCESS("Uyarılar başarıyla oluşturuldu."))
