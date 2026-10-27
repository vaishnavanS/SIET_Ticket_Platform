import socket
import logging
from urllib.parse import urlparse
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.core.mail import get_connection, EmailMessage
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)
signer = TimestampSigner(salt='siet-email-verification')


def get_lan_ip():
    """Detects the primary active LAN IP address of this machine"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def get_site_base_url(request=None):
    """
    Returns the absolute base URL (protocol + host + port) for generating external links
    in emails so all devices across the LAN / Internet can access the platform directly.
    """
    try:
        from accounts.models import SiteEmailSetting
        setting = SiteEmailSetting.get_setting()
        if setting.site_url and setting.site_url.strip():
            return setting.site_url.strip().rstrip('/')
    except Exception:
        pass

    lan_ip = get_lan_ip()

    if request:
        try:
            host = request.get_host()
            # If the request comes from localhost/127.0.0.1, replace with active LAN IP for emails!
            if 'localhost' in host or '127.0.0.1' in host:
                port = request.get_port()
                port_suffix = f":{port}" if port and str(port) not in ('80', '443') else ""
                return f"{request.scheme}://{lan_ip}{port_suffix}"
            return request.build_absolute_uri('/').rstrip('/')
        except Exception:
            pass

    # Default fallback
    return f"http://{lan_ip}:8000"


def get_site_email_connection():
    """
    Returns configured (connection, from_email_string, site_name)
    based on admin-configured SiteEmailSetting.
    """
    try:
        from accounts.models import SiteEmailSetting
        email_cfg = SiteEmailSetting.get_setting()
        from_header = f"{email_cfg.site_name} <{email_cfg.from_email}>"

        if email_cfg.smtp_backend == 'console':
            if getattr(settings, 'EMAIL_BACKEND', '') == 'django.core.mail.backends.locmem.EmailBackend':
                conn = get_connection('django.core.mail.backends.locmem.EmailBackend')
            else:
                conn = get_connection('django.core.mail.backends.console.EmailBackend')
            return conn, from_header, email_cfg.site_name

        use_ssl = bool(email_cfg.smtp_use_ssl)
        use_tls = bool(email_cfg.smtp_use_tls) and not use_ssl
        clean_pwd = (email_cfg.smtp_password or '').replace(' ', '').strip()

        conn = get_connection(
            'django.core.mail.backends.smtp.EmailBackend',
            host=email_cfg.smtp_host,
            port=email_cfg.smtp_port,
            username=email_cfg.smtp_user.strip(),
            password=clean_pwd,
            use_tls=use_tls,
            use_ssl=use_ssl,
            timeout=10,
        )
        return conn, from_header, email_cfg.site_name
    except Exception as e:
        logger.warning(f"Falling back to default settings email backend: {e}")
        return get_connection(), getattr(settings, 'DEFAULT_FROM_EMAIL', 'SIET Helpdesk <helpdesk@siet.edu.in>'), "SIET Helpdesk"


def generate_verification_token(user):
    """Generate a secure, signed verification token containing user ID and email"""
    payload = f"{user.id}:{user.email}"
    return signer.sign(payload)


def verify_token(token, max_age_seconds=86400):
    """
    Verify and unpack a signed token within the expiry window (default 24h).
    Returns (user_id, email) or (None, None) if invalid/expired.
    """
    try:
        original = signer.unsign(token, max_age=max_age_seconds)
        parts = original.split(':', 1)
        if len(parts) == 2:
            return int(parts[0]), parts[1]
    except (BadSignature, SignatureExpired, ValueError) as e:
        logger.warning(f"Verification token failed validation: {e}")
    return None, None


def send_verification_email(request, user):
    """
    Queues an official email verification link to user's registered email
    containing the LAN IP address so devices on the local network can verify directly.
    """
    if not user.email:
        return False, "No email address is associated with this account."

    token = generate_verification_token(user)
    base_url = get_site_base_url(request)
    path = reverse('accounts:verify_email', kwargs={'token': token})
    verify_url = f"{base_url}{path}"
    user_display = user.get_full_name() or user.username

    _, _, site_name = get_site_email_connection()

    subject = f"[{site_name}] Verify your email address"
    body = f"""Hello {user_display},

Thank you for using the {site_name} Platform.

Please verify that '{user.email}' is your active email address by clicking the link below:

{verify_url}

This verification link is secure and will expire in 24 hours.

If you are accessing from any phone, laptop, or computer connected to the campus LAN, this link will open the portal directly.

