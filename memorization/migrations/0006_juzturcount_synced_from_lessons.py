# Generated manually: JuzTurCount için 'Başlangıç Durumu Aktarımı' ile elle
# ayarlanan has tekrar sayaçlarını, ders senkronizasyonunun (sync_lesson)
# üzerine yazmasını engelleyen synced_from_lessons alanı eklenir.
# Bkz. memorization/models.py:JuzTurCount ve lessons/signals.py:_sync_juz_tur_counts.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('memorization', '0005_alter_juzturcount_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='juzturcount',
            name='synced_from_lessons',
            field=models.BooleanField(
                default=True,
                help_text=(
                    "True ise bu sayacı lessons/signals.py:_sync_juz_tur_counts RevisionRecord "
                    "kayıtlarından otomatik hesaplamıştır ve ders kaydı eklenip/silindiğinde yeniden "
                    "hesaplanabilir. False ise 'Başlangıç Durumu Aktarımı' (memorization.views ile elle "
                    "'Tamamlandı' işaretleme) sırasında elle ayarlanmıştır ve o cüz için gerçek bir Has "
                    "(RevisionRecord) kaydı girilene kadar ders senkronizasyonu bu sayacı sıfırlamaz."
                ),
                verbose_name='Ders Kaydından Senkronize',
            ),
        ),
    ]
