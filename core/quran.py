"""
Cüz / Sayfa Dönüşüm Yardımcıları
=================================
Hafızlık takibi artık "sayfa" yerine "cüz ve tur" sistemine göre yapılır.
Kural sabittir: her cüz 20 sayfadır (1. Cüz: 1-20, 2. Cüz: 21-40, ...).
Son cüz (30.), Mushaf'ın toplam sayfa sayısına göre kalan sayfaları kapsar
(TOTAL_QURAN_PAGES=604 için 30. Cüz: 581-604, yani 24 sayfa).

Sayfa bazlı iç veri modeli (MemorizationPage) korunur; bu modül sadece
kullanıcıya gösterilen/girilen cüz numaralarını mutlak Mushaf sayfa
numaralarına (ve tersine) çevirir.
"""
from django.conf import settings

PAGES_PER_JUZ = 20
TOTAL_JUZ = 30


def juz_page_range(juz_number):
    """Verilen cüz numarasının (1-30) kapsadığı mutlak (start_page, end_page) aralığını döner."""
    total_pages = settings.TOTAL_QURAN_PAGES
    start = (juz_number - 1) * PAGES_PER_JUZ + 1
    end = min(juz_number * PAGES_PER_JUZ, total_pages)
    return start, end


def juz_page_count(juz_number):
    """Verilen cüzün kaç sayfadan oluştuğunu döner (son cüz hariç genelde 20)."""
    start, end = juz_page_range(juz_number)
    return max(end - start + 1, 0)


def juz_of_page(page_number):
    """Bir mutlak sayfa numarasının hangi cüze (1-30) ait olduğunu döner."""
    if not page_number:
        return None
    juz = ((page_number - 1) // PAGES_PER_JUZ) + 1
    return min(juz, TOTAL_JUZ)


def local_page_to_absolute(juz_number, local_page):
    """Cüz içindeki yerel sayfa numarasını (1'den başlar) mutlak Mushaf sayfasına çevirir."""
    start, end = juz_page_range(juz_number)
    absolute = start + local_page - 1
    return min(max(absolute, start), end)


def absolute_to_local_page(page_number):
    """Mutlak bir sayfa numarasını, ait olduğu cüz içindeki yerel sayfa numarasına çevirir."""
    juz = juz_of_page(page_number)
    if juz is None:
        return None
    start, _ = juz_page_range(juz)
    return page_number - start + 1


JUZ_CHOICES = [(i, f"{i}. Cüz") for i in range(1, TOTAL_JUZ + 1)]
