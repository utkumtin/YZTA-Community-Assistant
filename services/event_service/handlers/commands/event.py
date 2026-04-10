"""
Event Service — /event komutu router ve basit alt komutlar.
"""
from __future__ import annotations

from datetime import date

from slack_bolt import Ack, App

from packages.database.manager import db
from packages.database.models.event import Event, EventInterest, EventStatus
from packages.database.repository.event import EventRepository, EventInterestRepository
from packages.settings import get_settings
from packages.slack.blocks.builder import MessageBuilder, BlockBuilder
from packages.slack.client import slack_client
from ...logger import _logger
from ...utils.calendar import build_google_calendar_url
from ...utils.notifications import _location_display

app: App = slack_client.app
settings = get_settings()


def _run_async(coro, timeout=30.0):
    """Bolt handler thread'inden async kodu calistirmak icin."""
    from services.event_service.core.event_loop import run_async
    return run_async(coro, timeout=timeout)


# ---------------------------------------------------------------------------
# /event command router
# ---------------------------------------------------------------------------

@app.command("/event")
def handle_event_command(ack: Ack, body: dict, client, command):
    ack()

    user_id = body.get("user_id")
    channel_id = body.get("channel_id", "")
    args = body.get("text", "").strip().split()
    cmd = args[0].lower() if args else "help"

    # Kanal kontrolu — sadece event_channel'da calisir
    if channel_id != settings.event_channel:
        client.chat_postMessage(
            channel=user_id,
            text=f"Bu komut sadece <#{settings.event_channel}> kanalinda kullanilabilir."
        )
        return

    if cmd == "create":
        _open_create_modal(client, body.get("trigger_id"), user_id)
    elif cmd == "list":
        _handle_list(client, user_id, channel_id)
    elif cmd == "my_list":
        _handle_my_list(client, user_id, channel_id)
    elif cmd == "history":
        _handle_history(client, user_id, channel_id)
    elif cmd == "add_me":
        event_id = args[1] if len(args) > 1 else None
        _handle_add_me(client, user_id, channel_id, event_id)
    elif cmd == "update":
        event_id = args[1] if len(args) > 1 else None
        _handle_update(client, body, user_id, channel_id, event_id)
    elif cmd == "cancel":
        event_id = args[1] if len(args) > 1 else None
        _handle_cancel(client, user_id, channel_id, event_id)
    elif cmd == "help":
        _handle_help(client, user_id, channel_id)
    else:
        client.chat_postEphemeral(
            channel=channel_id, user=user_id,
            text="Bilinmeyen komut. `/event help` ile kullanilabilir komutlari gorun."
        )


# ---------------------------------------------------------------------------
# /event create — Modal acma
# ---------------------------------------------------------------------------

DURATION_OPTIONS = [
    {"label": "30 dakika", "value": "30"},
    {"label": "1 saat", "value": "60"},
    {"label": "1.5 saat", "value": "90"},
    {"label": "2 saat", "value": "120"},
    {"label": "3 saat", "value": "180"},
]

LOCATION_OPTIONS = [
    {"label": "Slack Kanali", "value": "slack_channel"},
    {"label": "Zoom", "value": "zoom"},
    {"label": "YouTube", "value": "youtube"},
    {"label": "Google Meet", "value": "google_meet"},
    {"label": "Discord", "value": "discord"},
    {"label": "Diger", "value": "other"},
]


