from django import forms
from django.forms import inlineformset_factory
from core.widgets import ISODateInput
from core.quran import (
    JUZ_CHOICES,
    juz_page_count,
    juz_page_range,
    juz_of_page,
    local_page_to_absolute,
    absolute_to_local_page,
)

from .models import LessonRecord
from memorization.models import RevisionRecord

TAILWIND_INPUT = "w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-emerald-500 focus:ring-emerald-500 text-sm"

JUZ_SELECT_CHOICES = [("", "Cüz seçin")] + JUZ_CHOICES


class LessonRecordForm(forms.ModelForm):
    """
    Ham (yeni ezber) girişi artık sayfa değil, cüz + cüz içi sayfa aralığı ile yapılır.
    Kullanıcı bir cüz seçer, ardından o cüz içindeki başlangıç/bitiş sayfasını
    (örn. 5. Cüz, sayfa 3-7) girer; bu bilgi arka planda mutlak Mushaf sayfa
    numarasına çevrilip ham_start_page/ham_end_page alanlarına kaydedilir, böylece
    Hafızlık Haritası ve Akıllı Tahmin Motoru değişmeden çalışmaya devam eder.
    """

    ham_juz = forms.ChoiceField(
        choices=JUZ_SELECT_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": TAILWIND_INPUT, "id": "id_ham_juz"}),
        label="Hangi Cüzden Ders Alındı",
    )

    class Meta:
        model = LessonRecord
        fields = [
            "date", "attendance", "ham_juz", "ham_start_page", "ham_end_page",
            "pismis_done", "pismis_page_count", "quality", "notes",
        ]
        widgets = {
            "date": ISODateInput(attrs={"class": TAILWIND_INPUT}),
            "attendance": forms.Select(attrs={"class": TAILWIND_INPUT, "id": "id_attendance"}),
            "ham_start_page": forms.NumberInput(attrs={
                "class": TAILWIND_INPUT, "min": 1, "max": 20, "id": "id_ham_start_local",
            }),
            "ham_end_page": forms.NumberInput(attrs={
                "class": TAILWIND_INPUT, "min": 1, "max": 20, "id": "id_ham_end_local",
            }),
            "pismis_done": forms.CheckboxInput(attrs={"class": "rounded border-slate-300"}),
            "pismis_page_count": forms.NumberInput(attrs={
                "class": TAILWIND_INPUT, "min": 0, "id": "id_pismis_page_count",
            }),
            "quality": forms.Select(attrs={"class": TAILWIND_INPUT}),
            "notes": forms.Textarea(attrs={"class": TAILWIND_INPUT, "rows": 3}),
        }
        labels = {
            "ham_start_page": "Başlangıç Sayfası (1-20)",
            "ham_end_page": "Bitiş Sayfası (1-20)",
            "pismis_done": "Pişmiş (Ham Arkası Eski Sayfalar) Okundu mu",
            "pismis_page_count": "Pişmiş Okunan Sayfa Sayısı (isteğe bağlı)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Düzenleme ekranında mevcut mutlak sayfa değerlerini cüz + yerel sayfa olarak göster.
        if self.instance and self.instance.pk and self.instance.ham_start_page:
            juz = juz_of_page(self.instance.ham_start_page)
            self.initial["ham_juz"] = juz
            self.initial["ham_start_page"] = absolute_to_local_page(self.instance.ham_start_page)
            if self.instance.ham_end_page:
                self.initial["ham_end_page"] = absolute_to_local_page(self.instance.ham_end_page)

    def clean(self):
        cleaned_data = super().clean()
        date_value = cleaned_data.get("date")
        student = self.instance.student
        if date_value and student:
            qs = LessonRecord.objects.filter(student=student, date=date_value)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("date", "Bu öğrenci için bu tarihte zaten bir ders kaydı mevcut.")

        juz = cleaned_data.get("ham_juz")
        local_start = cleaned_data.get("ham_start_page")
        local_end = cleaned_data.get("ham_end_page")

        if not juz:
            if local_start or local_end:
                self.add_error("ham_juz", "Ham ders sayfası girildiyse cüz de seçilmelidir.")
            cleaned_data["ham_start_page"] = None
            cleaned_data["ham_end_page"] = None
            return cleaned_data

        juz = int(juz)
        max_local = juz_page_count(juz)

        if local_start is not None and not (1 <= local_start <= max_local):
            self.add_error("ham_start_page", f"{juz}. Cüz için sayfa 1-{max_local} arasında olmalı.")
        if local_end is not None and not (1 <= local_end <= max_local):
            self.add_error("ham_end_page", f"{juz}. Cüz için sayfa 1-{max_local} arasında olmalı.")
        if local_start is not None and local_end is not None and not self.errors.get("ham_start_page") and not self.errors.get("ham_end_page"):
            if local_end < local_start:
                self.add_error("ham_end_page", "Bitiş sayfası başlangıç sayfasından küçük olamaz.")
            else:
                cleaned_data["ham_start_page"] = local_page_to_absolute(juz, local_start)
                cleaned_data["ham_end_page"] = local_page_to_absolute(juz, local_end)
        return cleaned_data


class RevisionRecordForm(forms.ModelForm):
    """
    Tekrar (has) girişi artık sayfa aralığı değil, tekrar edilen cüzün seçilmesiyle yapılır.
    Her satır bir cüzü temsil eder; kaydedildiğinde ilgili cüzün 'has tekrar' sayacı
    (JuzTurCount) otomatik olarak yeniden hesaplanır (bkz. lessons/signals.py). Bu sayaç,
    ham derste ilerlenen "tur" kavramından farklıdır: has tekrar, tamamlanmış bir cüzün
    baştan sona tekrar dinletilme sayısını ifade eder.
    """

    juz_number = forms.ChoiceField(
        choices=JUZ_SELECT_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": TAILWIND_INPUT}),
        label="Tekrar Edilen Cüz",
    )

    class Meta:
        model = RevisionRecord
        fields = ["juz_number", "start_page", "end_page"]
        widgets = {
            "start_page": forms.HiddenInput(),
            "end_page": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["start_page"].required = False
        self.fields["end_page"].required = False
        if self.instance and self.instance.pk and self.instance.start_page:
            self.initial["juz_number"] = juz_of_page(self.instance.start_page)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("DELETE"):
            return cleaned_data
        juz = cleaned_data.get("juz_number")
        if juz:
            juz = int(juz)
            start, end = juz_page_range(juz)
            cleaned_data["start_page"] = start
            cleaned_data["end_page"] = end
        elif self.has_changed():
            self.add_error("juz_number", "Lütfen tekrar edilen cüzü seçin.")
        return cleaned_data


RevisionRecordFormSet = inlineformset_factory(
    LessonRecord,
    RevisionRecord,
    form=RevisionRecordForm,
    extra=1,
    can_delete=True,
)
