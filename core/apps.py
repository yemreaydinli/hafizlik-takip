from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Django Admin panelinin genel başlıklarını ve karşılama metnini Türkçeleştir.
        from django.contrib import admin
        admin.site.site_header = "Hafızlık Takip Sistemi — Yönetim Paneli"
        admin.site.site_title = "Hafızlık Takip Yönetimi"
        admin.site.index_title = "Yönetim Paneline Hoş Geldiniz"
