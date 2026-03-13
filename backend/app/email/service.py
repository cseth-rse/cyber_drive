# app/email/service.py
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import lru_cache

from fastapi import Depends

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_otp(self, to: str, otp: str) -> None:
        s = self.settings
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your Cyber Drive OTP"
        msg["From"] = s.email_from
        msg["To"] = to

        text = f"Your one-time password is: {otp}\n\nThis code expires in 10 minutes. Do not share it."
        html = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;
                    border:1px solid #e5e7eb;border-radius:8px;">
          <h2 style="color:#1d4ed8;margin-bottom:8px;">Cyber Drive</h2>
          <p style="color:#374151;">Use the code below to sign in.
             It expires in <strong>10 minutes</strong>.</p>
          <div style="font-size:36px;font-weight:bold;letter-spacing:8px;text-align:center;
                      padding:24px;background:#f3f4f6;border-radius:6px;
                      margin:24px 0;color:#111827;">{otp}</div>
          <p style="color:#6b7280;font-size:13px;">
            If you did not request this, you can safely ignore this email.</p>
        </div>"""

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        try:
            context = ssl.create_default_context() if s.email_secure else ssl._create_unverified_context()
            if s.email_secure:
                with smtplib.SMTP_SSL(s.email_host, s.email_port, context=context) as server:
                    server.login(s.email_user, s.email_pass)
                    server.sendmail(s.email_from, to, msg.as_string())
            else:
                with smtplib.SMTP(s.email_host, s.email_port) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.login(s.email_user, s.email_pass)
                    server.sendmail(s.email_from, to, msg.as_string())

            logger.info("OTP email sent to %s", to)
        except Exception as exc:
            logger.error("Failed to send OTP email to %s: %s", to, exc)
            raise


def get_email_service(settings: Settings = Depends(get_settings)) -> EmailService:
    return EmailService(settings)
