from django.urls import path
from . import views

app_name = "predictions"

urlpatterns = [
    path("ogrenci/<int:student_pk>/", views.PredictionDetailView.as_view(), name="detail"),
]
