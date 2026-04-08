"""Event Service — E-posta bildirim yardimcilari."""
from __future__ import annotations

from packages.settings import get_settings
from packages.smtp.client import SmtpClient
from packages.smtp.schema import EmailSchema
from packages.database.models.event import Event
from ..logger import _logger


def _get_smtp() -> SmtpClient | None:
    """SMTP client'i doner, devre disiysa None."""
    s = get_settings()
    if not s.smtp_email or not s.smtp_password:
        return None
    return SmtpClient(
        email=s.smtp_email,
        password=s.smtp_password,
        host=s.smtp_host,
        port=s.smtp_port,
        timeout=s.smtp_timeout,
    )


def send_admin_notification(event: Event) -> None:
    """Admin'e yeni etkinlik talebi e-postasi gonderir."""
    s = get_settings()
    smtp = _get_smtp()
    if not smtp or not s.admin_email:
        return
    try:
        subject = f"Yeni Etkinlik Talebi: {event.name}"
        body = (
            f"Etkinlik: {event.name}\n"
            f"Konu: {event.topic}\n"
            f"Aciklama: {event.description}\n"
            f"Tarih: {event.date} {event.time}\n"
            f"Sure: {event.duration_minutes} dakika\n"
            f"Lokasyon: {event.location_type}\n"
            f"Link: {event.link or '—'}\n"
            f"YZTA Talep: {event.yzta_request or '—'}\n"
            f"Talep Eden: {event.creator_slack_id}\n"
        )
        schema = EmailSchema(to=s.admin_email, subject=subject, body=body)
        smtp.send(schema)
    except Exception as e:
        _logger.error("[EVT-EMAIL] Admin bildirimi gonderilemedi: %s", e)


def send_user_status_email(user_email: str, event: Event, status: str, admin_note: str | None = None) -> None:
    """Kullaniciya onay/red/timeout e-postasi gonderir."""
    smtp = _get_smtp()
    if not smtp or not user_email:
        return
    try:
        status_text = {"approved": "Onaylandi", "rejected": "Reddedildi", "timeout": "Zaman Asimi"}.get(status, status)
        subject = f"Etkinlik {status_text}: {event.name}"
        body = (
            f"Etkinlik: {event.name}\n"
            f"Tarih: {event.date} {event.time}\n"
            f"Durum: {status_text}\n"
        )
        if admin_note:
            body += f"Admin Notu: {admin_note}\n"
        schema = EmailSchema(to=user_email, subject=subject, body=body)
        smtp.send(schema)
    except Exception as e:
        _logger.error("[EVT-EMAIL] Kullanici bildirimi gonderilemedi: %s", e)


def send_reminder_email(user_email: str, event: Event, reminder_type: str = "day") -> None:
    """Hatirlatma e-postasi gonderir (gun basi veya 10dk oncesi)."""
    smtp = _get_smtp()
    if not smtp or not user_email:
        return
    try:
        if reminder_type == "10min":
            subject = f"10 Dakika Sonra: {event.name}"
        else:
            subject = f"Bugun: {event.name}"
        body = (
            f"Etkinlik: {event.name}\n"
            f"Saat: {event.time.strftime('%H:%M')}\n"
            f"Sure: {event.duration_minutes} dakika\n"
            f"Link: {event.link or '—'}\n"
        )
        schema = EmailSchema(to=user_email, subject=subject, body=body)
        smtp.send(schema)
    except Exception as e:
        _logger.error("[EVT-EMAIL] Hatirlatma gonderilemedi: %s", e)


def send_cancellation_email(user_email: str, event: Event) -> None:
    """Iptal bildirimi e-postasi gonderir."""
    smtp = _get_smtp()
    if not smtp or not user_email:
        return
    try:
        subject = f"Etkinlik Iptal Edildi: {event.name}"
        body = (
            f"Etkinlik: {event.name}\n"
            f"Tarih: {event.date} {event.time}\n"
            f"Bu etkinlik iptal edilmistir.\n"
        )
        schema = EmailSchema(to=user_email, subject=subject, body=body)
        smtp.send(schema)
    except Exception as e:
        _logger.error("[EVT-EMAIL] Iptal bildirimi gonderilemedi: %s", e)