def _build_event_form_blocks(initial: dict | None = None) -> list[dict]:
    """Event form bloklarini olusturur. initial verilirse update icin dolu gelir."""
    iv = initial or {}
    blocks = []

    # 1. Etkinlik Adi
    name_elem = {"type": "plain_text_input", "action_id": "val",
                 "placeholder": {"type": "plain_text", "text": "Orn: Python ile Web Scraping Workshop"}}
    if iv.get("name"):
        name_elem["initial_value"] = iv["name"]
    blocks.append({"type": "input", "block_id": "event_name", "element": name_elem,
                    "label": {"type": "plain_text", "text": "Etkinlik Adi"}})

    # 2. Konu
    topic_elem = {"type": "plain_text_input", "action_id": "val",
                  "placeholder": {"type": "plain_text", "text": "Orn: Web Scraping, Veri Analizi"}}
    if iv.get("topic"):
        topic_elem["initial_value"] = iv["topic"]
    blocks.append({"type": "input", "block_id": "event_topic", "element": topic_elem,
                    "label": {"type": "plain_text", "text": "Konu"}})

    # 3. Aciklama & Amac
    desc_elem = {"type": "plain_text_input", "action_id": "val", "multiline": True,
                 "placeholder": {"type": "plain_text", "text": "Etkinligin amacini ve katilimcilara neler katacagini aciklayin..."}}
    if iv.get("description"):
        desc_elem["initial_value"] = iv["description"]
    blocks.append({"type": "input", "block_id": "event_description", "element": desc_elem,
                    "label": {"type": "plain_text", "text": "Aciklama & Amac"}})

    # 4. Tarih
    date_elem = {"type": "datepicker", "action_id": "val",
                 "placeholder": {"type": "plain_text", "text": "Tarih secin..."}}
    if iv.get("date"):
        date_elem["initial_date"] = iv["date"]
    blocks.append({"type": "input", "block_id": "event_date", "element": date_elem,
                    "label": {"type": "plain_text", "text": "Tarih"}})

    # 5. Saat
    time_elem = {"type": "timepicker", "action_id": "val",
                 "placeholder": {"type": "plain_text", "text": "Saat secin..."}}
    if iv.get("time"):
        time_elem["initial_time"] = iv["time"]
    blocks.append({"type": "input", "block_id": "event_time", "element": time_elem,
                    "label": {"type": "plain_text", "text": "Saat"}})

    # 6. Sure
    dur_opts = [{"text": {"type": "plain_text", "text": o["label"]}, "value": o["value"]} for o in DURATION_OPTIONS]
    dur_elem = {"type": "static_select", "action_id": "val",
                "placeholder": {"type": "plain_text", "text": "Sure secin..."}, "options": dur_opts}
    if iv.get("duration"):
        for o in dur_opts:
            if o["value"] == iv["duration"]:
                dur_elem["initial_option"] = o
                break
    blocks.append({"type": "input", "block_id": "event_duration", "element": dur_elem,
                    "label": {"type": "plain_text", "text": "Tahmini Sure"}})

    # 7. Etkinlik Lokasyonu
    loc_opts = [{"text": {"type": "plain_text", "text": o["label"]}, "value": o["value"]} for o in LOCATION_OPTIONS]
    loc_elem = {"type": "static_select", "action_id": "val",
                "placeholder": {"type": "plain_text", "text": "Lokasyon secin..."}, "options": loc_opts}
    if iv.get("location_type"):
        for o in loc_opts:
            if o["value"] == iv["location_type"]:
                loc_elem["initial_option"] = o
                break
    blocks.append({"type": "input", "block_id": "event_location", "element": loc_elem,
                    "label": {"type": "plain_text", "text": "Etkinlik Lokasyonu"}})

    # 8. Slack Kanali (opsiyonel — backend'de validate edilir)
    ch_elem = {"type": "channels_select", "action_id": "val",
               "placeholder": {"type": "plain_text", "text": "Kanal secin..."}}
    if iv.get("channel_id"):
        ch_elem["initial_channel"] = iv["channel_id"]
    blocks.append({"type": "input", "block_id": "event_channel", "optional": True, "element": ch_elem,
                    "label": {"type": "plain_text", "text": "Slack Kanali (lokasyon Slack ise zorunlu)"}})

    # 9. Etkinlik Linki (opsiyonel — backend'de validate edilir)
    link_elem = {"type": "url_text_input", "action_id": "val",
                 "placeholder": {"type": "plain_text", "text": "Orn: https://zoom.us/j/123 veya Drive linki"}}
    if iv.get("link"):
        link_elem["initial_value"] = iv["link"]
    blocks.append({"type": "input", "block_id": "event_link", "optional": True, "element": link_elem,
                    "label": {"type": "plain_text", "text": "Etkinlik Linki (harici platform ise zorunlu)"}})

    # 10. YZTA'dan Beklenen (opsiyonel)
    yzta_elem = {"type": "plain_text_input", "action_id": "val", "multiline": True,
                 "placeholder": {"type": "plain_text", "text": "Organizasyondan bir destek veya kaynak talebiniz varsa belirtin..."}}
    if iv.get("yzta_request"):
        yzta_elem["initial_value"] = iv["yzta_request"]
    blocks.append({"type": "input", "block_id": "event_yzta", "optional": True, "element": yzta_elem,
                    "label": {"type": "plain_text", "text": "YZTA'dan Beklenen (opsiyonel)"}})

    return blocks


