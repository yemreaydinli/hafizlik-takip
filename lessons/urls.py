from django.urls import path
from . import views

app_name = "lessons"

urlpatterns = [
    path("", views.LessonListView.as_view(), name="list"),
    path("bugun/", views.daily_entry, name="daily_entry"),
    path("ogrenci/<int:student_pk>/yeni/", views.lesson_create, name="create"),
    path("<int:pk>/duzenle/", views.lesson_update, name="update"),
    path("<int:pk>/sil/", views.lesson_delete, name="delete"),
]
