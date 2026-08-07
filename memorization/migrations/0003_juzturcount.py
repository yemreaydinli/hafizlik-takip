import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0002_alter_student_created_at_alter_student_updated_at'),
        ('memorization', '0002_alter_memorizationpage_first_memorized_date_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='JuzTurCount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('juz_number', models.PositiveSmallIntegerField(verbose_name='Cüz No')),
                ('tur_count', models.PositiveIntegerField(default=0, verbose_name='Tur Sayısı')),
                ('last_tur_date', models.DateField(blank=True, null=True, verbose_name='Son Tur Tarihi')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='juz_tur_counts', to='students.student', verbose_name='Öğrenci')),
            ],
            options={
                'verbose_name': 'Cüz Tur Sayacı',
                'verbose_name_plural': 'Cüz Tur Sayaçları',
                'ordering': ['juz_number'],
                'unique_together': {('student', 'juz_number')},
            },
        ),
    ]
