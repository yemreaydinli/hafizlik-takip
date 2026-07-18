def notifications_context(request):
    if not request.user.is_authenticated:
        return {}
    from notifications.models import Notification
    qs = Notification.objects.filter(is_read=False)
    if not request.user.is_admin_role:
        qs = qs.filter(teacher=request.user)
    return {"unread_notifications_count": qs.count(), "unread_notifications": qs[:5]}
