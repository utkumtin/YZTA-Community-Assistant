"""
Servis lifecycle bildirimleri — shutdown ve startup.

Tüm fonksiyonlar sync'tir (slack_helper sync SDK kullanır).
Hata olsa bile exception fırlatmaz — sadece loglar.

Kanal türüne göre token seçimi:
  - Ortak/admin kanal  → bot_client  (mesajlar bot kimliğiyle gider)
  - Özel challenge/eval kanalları → user_client  (bot her kanalda üye olmayabilir)
"""
from __future__ import annotations

from packages.settings import get_settings
from .slack_helpers import slack_helper
from ..logger import _logger


# ---------------------------------------------------------------------------
# Shutdown bildirimleri
# ---------------------------------------------------------------------------

def notify_shutdown(
    registry,
    category_queues: dict,
    pending_lock,
    pending_challenges: dict,
) -> None:
    """
    Servis kapanmadan önce tüm aktif kullanıcılara bildirim gönderir.
    registry ve queue'lar henüz temizlenmeden önce çağrılmalı.
    """
    s = get_settings()
    challenge_channel = s.slack_challenge_channel
    admin_channel = s.slack_admin_channel

    # 1. Aktif challenge kanalları — katılımcıları etiketle (özel kanal → user_client)
    for channel_id, record in registry.challenge_channels().items():
        if not record.members:
            continue
        mentions = " ".join(f"<@{uid}>" for uid in record.members)
        _safe_private(
            channel_id,
            f"{mentions}\n\n"
            "*Servis geçici olarak bakım moduna alınıyor.*\n\n"
            "Challenge'ınız korunuyor — kaldığı yerden devam edebilirsiniz.\n"
            "Komutlar kısa süre içinde yeniden aktif olacak.",
        )

    # 2. Evaluation kanalları — katılımcı + jüri etiketle (özel kanal → user_client)
    for channel_id, record in registry.evaluation_channels().items():
        all_members = list({*record.members, *record.jury})
        if not all_members:
            continue
        mentions = " ".join(f"<@{uid}>" for uid in all_members)
        _safe_private(
            channel_id,
            f"{mentions}\n\n"
            "*Servis geçici olarak bakım moduna alınıyor.*\n\n"
            "Değerlendirme süreciniz korunuyor — kaldığı yerden devam edebilirsiniz.",
        )

    # 3. Kuyrukta bekleyenler → ortak kanalda etiketle (genel kanal → bot_client)
    queued: list[tuple[str, str]] = []
    for cat, q in category_queues.items():
        cat_label = cat.value.replace("_", " ").title()
        for uid in q.get_order():
            queued.append((uid, cat_label))

    if queued:
        mentions = " ".join(f"<@{uid}>" for uid, _ in queued)
        lines = "\n".join(f"  • <@{uid}> — {cat}" for uid, cat in queued)
        _safe_public(
            challenge_channel,
            f"{mentions}\n\n"
            "Servis yeniden başlatılıyor. *Tüm kuyruklar sıfırlandı.*\n"
            "Geri döndüğünde `/challenge join` ile yeniden katılabilirsin.\n\n"
            f"{lines}",
        )

    # 4. In-memory pending challenge kullanıcıları → ortak kanalda etiketle (bot_client)
    with pending_lock:
        for pid, p in list(pending_challenges.items()):
            if not p.get("participants"):
                continue
            mentions = " ".join(f"<@{uid}>" for uid in p["participants"])
            cat_label = p["category"].value.replace("_", " ").title()
            _safe_public(
                challenge_channel,
                f"{mentions}\n\n"
                f"*{cat_label}* kategorisindeki bekleme listeniz iptal edildi.\n"
                "Geri döndüğünde `/challenge join` ile yeniden katılabilirsin.",
            )

    # 5. Admin kanalı — özet (bot_client)
    ch_count = len(registry.challenge_channels())
    ev_count = len(registry.evaluation_channels())
    q_count = sum(q.count() for q in category_queues.values())
    _safe_public(
        admin_channel,
        f"🔴 *Challenge Service — Bakım Modu*\n\n"
        f"• Aktif challenge kanalı: *{ch_count}*\n"
        f"• Aktif değerlendirme kanalı: *{ev_count}*\n"
        f"• Kuyrukta bekleyen: *{q_count}* kişi",
    )

    _logger.info("[NOTIFY] shutdown notifications sent")


# ---------------------------------------------------------------------------
# Startup: silinecek challenge'lar için bildirim
# ---------------------------------------------------------------------------

def notify_cancelled_challenges(
    cancel_data: list[tuple[str | None, list[str]]],
) -> None:
    """
    RESUME/FRESH temizliğinde silinecek challenge katılımcılarını bildirir.
    cancel_data: [(challenge_channel_id | None, [slack_id, ...])]
    Kanalı varsa o kanala (özel → user_client), yoksa ortak kanala (bot_client) gönderir.
    """
    if not cancel_data:
        return

    s = get_settings()
    fallback_channel = s.slack_challenge_channel

    for channel_id, member_slack_ids in cancel_data:
        if not member_slack_ids:
            continue
        mentions = " ".join(f"<@{uid}>" for uid in member_slack_ids)
        text = (
            f"{mentions}\n\n"
            "Servis yeniden başlatıldığından bu challenge iptal edildi.\n"
            "Yeniden katılmak için `/challenge join` komutunu kullanabilirsin."
        )
        if channel_id:
            _safe_private(channel_id, text)
        else:
            _safe_public(fallback_channel, text)

    _logger.info("[NOTIFY] cancelled challenge notifications sent (%d)", len(cancel_data))


