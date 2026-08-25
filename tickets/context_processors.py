from .models import TicketNotification, Ticket, TicketStatus

def ticket_notifications_processor(request):
    """Provides unread notifications and pending resolution confirmation counts globally"""
    if not request.user.is_authenticated:
        return {
            'unread_notifications_count': 0,
            'recent_notifications': [],
            'pending_resolutions_count': 0,
        }

    notifications_qs = TicketNotification.objects.filter(recipient=request.user)
    unread_count = notifications_qs.filter(is_read=False).count()
    recent_notifications = notifications_qs.filter(is_read=False)[:5]

    # Count of tickets reported by normal user that are in Resolved state awaiting confirmation
    pending_resolutions = Ticket.objects.filter(
        reporter=request.user,
        status=TicketStatus.RESOLVED
    ).count()

    return {
        'unread_notifications_count': unread_count,
        'recent_notifications': recent_notifications,
        'pending_resolutions_count': pending_resolutions,
    }