def _open_create_modal(client, trigger_id: str, user_id: str) -> None:
    blocks = _build_event_form_blocks()
    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "event_create_modal",
            "title": {"type": "plain_text", "text": "Yeni Etkinlik Olustur"},
            "submit": {"type": "plain_text", "text": "Gonder"},
            "close": {"type": "plain_text", "text": "Iptal"},
            "blocks": blocks,
        },
    )


# ---------------------------------------------------------------------------
# /event list
# ---------------------------------------------------------------------------

def _handle_list(client, user_id: str, channel_id: str) -> None:
    async def _fetch():
        async with db.session(read_only=True) as session:
            repo = EventRepository(session)
            events = await repo.list_current_month()
            interest_repo = EventInterestRepository(session)
            result = []
            for evt in events:
                count = await interest_repo.count_by_event(evt.id)
                result.append((evt, count))
            return result

    try:
        items = _run_async(_fetch())
    except Exception as e:
        _logger.error("[CMD] list failed: %s", e)
        client.chat_postEphemeral(channel=channel_id, user=user_id, text="Etkinlikler yuklenemedi.")
        return

    builder = MessageBuilder()
    builder.add_header("Bu Ayin Etkinlikleri")

    if not items:
        builder.add_text("_Bu ay henuz onaylanmis etkinlik yok._")
    else:
        builder.add_divider()
        for evt, count in items:
            loc = _location_display(evt)
            line = (
                f"• *{evt.id[:12]}* | *{evt.name}*\n"
                f"  <@{evt.creator_slack_id}> · {evt.date.strftime('%d %B')} {evt.time.strftime('%H:%M')} · {loc}"
            )
            if evt.link:
                line += f"\n  <{evt.link}|Link>"
            line += f" · {count} ilgili"
            builder.add_text(line)
        builder.add_divider()
        builder.add_context([f"_Toplam: {len(items)} etkinlik_"])

    client.chat_postEphemeral(channel=channel_id, user=user_id, text="Bu Ayin Etkinlikleri", blocks=builder.build())


# ---------------------------------------------------------------------------
# /event my_list
# ---------------------------------------------------------------------------

def _handle_my_list(client, user_id: str, channel_id: str) -> None:
    STATUS_LABELS = {
        "pending": "Onay Bekliyor",
        "approved": "Onaylandi",
        "rejected": "Reddedildi",
        "cancelled": "Iptal Edildi",
        "completed": "Gerceklesti",
    }

    async def _fetch():
        async with db.session(read_only=True) as session:
            repo = EventRepository(session)
            events = await repo.list_by_creator(user_id)
            interest_repo = EventInterestRepository(session)
            result = []
            for evt in events:
                count = await interest_repo.count_by_event(evt.id)
                result.append((evt, count))
            return result

    try:
        items = _run_async(_fetch())
    except Exception as e:
        _logger.error("[CMD] my_list failed: %s", e)
        client.chat_postEphemeral(channel=channel_id, user=user_id, text="Etkinlikler yuklenemedi.")
        return

    builder = MessageBuilder()
    builder.add_header("Etkinliklerim")

    if not items:
        builder.add_text("_Henuz etkinlik olusturmadiniz._")
    else:
        builder.add_divider()
        for evt, count in items:
            loc = _location_display(evt)
            status_label = STATUS_LABELS.get(evt.status.value, evt.status.value)
            line = (
                f"• *{evt.id[:12]}* | *{evt.name}*\n"
                f"  {evt.date.strftime('%d %B')} {evt.time.strftime('%H:%M')} · {loc} · {status_label}"
            )
            if count > 0:
                line += f" · {count} ilgili"
            builder.add_text(line)
        builder.add_divider()
        builder.add_context([f"_Toplam: {len(items)} etkinlik_"])

    client.chat_postEphemeral(channel=channel_id, user=user_id, text="Etkinliklerim", blocks=builder.build())


