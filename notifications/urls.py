from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="list"),
    path("tumunu-oku/", views.mark_all_as_read, name="mark_all_read"),
    path("<int:pk>/okundu/", views.mark_as_read, name="mark_read"),
]