# ---------------------------------------------------------------------------
# Startup bildirimleri
# ---------------------------------------------------------------------------

def notify_startup(registry) -> None:
    """
    Servis başladıktan ve registry dolduktan sonra çağrılır.
    Aktif kanalları ve ortak kanalı bildirir.
    """
    s = get_settings()
    challenge_channel = s.slack_challenge_channel
    admin_channel = s.slack_admin_channel

    # 1. Aktif challenge kanalları (özel kanal → user_client)
    for channel_id, record in registry.challenge_channels().items():
        if not record.members:
            continue
        mentions = " ".join(f"<@{uid}>" for uid in record.members)
        _safe_private(
            channel_id,
            f"{mentions}\n\n"
            "*Servis yeniden devreye girdi.*\n\n"
            "Challenge'ınız korunuyor — kaldığı yerden devam edebilirsiniz.",
        )

    # 2. Evaluation kanalları (özel kanal → user_client)
    for channel_id, record in registry.evaluation_channels().items():
        all_members = list({*record.members, *record.jury})
        if not all_members:
            continue
        mentions = " ".join(f"<@{uid}>" for uid in all_members)
        _safe_private(
            channel_id,
            f"{mentions}\n\n"
            "*Servis yeniden devreye girdi.*\n\n"
            "Değerlendirme süreci kaldığı yerden devam ediyor.",
        )

    # 3. Ortak challenge kanalı — genel duyuru (bot_client)
    ch_count = len(registry.challenge_channels())
    ev_count = len(registry.evaluation_channels())

    status_lines = []
    if ch_count:
        status_lines.append(f"• *{ch_count}* aktif challenge devam ediyor")
    if ev_count:
        status_lines.append(f"• *{ev_count}* değerlendirme süreci devam ediyor")
    if not ch_count and not ev_count:
        status_lines.append("• Aktif challenge veya değerlendirme yok — yenisine başlamak için hazır!")

    status_block = "\n".join(status_lines)

    _safe_public(
        challenge_channel,
        f"✅ *Challenge System aktif!*\n\n"
        f"Bu platform, topluluk üyelerinin birlikte gerçek projeler geliştirerek "
        f"hem teknik becerilerini pekiştirmelerini hem de birbirlerini tanımalarını sağlar.\n\n"
        f"*Nasıl işler?*\n"
        f"Kuyruğa katılırsın → eşleşen ekiple özel bir kanal açılır → belirlenen projeyi birlikte geliştirirsin → "
        f"teslim edersin → jüri değerlendirir → puan ve geri bildirim alırsın.\n\n"
        f"*Kategoriler:*\n"
        f"• 📚 *Learn* — Kavramları keşfetmek ve öğrenmek isteyenler için\n"
        f"• 🛠️ *Practice* — Eldeki becerileri gerçek görevlerle pekiştirmek için\n"
        f"• 🌍 *Real World* — Sektörden alınmış gerçek senaryolar\n"
        f"• 🚀 *No-Code / Low-Code* — Kod yazmadan çözüm üretenler için\n\n"
        f"*Kazanımlar:*\n"
        f"→ Ekip çalışması deneyimi\n"
        f"→ Portfolio'na eklenebilir GitHub projeleri\n"
        f"→ Jüri geri bildirimiyle nesnel değerlendirme\n"
        f"→ Topluluk içinde tanınma ve networking\n\n"
        f"*Durum:*\n"
        f"{status_block}\n\n"
        f"*Komutlar:*\n"
        f"• `/challenge join` — Kuyruğa katıl\n"
        f"• `/challenge start <n>` — n kişilik challenge başlat\n"
        f"• `/challenge leave` — Kuyruktan çık\n"
        f"• `/challenge list` — Kuyruk durumunu gör\n"
        f"• `/challenge info` — Challenge geçmişin\n"
        f"• `/challenge help` — Tüm komutlar\n\n"
        f"• `/jury join` — Jüri kuyruğuna katıl\n"
        f"• `/jury leave` — Jüri kuyruğundan çık",
    )

    # 4. Admin kanalı (bot_client)
    _safe_public(
        admin_channel,
        f"🟢 *Challenge Service — Aktif*\n\n"
        f"• Aktif challenge kanalı: *{ch_count}*\n"
        f"• Aktif değerlendirme kanalı: *{ev_count}*",
    )

    _logger.info("[NOTIFY] startup notifications sent")


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _safe_public(channel_id: str, text: str) -> None:
    """Ortak/admin kanallar için bot token'ıyla gönderir, hata fırlatmaz."""
    try:
        slack_helper.post_public_message(channel_id, text)
    except Exception as exc:
        _logger.warning("[NOTIFY] public post failed (channel=%s): %s", channel_id, exc)


def _safe_private(channel_id: str, text: str) -> None:
    """Özel kanallar için user token'ıyla gönderir, hata fırlatmaz."""
    try:
        slack_helper.post_message(channel_id, text)
    except Exception as exc:
        _logger.warning("[NOTIFY] private post failed (channel=%s): %s", channel_id, exc)
