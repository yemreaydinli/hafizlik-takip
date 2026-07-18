from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="list"),
    path("<int:pk>/okundu/", views.mark_as_read, name="mark_read"),
]
