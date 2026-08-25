from django.core.mail import EmailMessage
from accounts.utils import get_site_email_connection, get_site_base_url
import logging

logger = logging.getLogger(__name__)

def send_ticket_assigned_email(ticket, technician=None):
    """
    Send an automated notification email to the technician who is allotted for a ticket
    from the admin-configured site email with direct LAN portal link.
    """
    tech = technician or ticket.assigned_technician
    if not tech or not tech.email:
        return False

    tech_name = tech.get_full_name() or tech.username
    reporter_name = ticket.reporter.get_full_name() or ticket.reporter.username if ticket.reporter else "User"
    reporter_email = ticket.reporter.email if ticket.reporter else "Not specified"
    category_name = ticket.category.name if ticket.category else "General IT"
    priority_name = ticket.get_urgency_display()

    base_url = get_site_base_url()
    ticket_url = f"{base_url}/tickets/{ticket.pk}/"

    conn, from_email, site_name = get_site_email_connection()

    subject = f"[{site_name}] New Ticket Assigned: #{ticket.ticket_number} - {ticket.title}"
    body = f"""Hello {tech_name},

A new support ticket has been allotted to you on {site_name}:

============================================================
Ticket ID:    #{ticket.ticket_number}
Title:        {ticket.title}
Category:     {category_name}
Priority:     {priority_name}
Reported By:  {reporter_name} ({reporter_email})
Created At:   {ticket.created_at.strftime('%B %d, %Y at %I:%M %p')}
============================================================

Problem Description:
{ticket.description}

Direct Link to Ticket:
{ticket_url}

Please log in to your Technician Dashboard to review and begin work on this request.

Regards,
{site_name} Automated Notification System
"""

    try:
        msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[tech.email],
            connection=conn,
        )
        msg.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch ticket assigned email to {tech.email}: {e}")
        return False


def send_ticket_resolved_email(ticket, resolution_notes=None):
    """
    Send an email notification to the user who raised the ticket when the technician resolves it.
    """
    if not ticket.reporter or not ticket.reporter.email:
        return False

    reporter_name = ticket.reporter.get_full_name() or ticket.reporter.username
    tech = ticket.assigned_technician
    tech_name = tech.get_full_name() or tech.username if tech else "Assigned Technician"
    category_name = ticket.category.name if ticket.category else "General"

    notes_text = resolution_notes
    if not notes_text:
        latest_comment = ticket.comments.order_by('-created_at').first()
        notes_text = latest_comment.content if latest_comment else "Issue resolved and verified by technician."

    base_url = get_site_base_url()
    ticket_url = f"{base_url}/tickets/{ticket.pk}/"

    conn, from_email, site_name = get_site_email_connection()

    subject = f"[{site_name}] Your Ticket #{ticket.ticket_number} has been Resolved"
    body = f"""Hello {reporter_name},

Your support request #{ticket.ticket_number} ("{ticket.title}") has been marked as RESOLVED by technician {tech_name}:

============================================================
Ticket ID:    #{ticket.ticket_number}
Title:        {ticket.title}
Category:     {category_name}
Status:       Resolved (Pending Your Verification)
============================================================

Technician Resolution Notes:
{notes_text}

Review Ticket & Confirm Closure:
{ticket_url}

Next Steps:
- If the issue is solved, please click the link above and click "Confirm Closure".
- If the problem still persists, you can leave a reply or reopen the ticket.

Best regards,
{site_name} Automated Notification System
"""

    try:
        msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[ticket.reporter.email],
            connection=conn,
        )
        msg.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch ticket resolved email to {ticket.reporter.email}: {e}")
        return False
