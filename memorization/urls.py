from django.urls import path
from . import views

app_name = "memorization"

urlpatterns = [
    path("ogrenci/<int:student_pk>/", views.MemorizationMapView.as_view(), name="map"),
]
