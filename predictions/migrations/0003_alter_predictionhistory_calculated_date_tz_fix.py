from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('predictions', '0002_alter_predictionhistory_calculated_date_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='predictionhistory',
            name='calculated_date',
            field=models.DateField(default=django.utils.timezone.localdate, verbose_name='Hesaplama Tarihi'),
        ),
        migrations.AlterModelOptions(
            name='predictionhistory',
            options={'ordering': ['-calculated_date', '-id'], 'verbose_name': 'Tahmin Geçmişi', 'verbose_name_plural': 'Tahmin Geçmişleri'},
        ),
    ]
