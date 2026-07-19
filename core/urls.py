from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("sistem/sifirla/", views.SystemResetView.as_view(), name="system_reset"),
]
