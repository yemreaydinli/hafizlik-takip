# Hafızlık Takip Sistemi ve Akıllı İlerleme Tahmin Platformu

Hafızlık eğitimi veren kurumlar için geliştirilmiş, web tabanlı (mobil + masaüstü uyumlu) bir
öğrenci takip ve akıllı ilerleme tahmin platformu.

**Teknolojiler:** Django (Python) · PostgreSQL (SQLite ile yerel geliştirme) · Tailwind CSS (CDN) · HTMX

---

## 🌐 Canlı Demo

Sistem Render.com üzerinde yayında: **https://hafizlik-takip-app.onrender.com**

> Ücretsiz Render planında uygulama bir süre trafik almayınca uyku moduna geçer; ilk istekte
> sayfanın açılması birkaç saniye (bazen ~30 sn) sürebilir, bu normaldir.

Demo giriş bilgileri (kendi ortamınızda `seed_demo_data` komutunu çalıştırdıysanız aynı bilgiler geçerlidir):
- Yönetici: `admin` / `admin123`
- Öğretici: `ogretici` / `ogretici123`

---

## 1. Özellikler

- 👥 Kullanıcı yönetimi (Yönetici / Hafız Yetiştiricisi rolleri)
- 🎓 Öğrenci yönetimi (aktif / ara verdi / tamamladı)
- 📝 Günlük ders takibi: devam, **ham** (yeni ezber), **has** (tekrar) — cüz bazlı seçim —,
  **pişmiş** (ham arkası eski sayfa okuma: evet/hayır + isteğe bağlı kaç sayfa), ders kalitesi, notlar
- 🔁 **Cüz/Tur Takibi**: her cüz için kaçıncı kez has (tekrar) verildiğini gösteren `JuzTurCount`
  sayacı — Hafızlık Haritası ve öğrenci detay sayfasında görünür
- 🗺️ Görsel Hafızlık Haritası (604 sayfa; yeşil = has ile pişmiş / sarı = ham yapılmış ama
  henüz pişmemiş / gri = hiç çalışılmamış)
- 📈 Performans analiz sistemi (günlük/haftalık/aylık ortalamalar; ham ve has hızları ayrı ayrı)
- 🔮 **Akıllı Tahmin Motoru (iki fazlı)**: "hafız olma" tarihini artık tek bir ham hızına göre değil,
  **ham** (yeni ezber) ve **has** (pişirme/tekrar) hatlarını ayrı ayrı izleyip hangisi darboğaz
  (bottleneck) ise ona göre tahmin eder — bir sayfa sadece ham'ı okunmuşken "bitmiş" sayılmaz,
  gerçekten hafız olmak has ile pişmeyi gerektirir. İlk 30 gün/5 ders basit ortalama, sonrasında
  Üstel Hareketli Ortalama (EMA); güven seviyesi hem ham hem has verisinin yeterliliğine bakar.
- 🎯 **Hedef Karşılaştırması**: hedef tarihe göre "bugün itibarıyla olması gereken" sayfa sayısı ile
  gerçekten **pişmiş** (has ile tamamlanmış) sayfa sayısını karşılaştırır — tahmin motoruyla aynı
  tanımı (has bazlı) kullanır, çelişkili sinyal vermez
- 🔔 **Akıllı Uyarı Sistemi**: duraklama, devamsızlık, performans düşüşü, hedef sapması uyarıları
  (`generate_alerts` komutu — üretimde günlük zamanlanmış görev olarak kurulmalı, bkz. Bölüm 4.5)
- 📊 Dashboard (özet istatistikler)
- 🧾 Raporlama: Günlük / Haftalık / Aylık / Devamsızlık / İlerleme / Tahmin raporları — **PDF ve Excel** olarak indirilebilir
- ⚙️ Django Admin ile tam yönetim paneli — ders/tekrar kayıtları admin'den düzenlendiğinde de
  Hafızlık Haritası/JuzTurCount/Tahmin Motoru otomatik senkronize olur
- ✅ Kritik senkronizasyon ve tahmin fonksiyonları için otomatik testler (`python manage.py test`)

---

## 2. Proje Yapısı

