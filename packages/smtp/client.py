from __future__ import annotations

import smtplib
import threading
from email.mime.multipart import MIMEMultipart

from packages.settings import get_settings
from packages.smtp.schema import EmailMessage
from packages.smtp.template import render_html_template


class SmtpClient:
    _server: smtplib.SMTP | None = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        if not get_settings().smtp_enabled:
            raise RuntimeError("SMTP devre dışı — smtp_email ve smtp_password ortam değişkenlerini tanımlayın.")

        with self._lock:
            if SmtpClient._server is None:
                SmtpClient._server = self._connect_new()

    def _connect_new(self) -> smtplib.SMTP:
        s = get_settings()

        server = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=s.smtp_timeout)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(s.smtp_email, s.smtp_password)
        return server

    def _get_server(self) -> smtplib.SMTP:
        if SmtpClient._server is None:
            SmtpClient._server = self._connect_new()
        return SmtpClient._server

    def _reset_server(self) -> None:
        if SmtpClient._server is not None:
            try:
                SmtpClient._server.quit()
            except Exception:
                pass
            SmtpClient._server = None

    def send_template(self, template_name: str, message: EmailMessage) -> None:
        ctx = message.merged_template_context()
        html = render_html_template(template_name, **ctx)
        self.send(message.model_copy(update={"html": html}))

    def send(self, message: EmailMessage) -> None:
        s = get_settings()
        msg: MIMEMultipart = message.to_mime(s.smtp_email)
        recipients = message.recipients()
        payload = msg.as_string()

        with self._lock:
            try:
                self._get_server().sendmail(s.smtp_email, recipients, payload)
            except (smtplib.SMTPServerDisconnected, OSError):
                self._reset_server()
                self._get_server().sendmail(s.smtp_email, recipients, payload)

    @classmethod
    def close_shared(cls) -> None:
        """Paylaşımlı bağlantıyı kapatır (ör. kapanışta)."""
        with cls._lock:
            if cls._server is not None:
                try:
                    cls._server.quit()
                except Exception:
                    pass
                cls._server = None