# ---------------------------------------------------------------------------
# /event history
# ---------------------------------------------------------------------------

def _handle_history(client, user_id: str, channel_id: str) -> None:
    STATUS_LABELS = {
        "completed": "Gerceklesti",
        "cancelled": "Iptal Edildi",
    }

    async def _fetch():
        async with db.session(read_only=True) as session:
            repo = EventRepository(session)
            events = await repo.list_history()
            interest_repo = EventInterestRepository(session)
            result = []
            for evt in events:
                count = await interest_repo.count_by_event(evt.id)
                result.append((evt, count))
            return result

    try:
        items = _run_async(_fetch())
    except Exception as e:
        _logger.error("[CMD] history failed: %s", e)
        client.chat_postEphemeral(channel=channel_id, user=user_id, text="Gecmis yuklenemedi.")
        return

    builder = MessageBuilder()
    builder.add_header("Gecmis Etkinlikler")

    if not items:
        builder.add_text("_Henuz gecmis etkinlik yok._")
    else:
        builder.add_divider()
        for evt, count in items:
            loc = _location_display(evt)
            status_label = STATUS_LABELS.get(evt.status.value, evt.status.value)
            line = (
                f"• *{evt.id[:12]}* | *{evt.name}*\n"
                f"  <@{evt.creator_slack_id}> · {evt.date.strftime('%d %B')} {evt.time.strftime('%H:%M')} · {loc}\n"
                f"  {status_label}"
            )
            if count > 0:
                line += f" · {count} ilgili"
            builder.add_text(line)
        builder.add_divider()
        builder.add_context([f"_Toplam: {len(items)} etkinlik_"])

    client.chat_postEphemeral(channel=channel_id, user=user_id, text="Gecmis Etkinlikler", blocks=builder.build())


# ---------------------------------------------------------------------------
# /event add_me <id>
# ---------------------------------------------------------------------------

def _handle_add_me(client, user_id: str, channel_id: str, event_id: str | None) -> None:
    if not event_id:
        client.chat_postEphemeral(channel=channel_id, user=user_id,
                                   text="Kullanim: `/event add_me <id>`")
        return

    async def _add():
        async with db.session() as session:
            repo = EventRepository(session)
            evt = await repo.get(event_id)
            if not evt or evt.status != EventStatus.APPROVED:
                return None, "not_found"
            interest_repo = EventInterestRepository(session)
            existing = await interest_repo.find_by_event_and_user(event_id, user_id)
            if existing:
                return evt, "already"
            await interest_repo.create(EventInterest(event_id=event_id, slack_id=user_id))
            return evt, "ok"

    try:
        evt, status = _run_async(_add())
    except Exception as e:
        _logger.error("[CMD] add_me failed: %s", e)
        client.chat_postEphemeral(channel=channel_id, user=user_id, text="Islem basarisiz, tekrar deneyin.")
        return

    if status == "not_found":
        client.chat_postEphemeral(channel=channel_id, user=user_id,
                                   text="Etkinlik bulunamadi veya ilgi gosterilemez durumda.\n"
                                        "Aktif etkinlikleri gormek icin `/event list` komutunu kullanin.")
        return

    if status == "already":
        client.chat_postEphemeral(channel=channel_id, user=user_id,
                                   text=f"Bu etkinlige zaten ilgi gosterdiniz.\n*{evt.name}*\n_{evt.id}_")
        return

    # Basarili — ephemeral + DM
    cal_url = build_google_calendar_url(
        title=evt.name, event_date=evt.date, event_time=evt.time,
        duration_minutes=evt.duration_minutes, description=evt.description,
        location=evt.link or "",
    )
    loc = _location_display(evt)
    text = (
        f"Ilgin kaydedildi!\n\n"
        f"*{evt.name}*\n"
        f"{evt.date.strftime('%d %B %Y')} · {evt.time.strftime('%H:%M')} · {loc}\n\n"
        f"Etkinlik gunu hatirlatma e-postasi alacaksin.\n_{evt.id}_"
    )
    client.chat_postEphemeral(channel=channel_id, user=user_id, text=text)

    # DM
    from ...utils.notifications import send_dm
    dm_builder = MessageBuilder()
    dm_builder.add_text(text)
    dm_builder.add_button("Google Takvime Ekle", "event_calendar_btn", value=evt.id, url=cal_url)
    send_dm(user_id, f"Ilgin kaydedildi: {evt.name}", dm_builder.build())