```
├── config/              # Django ayarları, ana URL yönlendirmesi
├── accounts/            # Kullanıcı modeli (rol tabanlı), giriş/çıkış, öğretici yönetimi
├── core/                # Dashboard, context processor'lar, demo veri komutu
├── students/            # Öğrenci modeli ve CRUD işlemleri
├── lessons/             # Günlük ders kaydı (ham/pişmiş), performans geçmişi, senkronizasyon sinyalleri, testler
├── memorization/        # Sayfa haritası (604 sayfa), tekrar (has) kayıtları, Cüz/Tur sayacı (JuzTurCount)
├── predictions/         # Akıllı Tahmin Motoru (iki fazlı: ham + has, basit ortalama + EMA), testler
├── notifications/       # Akıllı Uyarı Sistemi + `generate_alerts` yönetim komutu
├── reports/              # PDF/Excel rapor üretimi (reportlab, openpyxl)
├── templates/            # Tailwind CSS + HTMX tabanlı arayüz şablonları
├── static/                # manifest.json (mobil ana ekrana ekleme desteği) ve statik dosyalar
├── requirements.txt
├── Procfile               # Render/Railway için başlatma komutları
└── .env.example
```

---

## 3. Yerel Kurulum (Geliştirme Ortamı)

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

Demo giriş bilgileri (`seed_demo_data` komutunu çalıştırdıysanız):
- Yönetici: `admin` / `admin123`
- Öğretici: `ogretici` / `ogretici123`

Kendi yönetici hesabınızı oluşturmak isterseniz:
```bash
python manage.py createsuperuser
```
(Oluşturduğunuz kullanıcının admin panelinden `role` alanını `admin` yapmayı unutmayın.)

Uyarı sistemini manuel çalıştırmak için (üretimde günlük zamanlanmış görev olarak kurulmalı):
```bash
python manage.py generate_alerts
```

Testleri çalıştırmak için:
```bash
python manage.py test
```

---

## 4. Ücretsiz Olarak Yayına Alma (Adım Adım)

> Bu projenin canlı örneği zaten aşağıdaki adımlarla Render.com + Neon.tech kombinasyonu
> kullanılarak yayına alındı: **https://hafizlik-takip-app.onrender.com**. Aşağıdaki adımlar
> hem mevcut kurulumu anlamak hem de projeyi kendi Render/Neon hesabınızda yeniden veya ek
> bir kopya olarak yayınlamak isteyenler için referans niteliğindedir.


Aşağıdaki kombinasyon tamamen **ücretsiz katmanlarla** çalışır: veritabanı için Neon veya Supabase,
uygulama barındırma için Render (önerilen) veya Railway. Mobil ve masaüstünde responsive
tasarım sayesinde ek bir mobil uygulama gerekmez; kullanıcılar telefonlarında tarayıcıdan
"Ana Ekrana Ekle" diyerek uygulama benzeri deneyim elde edebilir (PWA `manifest.json` dahil).

### Adım 1 — Ücretsiz PostgreSQL veritabanı (Neon.tech veya Supabase)

**Neon.tech (önerilen, tamamen ücretsiz katman):**
1. https://neon.tech adresinden ücretsiz hesap açın.
2. "New Project" ile bir proje oluşturun.
3. Bağlantı dizesini (Connection String) kopyalayın — şuna benzer:
   `postgresql://kullanici:sifre@ep-xxxx.eu-central-1.aws.neon.tech/veritabani?sslmode=require`

**Supabase alternatifi:**
1. https://supabase.com üzerinden proje oluşturun.
2. Project Settings → Database → Connection string (URI) kısmından bağlantıyı alın.

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

1. https://render.com adresinden GitHub hesabınızla giriş yapın.
2. "New +" → "Web Service" → GitHub reponuzu seçin.
3. Ayarlar:
   - **Build Command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - **Start Command:** `gunicorn config.wsgi:application`
   - **Plan:** Free
4. "Environment" sekmesinden şu değişkenleri ekleyin:
   - `DJANGO_SECRET_KEY` → rastgele uzun bir metin (örn. `python -c "import secrets; print(secrets.token_urlsafe(50))"` ile üretebilirsiniz)
   - `DJANGO_DEBUG` → `False`
   - `DJANGO_ALLOWED_HOSTS` → `sizin-servis-adiniz.onrender.com`
   - `DJANGO_CSRF_TRUSTED_ORIGINS` → `https://sizin-servis-adiniz.onrender.com`
   - `DATABASE_URL` → Adım 1'de aldığınız Neon/Supabase bağlantı dizesi
5. "Create Web Service" ile dağıtımı başlatın. İlk deploy birkaç dakika sürer.
6. Deploy tamamlandıktan sonra Render'ın "Shell" sekmesinden bir kerelik şu komutları çalıştırın:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

> Not: Render'ın ücretsiz planı belirli bir süre trafik almayınca uygulamayı uyku moduna alır;
> ilk istek birkaç saniye gecikebilir. Kurumsal kullanım için gerekirse ücretli plana geçilebilir.

