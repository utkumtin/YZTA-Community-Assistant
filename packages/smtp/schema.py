from __future__ import annotations

from typing import Any

from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from pydantic import BaseModel, Field


class EmailMessage(BaseModel):
    """Şablonlu veya ham HTML/düz metin gönderimi için tek model."""

    to: list[str] = Field(..., description="Alıcı adresleri")
    cc: list[str] = Field(default_factory=list, description="CC")
    bcc: list[str] = Field(default_factory=list, description="BCC")
    subject: str = Field(..., description="Konu")
    reply_to: str | None = Field(None, description="Reply-To başlığı")

    text_plain: str | None = Field(None, description="Düz metin gövde (multipart/alternative)")
    html: str | None = Field(None, description="HTML gövde; şablon gönderiminde istemci doldurur")
    body: str | None = Field(None, description="İnsan okunur metin; şablon bağlamına `body` olarak otomatik eklenir (yoksa)")
    template_vars: dict[str, Any] = Field(default_factory=dict, description="Jinja şablonuna giden dinamik değişkenler")

    def merged_template_context(self) -> dict[str, Any]:
        """Şablon render için birleşik bağlam: ``template_vars`` + isteğe bağlı ``body`` (``message`` anahtarı da doldurulabilir)."""
        ctx: dict[str, Any] = dict(self.template_vars)
        if self.body is not None:
            ctx.setdefault("body", self.body)
            ctx.setdefault("message", self.body)
        return ctx

    def recipients(self) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for addr in (*self.to, *self.cc, *self.bcc):
            if addr not in seen:
                seen.add(addr)
                out.append(addr)
        return out

    def to_mime(self, from_addr: str) -> MIMEMultipart:
        if not self.html and not self.text_plain:
            raise ValueError("html veya text_plain alanlarından en az biri dolu olmalı")
        msg = MIMEMultipart("alternative")
        if self.text_plain:
            msg.attach(MIMEText(self.text_plain, "plain", "utf-8"))
        if self.html:
            msg.attach(MIMEText(self.html, "html", "utf-8"))

        msg["Subject"] = Header(self.subject, "utf-8")
        msg["From"] = from_addr
        msg["To"] = ", ".join(self.to)
        if self.cc:
            msg["Cc"] = ", ".join(self.cc)
        if self.reply_to:
            msg["Reply-To"] = self.reply_to
        return msg