# ---------------------------------------------------------------------------
# /event cancel <id>
# ---------------------------------------------------------------------------

def _handle_cancel(client, user_id: str, channel_id: str, event_id: str | None) -> None:
    if not event_id:
        client.chat_postEphemeral(channel=channel_id, user=user_id,
                                   text="Kullanim: `/event cancel <id>`")
        return

    is_admin = user_id in settings.slack_admins

    async def _cancel():
        async with db.session() as session:
            repo = EventRepository(session)
            evt = await repo.get(event_id)
            if not evt:
                return None, "not_found"
            if evt.status != EventStatus.APPROVED:
                return evt, "wrong_status"
            if evt.creator_slack_id != user_id and not is_admin:
                return evt, "no_permission"
            evt.status = EventStatus.CANCELLED
            await session.flush()
            return evt, "ok"

    try:
        evt, status = _run_async(_cancel())
    except Exception as e:
        _logger.error("[CMD] cancel failed: %s", e)
        client.chat_postEphemeral(channel=channel_id, user=user_id, text="Iptal islemi basarisiz.")
        return

    if status == "not_found":
        client.chat_postEphemeral(channel=channel_id, user=user_id, text="Etkinlik bulunamadi.")
        return
    if status == "wrong_status":
        client.chat_postEphemeral(channel=channel_id, user=user_id,
                                   text="Sadece onaylanmis etkinlikler iptal edilebilir.")
        return
    if status == "no_permission":
        client.chat_postEphemeral(channel=channel_id, user=user_id,
                                   text="Bu etkinligi iptal etme yetkiniz yok.")
        return

    # Basarili
    client.chat_postEphemeral(
        channel=channel_id, user=user_id,
        text=f"Etkinlik basariyla iptal edildi.\n*{evt.name}*\n_{evt.id}_"
    )

    # Duyuru kanallarina iptal bildirisi
    from ...utils.notifications import post_cancellation
    post_cancellation(evt, user_id)

    # Admin iptal ettiyse sahibe DM
    if is_admin and evt.creator_slack_id != user_id:
        from ...utils.notifications import send_dm
        send_dm(
            evt.creator_slack_id,
            f"Etkinliginiz admin tarafindan iptal edildi.\n*{evt.name}*\n_{evt.id}_"
        )

    # Ilgi gosterenlere iptal e-postasi
    async def _notify_interested():
        async with db.session(read_only=True) as session:
            interest_repo = EventInterestRepository(session)
            interests = await interest_repo.list_by_event(event_id)
            return [i.slack_id for i in interests]

    try:
        interested_ids = _run_async(_notify_interested())
        from ...utils.email import send_cancellation_email
        for sid in interested_ids:
            send_cancellation_email(sid, evt)
    except Exception as e:
        _logger.warning("[CMD] Cancel email notifications failed: %s", e)

    _logger.info("[CMD] Event cancelled: %s by %s", event_id, user_id)