**Alternatif ücretsiz barındırma seçenekleri:** Railway.app (aylık ücretsiz kredi), Fly.io
(küçük uygulamalar için ücretsiz katman), PythonAnywhere (küçük Django projeleri için ücretsiz plan).
Hepsinde mantık aynıdır: `DATABASE_URL`, `DJANGO_SECRET_KEY` ve `DJANGO_ALLOWED_HOSTS`
ortam değişkenlerini tanımlayıp `gunicorn config.wsgi:application` komutuyla başlatmak.

### Adım 4 — Mobilde kullanım

Sistem responsive olduğu için ek bir mobil uygulamaya gerek yoktur:
- Kullanıcılar telefon tarayıcısından siteyi açıp "Ana Ekrana Ekle" seçeneğini kullanarak
  uygulama simgesi ile hızlı erişim sağlayabilir (`static/manifest.json` bu deneyimi destekler).
- Tüm sayfalar mobil genişliklere göre otomatik uyum sağlar (sidebar mobilde açılır menüye dönüşür).

### Adım 5 — Günlük uyarı üretimi için zamanlanmış görev (opsiyonel ama önerilir)

`generate_alerts` komutunun her gün otomatik çalışması için:
- **Render:** "Cron Jobs" özelliğini kullanarak günde bir kez `python manage.py generate_alerts` komutunu çalıştırın (ücretsiz katmanda sınırlı sayıda cron job desteklenir).
- **Alternatif:** GitHub Actions ile günlük bir workflow oluşturup Render'daki bir endpoint'i (veya management komutunu SSH/Shell üzerinden) tetikleyebilirsiniz.

> ⚠️ Bu adımın canlı örnekte (`hafizlik-takip-app`) fiilen kurulu olup olmadığı kod deposundan
> doğrulanamaz — bir Render Cron Job kaynağıdır, repodaki dosyalarda görünmez. Render
> Dashboard'da ilgili servisin "Cron Jobs" sekmesinden kontrol edin; kurulu değilse "Akıllı
> Uyarı Sistemi" (duraklama/devamsızlık/hedef sapması uyarıları) hiç tetiklenmez.

---

## 5. Önemli Notlar ve Varsayımlar


- Kur'an-ı Kerim toplam sayfa sayısı `settings.TOTAL_QURAN_PAGES = 604` olarak tanımlanmıştır
  (yaygın 15 satırlı mushaf standardı); farklı bir mushaf kullanıyorsanız bu değeri güncelleyin.
- Tahmin motoru parametreleri (`PREDICTION_SIMPLE_AVG_DAYS`, `PREDICTION_EMA_ALPHA`) ve uyarı
  eşikleri (`ALERT_*`) `config/settings.py` içinde tanımlıdır; kurumunuzun ihtiyacına göre
  ayarlanabilir.
- **"Pişmiş sayılma" eşiği:** Bir sayfa şu an her cüz için en az **1 kez** has verildiğinde
  (`MemorizationPage.Status.COMPLETED`) "pişmiş"/hafız-uyumlu sayılır. Kursunuzun usulü daha
  fazla tur gerektiriyorsa, `memorization/models.py:JuzTurCount.tur_count` üzerinden
  ayarlanabilir bir hedef tur sayısı eklenerek bu eşik genelleştirilebilir.
- **"Tur" kavramı** (cüzler arası dönen tur, klasik Osmanlı usulü) şu an yalnızca has
  tarafında (`JuzTurCount`) takip edilir; ham tarafı cüz-lineer ilerler (bir cüz bitmeden
  diğerine geçilmez). Kursunuz karışık usul kullanıyorsa bu, mevcut esnekliği koruyacak
  şekilde bilinçli olarak değiştirilmemiştir.
- Tailwind CSS, hızlı teslimat için CDN üzerinden (`cdn.tailwindcss.com`) kullanılmaktadır.
  Üretimde daha küçük dosya boyutu isterseniz `django-tailwind` ile derleme adımına geçilebilir;
  mevcut şablonlar sınıf isimleri aynı kaldığı için uyumludur.
- Raporlar PDF için **reportlab**, Excel için **openpyxl** kütüphaneleriyle sunucu tarafında
  anlık üretilir; ayrı bir dosya depolama servisi gerekmez.
- Denetim/audit log şu an sınırlıdır — her kayıtta `created_by` alanı var ama kim neyi ne zaman
  değiştirdi diye genel bir log tutulmuyor.

## 6. Sırada Ne Var? (SRS Bölüm 16 - Gelecek Özellikler)

Aşağıdaki maddeler mevcut mimariye kolayca eklenebilecek şekilde tasarlanmıştır:
makine öğrenmesi destekli kişiselleştirilmiş tahminler, WhatsApp/SMS ve e-posta bildirimleri,
çoklu kurum desteği, mobil uygulama, sesli ders değerlendirme, cüz bazlı ayarlanabilir hedef
tur sayısı, genel değişiklik/audit log.

