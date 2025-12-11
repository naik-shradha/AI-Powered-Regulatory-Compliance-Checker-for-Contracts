# email_utils.py
import os
import logging
from email.message import EmailMessage
from pathlib import Path
import smtplib

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@example.com")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def build_message(subject: str, to_email: str, plain: str, html: str, attachment_path: str = None) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")

    if attachment_path:
        p = Path(attachment_path)
        if p.exists():
            with open(p, "rb") as f:
                data = f.read()
            # Attach as PDF
            msg.add_attachment(data, maintype="application", subtype="pdf", filename=p.name)
        else:
            logger.warning("Attachment %s not found", attachment_path)
    return msg

def send_email_smtp(subject: str, to_email: str, plain: str, html: str, attachment_path: str = None, timeout: int = 30) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error("SMTP credentials are missing. Set SMTP_USER and SMTP_PASSWORD in your environment.")
        return False

    msg = build_message(subject, to_email, plain, html, attachment_path)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=timeout) as smtp:
            smtp.ehlo()
            # Gmail uses STARTTLS on port 587
            smtp.starttls()
            smtp.ehlo()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
        logger.info("Email sent to %s via SMTP (Gmail).", to_email)
        return True
    except Exception as e:
        logger.exception("Failed to send SMTP email: %s", e)
        return False
