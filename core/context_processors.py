def notifications_context(request):
    if not request.user.is_authenticated:
        return {}
    from notifications.models import Notification
    qs = Notification.objects.filter(is_read=False)
    if not request.user.is_admin_role:
        qs = qs.filter(teacher=request.user)
    return {"unread_notifications_count": qs.count(), "unread_notifications": qs[:5]}


def backup_context(request):
    """Yalnızca yönetici için: yedek gecikmişse tüm sayfalarda gösterilecek uyarı verisi."""
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated and user.is_admin_role):
        return {}
    from .backup import get_backup_status
    status = get_backup_status()
    return {"backup_status": status, "backup_warning": status["warn"]}
