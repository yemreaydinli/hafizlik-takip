<div align="center">

# 📖 Hafızlık Takip Sistemi

### Akıllı İlerleme Tahmin Platformu

Hafızlık eğitimi veren kurumlar için geliştirilmiş, Osmanlı usulü (ham / has / pişmiş)
ezber takip yöntemini esas alan; web tabanlı, mobil ve masaüstü uyumlu öğrenci takip ve
akıllı ilerleme tahmin platformu.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Production-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-Proprietary-lightgrey.svg)](#-lisans)

[Özellikler](#-özellikler) ·
[Mimari](#-mimari--proje-yapısı) ·
[Kurulum](#-hızlı-başlangıç-yerel-kurulum) ·
[Dağıtım](#-üretime-alma-render--neonsupabase) ·
[Sorun Giderme](#-sorun-giderme)

</div>

---

## 📑 İçindekiler

1. [Genel Bakış](#-genel-bakış)
2. [Özellikler](#-özellikler)
3. [Teknoloji Yığını](#-teknoloji-yığını)
4. [Mimari & Proje Yapısı](#-mimari--proje-yapısı)
5. [Domain Terminolojisi](#-domain-terminolojisi-ham--has--pişmiş)
6. [Hızlı Başlangıç (Yerel Kurulum)](#-hızlı-başlangıç-yerel-kurulum)
7. [Ortam Değişkenleri](#-ortam-değişkenleri)
8. [Üretime Alma (Render + Neon/Supabase)](#-üretime-alma-render--neonsupabase)
9. [Zamanlanmış Görevler](#-zamanlanmış-görevler)
10. [Sorun Giderme](#-sorun-giderme)
11. [Önemli Notlar ve Varsayımlar](#-önemli-notlar-ve-varsayımlar)
12. [Yol Haritası](#-yol-haritası)
13. [Lisans](#-lisans)

---

## 🔎 Genel Bakış

Hafızlık Takip Sistemi, hafızlık eğitim kurumlarındaki hocaların **günlük ders takibini**
dijitalleştirmesini; yöneticilerin ise **kurum genelinde ilerlemeyi tek ekrandan izlemesini**
sağlar. Sistemin çekirdeğinde iki şey vardır:

- **Görsel Hafızlık Haritası** — 604 sayfalık mushafın her sayfasının durumunu
  (henüz çalışılmadı / tekrar bekliyor / tamamlandı) tek bakışta gösterir.
- **Akıllı Tahmin Motoru** — öğrencinin güncel tempsuna göre hafızlığı tamamlama
  tarihini istatistiksel olarak tahmin eder ve tempo düşüşü/duraklama gibi durumları
  otomatik olarak hocaya/yöneticiye bildirir.

---

## ✨ Özellikler

| Modül | Açıklama |
|---|---|
| 👥 **Kullanıcı Yönetimi** | Rol tabanlı erişim (Yönetici / Hafız Yetiştiricisi) |
| 🎓 **Öğrenci Yönetimi** | Aktif / ara verdi / tamamladı durum takibi, öğretici atama |
| 📝 **Günlük Ders Takibi** | Devam durumu, ham ezber, has tekrar, pişmiş onayı, ders kalitesi, notlar |
| 🗺️ **Hafızlık Haritası** | 604 sayfa üzerinde yeşil / sarı / gri durum gösterimi, ders geçmişiyle her zaman senkron |
| 📈 **Performans Analizi** | Günlük / haftalık / aylık ortalamalar, tempo grafikleri |
| 🔮 **Akıllı Tahmin Motoru** | İlk 30 gün basit ortalama, sonrasında Üstel Hareketli Ortalama (EMA) ile tamamlanma tarihi tahmini |
| 🔔 **Akıllı Uyarı Sistemi** | Duraklama, devamsızlık, performans düşüşü, hedeften sapma uyarıları |
| 📊 **Dashboard** | Kurum genelinde özet istatistikler |
| 🧾 **Raporlama** | Günlük / Haftalık / Aylık / Devamsızlık / İlerleme / Tahmin raporları — **PDF ve Excel** çıktısı |
| ⚙️ **Django Admin** | Tam yönetim paneli, veri düzeltme ve denetim için |

---

## 🧱 Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Backend | [Django 6.0](https://www.djangoproject.com/) (Python 3.12) |
| Veritabanı | PostgreSQL (üretim) · SQLite (yerel geliştirme) |
| Arayüz | Tailwind CSS (CDN) + [HTMX](https://htmx.org/) |
| Raporlama | [reportlab](https://www.reportlab.com/) (PDF) · [openpyxl](https://openpyxl.readthedocs.io/) (Excel) |
| Statik dosya sunumu | [WhiteNoise](https://whitenoise.readthedocs.io/) |
| Uygulama sunucusu | [Gunicorn](https://gunicorn.org/) |
| Barındırma (önerilen) | [Render](https://render.com/) + [Neon](https://neon.tech/) / [Supabase](https://supabase.com/) (ücretsiz katman) |

---

## 🏗 Mimari & Proje Yapısı

Proje, sorumlulukların net ayrıldığı çoklu Django app mimarisi ile geliştirilmiştir:

```
hafizlik-takip/
├── config/            # Proje ayarları, ortam değişkeni okuma, ana URL yönlendirmesi, logging
├── accounts/          # Kullanıcı modeli (rol tabanlı), kimlik doğrulama
├── core/              # Dashboard, context processor'lar, Kur'an sayfa/cüz yardımcıları, demo veri
├── students/          # Öğrenci modeli ve CRUD işlemleri
├── lessons/           # Günlük ders kaydı, tekrar (has) formseti, senkronizasyon sinyalleri
├── memorization/      # Hafızlık Haritası (604 sayfa), tekrar kayıtları, cüz tur sayaçları
├── predictions/       # Akıllı Tahmin Motoru (basit ortalama + EMA), tahmin geçmişi
├── notifications/     # Akıllı Uyarı Sistemi + `generate_alerts` yönetim komutu
├── reports/           # PDF / Excel rapor üretimi
├── templates/         # Tailwind CSS + HTMX tabanlı arayüz şablonları
├── static/            # manifest.json (PWA / "Ana Ekrana Ekle") ve statik varlıklar
├── requirements.txt
├── Procfile           # Referans amaçlı; Render bunu otomatik OKUMAZ (bkz. Dağıtım bölümü)
└── .env.example
```

### Veri akışı — bir ders nasıl senkronize edilir?

```
LessonRecord (ham + has aralıkları)
        │
        ▼
lessons/signals.py :: sync_lesson()
        │   ├─ recompute_student_memorization()  → MemorizationPage (604 sayfa haritası)
        │   ├─ _sync_juz_tur_counts()             → JuzTurCount (has tekrar sayaçları)
        │   └─ _sync_performance_history()        → PerformanceHistory (günlük tempo)
        ▼
predictions/services.py :: calculate_prediction()  → PredictionHistory (tamamlanma tahmini)
        ▼
notifications/services.py :: generate_alerts()     → Notification (uyarılar)
```

`recompute_student_memorization()` **idempotenttir**: bir ders kaydı silinir veya
düzenlenirse, Hafızlık Haritası'ndaki ilgili sayfalar otomatik olarak doğru duruma geri
döner — kısmi/artımlı güncelleme değil, öğrencinin tüm ders geçmişinden sıfırdan yeniden
hesaplama yapılır.

---

## 📚 Domain Terminolojisi (Ham / Has / Pişmiş)

Bu sistem, geleneksel Osmanlı usulü hıfz eğitimindeki üç aşamayı birebir modeller:

| Terim | Anlamı | Sistemdeki karşılığı |
|---|---|---|
| **Ham** | O günkü yeni ezberlenen sayfa(lar) | `LessonRecord.ham_start_page` / `ham_end_page` |
| **Pişmiş** | Ham'ın hemen arkasından, aynı cüzde daha önce ezberlenmiş eski sayfaların da dinletilmesi | `LessonRecord.pismis_done` |
| **Has (Tekrar)** | Tamamlanmış bir cüzün baştan sona tekrar dinletilmesi | `RevisionRecord` → `JuzTurCount.tur_count` ("has tekrar sayacı") |

> ⚠️ **Terminoloji notu:** "Tur" kelimesi yalnızca **has tekrar** bağlamında kullanılır
> (bir cüzün kaçıncı kez baştan sona tekrar edildiği). Ham derste ilerleme kavramıyla
> karıştırılmamalıdır.

---

## 🚀 Hızlı Başlangıç (Yerel Kurulum)

Yerelde **SQLite** otomatik kullanılır; PostgreSQL bağlantısı zorunlu değildir.

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # gerekirse .env içeriğini düzenleyin

python manage.py migrate
python manage.py seed_demo_data   # örnek yönetici/öğretici/öğrenci oluşturur (opsiyonel)
python manage.py runserver
```

Tarayıcıdan `http://127.0.0.1:8000/hesap/giris/` adresine gidin.

**Demo giriş bilgileri** (`seed_demo_data` çalıştırıldıysa):

| Rol | Kullanıcı adı | Şifre |
|---|---|---|
| Yönetici | `admin` | `admin123` |
| Öğretici | `ogretici` | `ogretici123` |

Kendi yönetici hesabınızı oluşturmak isterseniz:
```bash
python manage.py createsuperuser
```
> Oluşturduğunuz kullanıcının Django Admin panelinden `role` alanını `admin` yapmayı unutmayın.

Uyarı sistemini manuel çalıştırmak için (üretimde günlük zamanlanmış görev olarak kurulmalı):
```bash
python manage.py generate_alerts
```

---

## 🔐 Ortam Değişkenleri

| Değişken | Zorunlu | Açıklama |
|---|:---:|---|
| `DJANGO_SECRET_KEY` | ✅ (üretimde) | Rastgele, uzun ve gizli bir metin. Üretmek için: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | ✅ | `True` (yerel) / `False` (üretim) |
| `DJANGO_ALLOWED_HOSTS` | ✅ (üretimde) | Virgülle ayrılmış izinli host'lar, örn. `uygulamaniz.onrender.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | ✅ (üretimde) | `https://` dahil tam origin, örn. `https://uygulamaniz.onrender.com` |
| `DATABASE_URL` | Üretimde ✅ | PostgreSQL bağlantı dizesi (Neon/Supabase). Yoksa yerelde SQLite'a düşülür |

Tüm değişkenler için bkz. `.env.example`.

---

## ☁️ Üretime Alma (Render + Neon/Supabase)

Aşağıdaki kombinasyon tamamen **ücretsiz katmanlarla** çalışır. Mobil/masaüstü responsive
tasarım sayesinde ayrı bir mobil uygulamaya gerek yoktur; kullanıcılar tarayıcıdan
"Ana Ekrana Ekle" diyerek uygulama benzeri deneyim elde edebilir (`static/manifest.json`).

### Adım 1 — Ücretsiz PostgreSQL veritabanı

**Neon.tech (önerilen):**
1. [neon.tech](https://neon.tech) üzerinden ücretsiz hesap açın.
2. **New Project** ile bir proje oluşturun.
3. Bağlantı dizesini (Connection String) kopyalayın:
   ```
   postgresql://kullanici:sifre@ep-xxxx.eu-central-1.aws.neon.tech/veritabani?sslmode=require
   ```

**Supabase alternatifi:** Project Settings → Database → Connection string (URI).

### Adım 2 — Kodu GitHub'a yükleyin

```bash
git init
git add .
git commit -m "İlk sürüm"
git branch -M main
git remote add origin https://github.com/KULLANICI_ADINIZ/hafizlik-takip.git
git push -u origin main
```

### Adım 3 — Render.com üzerinde ücretsiz web servisi oluşturun

1. [render.com](https://render.com) adresinden GitHub hesabınızla giriş yapın.
2. **New +** → **Web Service** → reponuzu seçin.
3. Ayarları girin:

   | Alan | Değer |
   |---|---|
   | **Build Command** | `pip install -r requirements.txt && python manage.py collectstatic --noinput` |
   | **Start Command** | `python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT` |
   | **Plan** | Free |

   > ⚠️ **Kritik:** Render, Heroku'nun `Procfile` içindeki `release:` fazını **desteklemez**
   > ve ücretsiz planda **Shell sekmesi bulunmaz**. Bu yüzden migration'ların
   > `Start Command`'a eklenmesi zorunludur — yukarıdaki komut her deploy/yeniden
   > başlatmada `migrate`'i otomatik çalıştırır ve Shell'e ihtiyaç bırakmaz.

4. **Environment** sekmesinden [Ortam Değişkenleri](#-ortam-değişkenleri) tablosundaki
   tüm değerleri ekleyin (`DATABASE_URL` = Adım 1'deki bağlantı dizesi).
5. **Create Web Service** ile dağıtımı başlatın. İlk deploy birkaç dakika sürer.
6. Yönetici hesabı oluşturmak için (Shell olmadan), yerel makinenizden üretim
   veritabanına bağlanıp tek seferlik çalıştırın:
   ```bash
   DATABASE_URL="<Adım 1'deki bağlantı dizesi>" python manage.py createsuperuser
   ```
   (Ardından o kullanıcının `role` alanını Django Admin'den `admin` yapın.)

> **Not:** Render'ın ücretsiz planı belirli bir süre trafik almayınca uygulamayı uyku
> moduna alır; ilk istek birkaç saniye gecikebilir. Kurumsal kullanım için ücretli plana
> geçilebilir (bu durumda Shell sekmesi de açılır).

**Alternatif ücretsiz barındırma seçenekleri:** Railway.app (aylık ücretsiz kredi),
Fly.io (küçük uygulamalar için ücretsiz katman), PythonAnywhere. Mantık aynıdır:
`DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` tanımlayıp Start Command'ı
`migrate`'i içerecek şekilde ayarlamak.

### Adım 4 — Mobilde kullanım

- Kullanıcılar telefon tarayıcısından siteyi açıp **"Ana Ekrana Ekle"** ile uygulama
  simgesi üzerinden hızlı erişim sağlayabilir (`static/manifest.json`).
- Tüm sayfalar mobil genişliklere göre otomatik uyum sağlar (sidebar mobilde açılır menüye dönüşür).

---

## ⏰ Zamanlanmış Görevler

`generate_alerts` komutunun her gün otomatik çalışması için:

- **Render:** "Cron Jobs" özelliğini kullanarak günde bir kez
  `python manage.py generate_alerts` komutunu çalıştırın (ücretsiz katmanda sınırlı
  sayıda cron job desteklenir).
- **Alternatif:** GitHub Actions ile günlük bir workflow oluşturup Render'daki bir
  yönetim komutunu tetikleyebilirsiniz.

---

## 🩺 Sorun Giderme

### 500 Server Error alıyorum

En sık karşılaşılan sebep, **migration'ların üretim veritabanında henüz uygulanmamış**
olmasıdır (yeni bir model alanı eklendiğinde). Kontrol listesi:

1. Render **Start Command**'ının `python manage.py migrate && gunicorn ...` şeklinde
   olduğundan emin olun (bkz. [Adım 3](#adım-3--rendercom-üzerinde-ücretsiz-web-servisi-oluşturun)).
2. `Build Command`'da `collectstatic` adımının bulunduğundan emin olun.
3. [Ortam Değişkenleri](#-ortam-değişkenleri) tablosundaki tüm değerlerin dolu olduğunu kontrol edin.

### Render loglarında traceback görünmüyor

Proje, `DEBUG=False` olsa bile hata izlerini (traceback) konsola (Render Logs) basacak
şekilde `config/settings.py` içinde `LOGGING` yapılandırmasına sahiptir. Bir 500 hatası
aldığınızda Render **Logs** sekmesinde ilgili isteğin hemen altında tam Python
traceback'ini görmelisiniz; bu, kök nedeni hızlıca teşhis etmenizi sağlar.

---

## 📌 Önemli Notlar ve Varsayımlar

- Kur'an-ı Kerim toplam sayfa sayısı `settings.TOTAL_QURAN_PAGES = 604` olarak
  tanımlanmıştır (yaygın 15 satırlı mushaf standardı); farklı bir mushaf kullanıyorsanız
  bu değeri güncelleyin.
- Tahmin motoru parametreleri (`PREDICTION_SIMPLE_AVG_DAYS`, `PREDICTION_EMA_ALPHA`) ve
  uyarı eşikleri (`ALERT_*`) `config/settings.py` içinde tanımlıdır; kurumunuzun
  ihtiyacına göre ayarlanabilir.
- Tailwind CSS, hızlı teslimat için CDN üzerinden (`cdn.tailwindcss.com`) kullanılmaktadır.
  Üretimde daha küçük dosya boyutu isterseniz `django-tailwind` ile derleme adımına
  geçilebilir; mevcut şablonlar sınıf isimleri aynı kaldığı için uyumludur.
- Raporlar PDF için **reportlab**, Excel için **openpyxl** kütüphaneleriyle sunucu
  tarafında anlık üretilir; ayrı bir dosya depolama servisi gerekmez.
- Elle girilen "başlangıç durumu aktarımı" (`memorization.services.bulk_apply_range`)
  ile oluşturulan sayfa durumları, ders kaydı senkronizasyonundan (`synced_from_lessons`
  bayrağı sayesinde) etkilenmez ve geri alınmaz.

---

## 🗺 Yol Haritası

Aşağıdaki maddeler mevcut mimariye kolayca eklenebilecek şekilde tasarlanmıştır:

- [ ] Makine öğrenmesi destekli kişiselleştirilmiş tahminler
- [ ] WhatsApp / SMS ve e-posta bildirimleri
- [ ] Çoklu kurum desteği
- [ ] Native mobil uygulama
- [ ] Sesli ders değerlendirme
- [ ] "Kaçıncı Tur?" seçiminden ham sayfa aralığının otomatik doldurulması
      (net bir iş kuralı belirlendiğinde eklenecek)

---

## 📄 Lisans

Bu proje, sahibinin izni olmadan dağıtılamaz veya ticari amaçla kullanılamaz.
