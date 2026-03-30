from .builder import BlockBuilder, Formatter
from typing import List, Dict, Any, Optional

class Layouts:
    """
    Akademi Topluluk Asistanı için hazır, tutarlı UI şablonları.
    Her metod bir BLOCK LİSTESİ döner.
    """

    @staticmethod
    def error(title: str, message: str, details: Optional[str] = None) -> List[Dict]:
        """Kırmızı temalı (emoji ile) hata mesajı layoutu."""
        blocks = [
            BlockBuilder.header(f"🛑 {title}"),
            BlockBuilder.section(message)
        ]
        if details:
            blocks.append(BlockBuilder.context([f"ℹ️ *Hata Detayı:* {Formatter.code(details)}"]))
        return blocks

    @staticmethod
    def success(title: str, message: str, action_text: Optional[str] = None, action_id: Optional[str] = None) -> List[Dict]:
        """Yeşil temalı başarı mesajı layoutu."""
        blocks = [
            BlockBuilder.header(f"✅ {title}"),
            BlockBuilder.section(message)
        ]
        if action_text and action_id:
            blocks.append(BlockBuilder.actions([
                BlockBuilder.button(action_text, action_id, style="primary")
            ]))
        return blocks

    @staticmethod
    def info_card(title: str, description: str, icon: str = "ℹ️", fields: Optional[List[str]] = None) -> List[Dict]:
        """Bilgilendirme kartı (örn. profil, yardım içeriği)."""
        blocks = [
            BlockBuilder.header(f"{icon} {title}"),
            BlockBuilder.section(description)
        ]
        if fields:
            blocks.append(BlockBuilder.section(fields=fields))
        return blocks

    @staticmethod
    def challenge_invitation(
        title: str, description: str, theme: str, difficulty: str,
        action_id: str, challenge_id: str
    ) -> List[Dict]:
        """Challenge katılım ilanı layoutu. Buton tıklanınca challenge_id action_value olarak gelir."""
        return [
            BlockBuilder.header(f"🚀 Yeni Challenge: {title}"),
            BlockBuilder.section(description),
            BlockBuilder.section(fields=[
                f"*Tema:* {theme}",
                f"*Zorluk:* {difficulty}"
            ]),
            BlockBuilder.divider(),
            BlockBuilder.actions([
                BlockBuilder.button("Katılmak İstiyorum! ✨", action_id, value=challenge_id, style="primary"),
                BlockBuilder.button("Detaylar 🔍", f"details_{action_id}", value=challenge_id)
            ])
        ]
    @staticmethod
    def summary_card(title: str, summary_text: str) -> List[Dict]:
        """Özet içeriğini gösteren layout."""
        return [
            BlockBuilder.header(f"📚 {title}"),
            BlockBuilder.section(summary_text),
            BlockBuilder.divider(),
            BlockBuilder.context(["🪄 *Groq AI tarafından asistanınız Cemil için hazırlanmıştır.*"])
        ]