# ---------------------------------------------------------------------------
# /event update <id>
# ---------------------------------------------------------------------------

def _handle_update(client, body: dict, user_id: str, channel_id: str, event_id: str | None) -> None:
    if not event_id:
        client.chat_postEphemeral(channel=channel_id, user=user_id,
                                   text="Kullanim: `/event update <id>`")
        return

    is_admin = user_id in settings.slack_admins

    async def _fetch():
        async with db.session(read_only=True) as session:
            repo = EventRepository(session)
            return await repo.get(event_id)

    try:
        evt = _run_async(_fetch())
    except Exception as e:
        _logger.error("[CMD] update fetch failed: %s", e)
        client.chat_postEphemeral(channel=channel_id, user=user_id, text="Etkinlik yuklenemedi.")
        return

    if not evt:
        client.chat_postEphemeral(channel=channel_id, user=user_id, text="Etkinlik bulunamadi.")
        return
    if evt.status != EventStatus.APPROVED:
        client.chat_postEphemeral(channel=channel_id, user=user_id,
                                   text="Sadece onaylanmis etkinlikler guncellenebilir.")
        return
    if evt.creator_slack_id != user_id and not is_admin:
        client.chat_postEphemeral(channel=channel_id, user=user_id,
                                   text="Bu etkinligi guncelleme yetkiniz yok.")
        return

    # Mevcut degerlerle modal ac
    initial = {
        "name": evt.name,
        "topic": evt.topic,
        "description": evt.description,
        "date": evt.date.isoformat(),
        "time": evt.time.strftime("%H:%M"),
        "duration": str(evt.duration_minutes),
        "location_type": evt.location_type,
        "channel_id": evt.channel_id,
        "link": evt.link,
        "yzta_request": evt.yzta_request,
    }
    blocks = _build_event_form_blocks(initial)

    import json
    client.views_open(
        trigger_id=body.get("trigger_id"),
        view={
            "type": "modal",
            "callback_id": "event_update_modal",
            "private_metadata": json.dumps({"event_id": event_id}),
            "title": {"type": "plain_text", "text": "Etkinlik Guncelle"},
            "submit": {"type": "plain_text", "text": "Guncelle"},
            "close": {"type": "plain_text", "text": "Iptal"},
            "blocks": blocks,
        },
    )


# ---------------------------------------------------------------------------
# /event help
# ---------------------------------------------------------------------------

def _handle_help(client, user_id: str, channel_id: str) -> None:
    builder = MessageBuilder()
    builder.add_header("Event Komutlari")
    builder.add_text(
        "*`/event create`*\n"
        "Yeni etkinlik talebi olustur. Form acilir, admin onayindan sonra duyuru yapilir.\n\n"
        "*`/event list`*\n"
        "Bu ayin yaklasan etkinliklerini listele.\n\n"
        "*`/event my_list`*\n"
        "Kendi olusturdugum etkinlikleri listele.\n\n"
        "*`/event history`*\n"
        "Gecmis etkinlikleri goruntule.\n\n"
        "*`/event add_me <id>`*\n"
        "Etkinlige ilgi goster. Her etkinlige 1 kez ilgi gosterilebilir. Butona tiklama ile ayni isi gorur.\n\n"
        "*`/event update <id>`*\n"
        "Etkinlik bilgilerini guncelle (sahip + admin).\n\n"
        "*`/event cancel <id>`*\n"
        "Etkinligi iptal et (sahip + admin).\n\n"
        "*`/event help`*\n"
        "Bu yardim mesajini goster."
    )
    builder.add_divider()
    builder.add_context(["_Etkinlik ID'sini `/event list` ile ogrenebilirsin_"])

    client.chat_postEphemeral(channel=channel_id, user=user_id, text="Event Komutlari", blocks=builder.build())
