from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("hesap/", include("accounts.urls")),
    path("ogrenciler/", include("students.urls")),
    path("dersler/", include("lessons.urls")),
    path("hafizlik-haritasi/", include("memorization.urls")),
    path("tahminler/", include("predictions.urls")),
    path("bildirimler/", include("notifications.urls")),
    path("raporlar/", include("reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
