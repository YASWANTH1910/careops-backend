"""
Email service using Python's built-in smtplib.
Falls back to console logging if SMTP is not configured.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)


def _get_smtp_settings():
    """Load SMTP settings lazily to avoid import-time errors."""
    try:
        from app.core.config import settings
        return {
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "user": settings.SMTP_USER,
            "password": settings.SMTP_PASSWORD,
            "from_email": settings.SMTP_FROM,
            "configured": bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD
                               and settings.SMTP_PASSWORD != "your-app-password"),
        }
    except Exception as e:
        logger.warning(f"[Email] Could not load SMTP settings: {e}")
        return {"configured": False}


def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
) -> bool:
    """
    Send an email via SMTP (built-in smtplib).

    Args:
        to_email:   Recipient email address
        subject:    Email subject line
        body:       Plain-text body
        html_body:  Optional HTML body (if provided, sends multipart/alternative)

    Returns:
        True on success, False on failure (non-blocking — never raises).
    """
    cfg = _get_smtp_settings()

    if not cfg.get("configured"):
        # Graceful fallback: just log the email content
        logger.info(
            f"[Email] SMTP not configured. Would send to {to_email!r}:\n"
            f"  Subject: {subject}\n"
            f"  Body: {body[:200]}"
        )
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = cfg["from_email"]
        msg["To"] = to_email

        msg.attach(MIMEText(body, "plain", "utf-8"))
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["from_email"], [to_email], msg.as_string())

        logger.info(f"[Email] Sent to {to_email!r} — Subject: {subject!r}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "[Email] SMTP authentication failed. "
            "For Gmail, use an App Password (not your regular password): "
            "https://myaccount.google.com/apppasswords"
        )
        return False
    except Exception as e:
        logger.error(f"[Email] Failed to send to {to_email!r}: {e}")
        return False


# ── Pre-built template senders ────────────────────────────────────────────────

def send_booking_confirmation(contact_name: str, contact_email: str, start_time, service_type: str = "") -> bool:
    """Send booking confirmation email to a contact."""
    formatted_time = start_time.strftime("%A, %B %d %Y at %I:%M %p")
    subject = "Your Booking is Confirmed ✅"
    body = (
        f"Hi {contact_name},\n\n"
        f"Your booking has been confirmed!\n\n"
        f"📅 Date & Time: {formatted_time}\n"
        f"💼 Service: {service_type or 'General Appointment'}\n\n"
        f"If you need to reschedule or cancel, please contact us.\n\n"
        f"See you soon,\nThe CareOps Team"
    )
    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:auto;padding:24px">
      <h2 style="color:#4f46e5">Booking Confirmed ✅</h2>
      <p>Hi <strong>{contact_name}</strong>,</p>
      <p>Your booking has been confirmed!</p>
      <div style="background:#f1f5f9;border-radius:12px;padding:16px;margin:20px 0">
        <p>📅 <strong>{formatted_time}</strong></p>
        <p>💼 <strong>{service_type or 'General Appointment'}</strong></p>
      </div>
      <p>If you need to reschedule or cancel, please contact us.</p>
      <p>See you soon!<br><em>The CareOps Team</em></p>
    </div>
    """
    return send_email(contact_email, subject, body, html_body)


def send_booking_reminder(contact_name: str, contact_email: str, start_time, service_type: str = "") -> bool:
    """Send a 24-hour reminder email."""
    formatted_time = start_time.strftime("%A, %B %d %Y at %I:%M %p")
    subject = "Reminder: Your Appointment is Tomorrow 🔔"
    body = (
        f"Hi {contact_name},\n\n"
        f"This is a friendly reminder about your upcoming appointment:\n\n"
        f"📅 {formatted_time}\n"
        f"💼 {service_type or 'General Appointment'}\n\n"
        f"See you soon!\nThe CareOps Team"
    )
    return send_email(contact_email, subject, body)


def send_admin_new_lead_alert(admin_email: str, lead_name: str, lead_email: str, service_interest: str = "") -> bool:
    """Send admin alert when a new lead submits the public form."""
    subject = f"🆕 New Lead: {lead_name}"
    body = (
        f"A new lead has submitted the contact form.\n\n"
        f"Name:    {lead_name}\n"
        f"Email:   {lead_email}\n"
        f"Service: {service_interest or 'Not specified'}\n\n"
        f"Log in to CareOps to follow up."
    )
    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:auto;padding:24px">
      <h2 style="color:#4f46e5">🆕 New Lead Received</h2>
      <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:6px;color:#64748b">Name</td><td style="padding:6px;font-weight:bold">{lead_name}</td></tr>
        <tr><td style="padding:6px;color:#64748b">Email</td><td style="padding:6px;font-weight:bold">{lead_email}</td></tr>
        <tr><td style="padding:6px;color:#64748b">Service</td><td style="padding:6px">{service_interest or 'Not specified'}</td></tr>
      </table>
      <a href="http://localhost:5173/leads" style="display:inline-block;margin-top:20px;background:#4f46e5;color:white;padding:10px 20px;border-radius:8px;text-decoration:none">View in CareOps</a>
    </div>
    """
    return send_email(admin_email, subject, body, html_body)


def send_admin_new_booking_alert(admin_email: str, contact_name: str, start_time, service_type: str = "") -> bool:
    """Send admin alert when a new booking is created."""
    formatted_time = start_time.strftime("%A, %B %d %Y at %I:%M %p")
    subject = f"📅 New Booking: {contact_name}"
    body = (
        f"A new booking has been created.\n\n"
        f"Client:  {contact_name}\n"
        f"Time:    {formatted_time}\n"
        f"Service: {service_type or 'General Appointment'}\n\n"
        f"Log in to CareOps to manage this booking."
    )
    return send_email(admin_email, subject, body)
