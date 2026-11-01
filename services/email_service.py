import smtplib
from smtplib import SMTPException
from email.message import EmailMessage

from flask import current_app


def send_otp_email(recipient, code):
    settings = current_app.config
    required = ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM")
    missing = [key for key in required if not settings.get(key)]
    if missing:
        raise RuntimeError(
            "Email delivery is not configured. Set: " + ", ".join(missing)
        )

    message = EmailMessage()
    message["Subject"] = "Your PIXORA verification code"
    message["From"] = settings["MAIL_FROM"]
    message["To"] = recipient
    message.set_content(
        f"Your PIXORA verification code is {code}. It expires in 10 minutes."
    )
    try:
        with smtplib.SMTP(settings["SMTP_HOST"], settings["SMTP_PORT"], timeout=15) as server:
            server.starttls()
            server.login(settings["SMTP_USER"], settings["SMTP_PASSWORD"])
            server.send_message(message)
    except (OSError, SMTPException) as exc:
        raise RuntimeError("The verification email could not be delivered.") from exc
