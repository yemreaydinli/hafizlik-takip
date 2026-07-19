from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("", views.ReportIndexView.as_view(), name="index"),
    path("olustur/", views.GenerateReportView.as_view(), name="generate"),
    path("ogrenci/<int:student_pk>/karne/", views.StudentReportCardView.as_view(), name="student_card"),
]
