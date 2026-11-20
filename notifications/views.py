from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["unread_total"] = self.get_queryset().filter(is_read=False).count()
        return ctx


def _visible_notifications(user):
    qs = Notification.objects.all()
    return qs if user.is_admin_role else qs.filter(teacher=user)


@login_required
@require_POST
def mark_as_read(request, pk):
    notification = get_object_or_404(_visible_notifications(request.user), pk=pk)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return redirect(reverse("notifications:list"))


@login_required
@require_POST
def mark_all_as_read(request):
    updated = _visible_notifications(request.user).filter(is_read=False).update(is_read=True)
    if updated:
        messages.success(request, f"{updated} uyarı okundu olarak işaretlendi.")
    return redirect(reverse("notifications:list"))
