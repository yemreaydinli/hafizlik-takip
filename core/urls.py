from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("yedek/", views.BackupView.as_view(), name="backup"),
]