Best regards,
{site_name} Administration
"""

    try:
        queue_email(
            recipient_email=user.email,
            recipient_name=user_display,
            subject=subject,
            body=body,
            notification_type='email_verification',
        )
        return True, f"Verification link has been queued and will be sent to {user.email}. Please check your inbox."
    except Exception as e:
        logger.error(f"Failed to queue email verification to {user.email}: {e}")
        return False, f"Could not dispatch email: {str(e)}"


def queue_email(recipient_email, subject, body, html_message=None, recipient_name='', ticket=None, notification_type='general'):
    """
    Saves an outgoing email to the EmailQueue table for asynchronous dispatch via cron.
    Returns the created EmailQueue instance immediately without blocking on SMTP network latency.
    """
    from accounts.models import EmailQueue
    queued = EmailQueue.objects.create(
        recipient_email=recipient_email,
        recipient_name=recipient_name or '',
        subject=subject,
        body=body,
        html_message=html_message or '',
        ticket=ticket,
        notification_type=notification_type,
        status=EmailQueue.Status.PENDING,
    )

    # When running unit tests with locmem backend, automatically dispatch in-memory
    # so mail.outbox is populated for test assertions without any external network delay.
    if getattr(settings, 'EMAIL_BACKEND', '') == 'django.core.mail.backends.locmem.EmailBackend':
        try:
            dispatch_single_queued_email(queued)
        except Exception as e:
            logger.warning(f"Failed to auto-dispatch queued email in locmem test mode: {e}")

    return queued


def dispatch_single_queued_email(queued_email, connection=None, from_header=None):
    """
    Dispatches a single EmailQueue record using the provided connection
    or a new connection from get_site_email_connection().
    Updates the record's status, sent_at, attempts, and error_message.
    """
    from django.utils import timezone
    from accounts.models import EmailQueue

    conn = connection
    hdr = from_header
    if conn is None:
        conn, hdr, _ = get_site_email_connection()

    try:
        msg = EmailMessage(
            subject=queued_email.subject,
            body=queued_email.body,
            from_email=hdr or getattr(settings, 'DEFAULT_FROM_EMAIL', 'helpdesk@siet.edu.in'),
            to=[queued_email.recipient_email],
            connection=conn,
        )
        if queued_email.html_message:
            msg.content_subtype = "html"
        msg.send(fail_silently=False)
        queued_email.status = EmailQueue.Status.SENT
        queued_email.sent_at = timezone.now()
        queued_email.error_message = ''
        queued_email.save(update_fields=['status', 'sent_at', 'error_message'])
        return True
    except Exception as e:
        queued_email.attempts += 1
        queued_email.error_message = str(e)
        if queued_email.attempts >= queued_email.max_attempts:
            queued_email.status = EmailQueue.Status.FAILED
        queued_email.save(update_fields=['attempts', 'error_message', 'status'])
        raise


def process_email_queue(limit=50, retry_failed=False):
    """
    Processes pending (and optionally failed retryable) queued emails in a batch.
    Reuses a single SMTP connection for maximum efficiency and speed.
    Returns a dict with summary counts: {'processed': X, 'sent': Y, 'failed': Z}.
    """
    from django.utils import timezone
    from django.db import models
    from accounts.models import EmailQueue

    status_filter = [EmailQueue.Status.PENDING]
    if retry_failed:
        status_filter.append(EmailQueue.Status.FAILED)

    qs = EmailQueue.objects.filter(
        status__in=status_filter,
        attempts__lt=models.F('max_attempts')
    ).order_by('created_at')[:limit]

    emails = list(qs)
    if not emails:
        return {'processed': 0, 'sent': 0, 'failed': 0}

    conn, from_header, site_name = get_site_email_connection()
    sent_count = 0
    fail_count = 0

    try:
        conn.open()
    except Exception as e:
        logger.error(f"Failed to open email connection for queue dispatch: {e}")
        for em in emails:
            em.attempts += 1
            em.error_message = f"Connection error: {e}"
            if em.attempts >= em.max_attempts:
                em.status = EmailQueue.Status.FAILED
            em.save(update_fields=['attempts', 'error_message', 'status'])
            fail_count += 1
        return {'processed': len(emails), 'sent': 0, 'failed': fail_count}

    try:
        for em in emails:
            try:
                msg = EmailMessage(
                    subject=em.subject,
                    body=em.body,
                    from_email=from_header,
                    to=[em.recipient_email],
                    connection=conn,
                )
                if em.html_message:
                    msg.content_subtype = "html"
                msg.send(fail_silently=False)
                em.status = EmailQueue.Status.SENT
                em.sent_at = timezone.now()
                em.error_message = ''
                em.save(update_fields=['status', 'sent_at', 'error_message'])
                sent_count += 1
            except Exception as e:
                em.attempts += 1
                em.error_message = str(e)
                if em.attempts >= em.max_attempts:
                    em.status = EmailQueue.Status.FAILED
                em.save(update_fields=['attempts', 'error_message', 'status'])
                fail_count += 1
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return {'processed': len(emails), 'sent': sent_count, 'failed': fail_count}

