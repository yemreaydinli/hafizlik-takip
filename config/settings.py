"""
Hafızlık Takip Sistemi - Django Settings

Ortam değişkenleri (.env dosyası) üzerinden yapılandırılır.
Yerelde SQLite, üretimde (Render/Railway/Neon/Supabase) DATABASE_URL ile PostgreSQL kullanır.
"""
import os
import sys
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"

# Üretimde (DEBUG=False) SECRET_KEY ortam değişkeni ZORUNLUDUR; tanımlı değilse
# uygulama zayıf bir varsayılanla sessizce çalışmak yerine açılışta hata verir.
_DEV_SECRET_KEY = "django-insecure-dev-key-CHANGE-ME-IN-PRODUCTION"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = _DEV_SECRET_KEY
    else:
        raise RuntimeError(
            "DJANGO_SECRET_KEY ortam değişkeni tanımlı olmalıdır (DJANGO_DEBUG=False iken)."
        )
elif not DEBUG and (SECRET_KEY == _DEV_SECRET_KEY or SECRET_KEY.startswith("change-this")):
    raise RuntimeError("DJANGO_SECRET_KEY örnek/varsayılan bir değer olamaz; rastgele uzun bir anahtar üretin.")

ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django_htmx",
    "accounts",
    "core",
    "students",
    "lessons",
    "memorization",
    "predictions",
    "notifications",
    "reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.notifications_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database: DATABASE_URL varsa (Postgres/Neon/Supabase) onu kullanır,
# yoksa yerel geliştirme için SQLite kullanılır.
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=True)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
RUNNING_TESTS = len(sys.argv) > 1 and sys.argv[1] == "test"
STORAGES = {
    "staticfiles": {
        # Testlerde collectstatic çalıştırılmadığı için manifest yoktur; manifest tabanlı
        # depolama yerine düz depolama kullanılır (aksi halde {% static %} kullanan
        # şablonlar "Missing staticfiles manifest entry" hatasıyla düşer).
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if RUNNING_TESTS
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# ---------------------------------------------------------------------------
# Üretim güvenlik ayarları (yalnızca DEBUG=False iken etkin).
# Render gibi bir reverse proxy arkasında HTTPS, X-Forwarded-Proto başlığı ile bildirilir.
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = os.getenv("DJANGO_SSL_REDIRECT", "True") == "True"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", "3600"))  # sorunsuzsa 31536000'e (1 yıl) çıkarın
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 12  # 12 saat

# Hafızlık sistem sabitleri
TOTAL_QURAN_PAGES = 604
PREDICTION_SIMPLE_AVG_DAYS = 30      # İlk N gün boyunca basit ortalama kullanılır
PREDICTION_EMA_ALPHA = 0.25          # EMA düzleştirme katsayısı
ALERT_PAUSE_DAYS = 5                 # Duraklama uyarısı için gün eşiği
ALERT_CONSECUTIVE_ABSENCE = 3        # Ardışık devamsızlık uyarı eşiği
ALERT_PERFORMANCE_DROP_RATIO = 0.35  # %35 ve üzeri düşüş uyarı verir
ALERT_TARGET_DEVIATION_DAYS = 30     # Hedeften sapma eşiği (gün)

# ---------------------------------------------------------------------------
# Logging: DEBUG=False (üretim/Render) iken Django varsayılan olarak 500
# hatalarının traceback'ini konsola YAZMAZ (sadece ADMINS'e e-posta göndermeye
# çalışır). Bu da Render "Logs" sekmesinde sadece "500" diyen erişim satırları
# görüp gerçek hatayı göremeye neden olur. Aşağıdaki yapılandırma, DEBUG
# durumundan bağımsız olarak tüm hata traceback'lerini stdout'a (Render'ın
# yakaladığı konsola) basar.
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
