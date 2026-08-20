import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def send_email(subject: str, body: str, to_email: str) -> None:
    if not settings.smtp_host or not settings.smtp_port or not settings.smtp_from_email:
        raise RuntimeError("SMTP settings are not configured")

    msg = MIMEMultipart()
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
        timeout=settings.outbound_request_timeout_seconds,
    ) as server:
        server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
