from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("giris/", views.LoginView.as_view(), name="login"),
    path("cikis/", views.LogoutView.as_view(), name="logout"),
    path("ogreticiler/", views.TeacherListView.as_view(), name="teacher_list"),
    path("ogreticiler/yeni/", views.TeacherCreateView.as_view(), name="teacher_create"),
    path("ogreticiler/<int:pk>/duzenle/", views.TeacherUpdateView.as_view(), name="teacher_update"),
    path("ogreticiler/<int:pk>/sil/", views.TeacherDeleteView.as_view(), name="teacher_delete"),
]
