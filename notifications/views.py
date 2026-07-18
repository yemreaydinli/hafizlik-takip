from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import ListView

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "notifications/list.html"
    context_object_name = "notifications"
    paginate_by = 30

    def get_queryset(self):
        user = self.request.user
        qs = Notification.objects.select_related("student")
        if not user.is_admin_role:
            qs = qs.filter(teacher=user)
        return qs


def mark_as_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk)
    if request.user.is_admin_role or notification.teacher_id == request.user.id:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return redirect(reverse("notifications:list"))
