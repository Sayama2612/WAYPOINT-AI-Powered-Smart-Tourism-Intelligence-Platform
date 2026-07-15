import os
import smtplib
from email.message import EmailMessage


def send_email_smtp(to_email: str, subject: str, body: str, from_email: str = None) -> bool:
    """Send a plain-text email using SMTP settings from environment variables.

    Required env vars: SMTP_HOST, SMTP_PORT. Optional: SMTP_USER, SMTP_PASS, SMTP_FROM, SMTP_USE_SSL
    Returns True on success.
    """
    host = os.environ.get('SMTP_HOST')
    port = int(os.environ.get('SMTP_PORT', '0') or 0)
    if not host or not port:
        return False
    user = os.environ.get('SMTP_USER')
    password = os.environ.get('SMTP_PASS')
    default_from = os.environ.get('SMTP_FROM') or from_email or f'no-reply@{host}'
    use_ssl = os.environ.get('SMTP_USE_SSL', '0') in ('1', 'true', 'True')
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = default_from
        msg['To'] = to_email
        msg.set_content(body)
        if use_ssl:
            with smtplib.SMTP_SSL(host, port) as s:
                if user and password:
                    s.login(user, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port) as s:
                s.ehlo()
                s.starttls()
                if user and password:
                    s.login(user, password)
                s.send_message(msg)
        return True
    except Exception:
        return False


def send_magic_link_email(to_email: str, link: str, subject: str = 'Your WAYPOINT magic login link') -> bool:
    body = f"Use this link to sign in to WAYPOINT:\n\n{link}\n\nIf you didn't request this, ignore this email."
    return send_email_smtp(to_email, subject, body)
