"""
Event Service — Background scheduler.
Periyodik gorevler:
  1. Timeout: PENDING + 72 saat → REJECTED
  2. Gun basi hatirlatma: O gunun etkinliklerini duyur
  3. 10dk oncesi hatirlatma
  4. COMPLETED gecisi: Tarihi gecmis APPROVED → COMPLETED
"""
from __future__ import annotations

import asyncio
from datetime import datetime, date, timedelta, timezone

from packages.database.manager import db
from packages.database.models.event import Event, EventStatus
from packages.database.repository.event import EventRepository, EventInterestRepository
from packages.settings import get_settings
from packages.slack.client import slack_client
from packages.slack.blocks.builder import MessageBuilder
from ..logger import _logger
from ..utils.notifications import (
    get_announcement_channels, send_dm, _location_display, _calendar_url,
)
from ..utils.email import send_reminder_email_async, send_user_status_email_async


class EventScheduler:
    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None
        self._morning_reminder_last_date: date | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        _logger.info("[SCHED] Event scheduler started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        _logger.info("[SCHED] Event scheduler stopped")

    async def _run_loop(self) -> None:
        """Her 60 saniyede bir tum gorevleri calistirir."""
        while self._running:
            try:
                await self._check_pending_timeout()
                await self._check_completed_transition()
                await self._check_morning_reminder()
                await self._check_10min_reminder()
            except Exception as e:
                _logger.error("[SCHED] Error in loop: %s", e, exc_info=True)
            await asyncio.sleep(60)

    # ---- 1. Timeout: PENDING + 72 saat → REJECTED ----

    async def _check_pending_timeout(self) -> None:
        s = get_settings()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=s.event_approval_timeout_hours)

        async with db.session() as session:
            repo = EventRepository(session)
            expired = await repo.list_pending_expired(cutoff)
            for evt in expired:
                evt.status = EventStatus.REJECTED
                _logger.info("[SCHED] Timeout: %s", evt.id)
                send_dm(
                    evt.creator_slack_id,
                    f"Etkinlik Talebiniz Zaman Asimina Ugradi\n\n"
                    f"*{evt.name}*\n"
                    f"{evt.date.strftime('%d %B %Y')} · {evt.time.strftime('%H:%M')}\n\n"
                    f"Talebiniz {s.event_approval_timeout_hours // 24} gun icinde yanit alamadigi icin "
                    f"otomatik olarak reddedildi.\n\n"
                    f"Yeni bir etkinlik talebi icin `/event create` komutunu kullanabilirsiniz.\n_{evt.id}_"
                )
                await send_user_status_email_async(evt.creator_slack_id, evt, "timeout")

    # ---- 2. COMPLETED gecisi ----

    async def _check_completed_transition(self) -> None:
        utc_today = datetime.now(timezone.utc).date()
        async with db.session() as session:
            repo = EventRepository(session)
            past = await repo.list_approved_past(utc_today)
            for evt in past:
                evt.status = EventStatus.COMPLETED
                _logger.info("[SCHED] Completed: %s", evt.id)

    # ---- 3. Gun basi hatirlatma ----

    async def _check_morning_reminder(self) -> None:
        """Her gun 08:00 UTC'de o gunun etkinliklerini duyurur. Gun basina 1 kez."""
        now = datetime.now(timezone.utc)
        utc_today = now.date()

        # Saat 08:00 UTC'den once calisma
        if now.hour < 8:
            return

        # Bugun zaten gonderildiyse atla
        if self._morning_reminder_last_date == utc_today:
            return

        s = get_settings()
        if not s.event_reminder_enabled:
            return

        async with db.session(read_only=True) as session:
            repo = EventRepository(session)
            events = await repo.list_approved_by_date(utc_today)
            if not events:
                self._morning_reminder_last_date = utc_today
                return

            interest_repo = EventInterestRepository(session)

            builder = MessageBuilder()
            builder.add_header(f"Bugunun Etkinlikleri — {utc_today.strftime('%d %B %Y')}")
            builder.add_divider()

            # E-posta gonderilecek ilgili kullanicilari topla
            interested_users: list[tuple[str, Event]] = []

            for i, evt in enumerate(events, 1):
                loc = _location_display(evt)
                count = await interest_repo.count_by_event(evt.id)
                cal_url = _calendar_url(evt)

                builder.add_text(
                    f"*{i}. {evt.name}*\n"
                    f"{evt.time.strftime('%H:%M')} · {evt.duration_minutes} dk · {loc}\n"
                    f"<@{evt.creator_slack_id}> · {count} kisi ilgi gosterdi"
                )
                if evt.link:
                    builder.add_button("Katil", f"event_link_{evt.id}", url=evt.link)
                builder.add_button("Google Takvime Ekle", f"event_cal_{evt.id}", url=cal_url)
                builder.add_divider()

                # Ilgi gosterenleri topla
                interests = await interest_repo.list_by_event(evt.id)
                for interest in interests:
                    interested_users.append((interest.slack_id, evt))

            builder.add_context(["_Iyi etkinlikler!_"])
            blocks = builder.build()

            # Tum duyuru kanallarini topla (tekrarsiz)
            all_channels: set[str] = set()
            for evt in events:
                all_channels.update(get_announcement_channels(evt))

            for ch in all_channels:
                try:
                    slack_client.bot_client.chat_postMessage(
                        channel=ch,
                        text=f"Bugunun Etkinlikleri — {utc_today.strftime('%d %B %Y')}",
                        blocks=blocks,
                    )
                except Exception as e:
                    _logger.error("[SCHED] Morning reminder failed channel=%s: %s", ch, e)

        # E-posta gonder (read session kapandiktan sonra)
        for slack_id, evt in interested_users:
            await send_reminder_email_async(slack_id, evt, "day")

        self._morning_reminder_last_date = utc_today
        _logger.info("[SCHED] Morning reminder sent for %d events", len(events))

    # ---- 4. 10dk oncesi hatirlatma ----

    async def _check_10min_reminder(self) -> None:
        s = get_settings()
        if not s.event_reminder_enabled:
            return

        now = datetime.now(timezone.utc)
        utc_today = now.date()

        # Bildirim gonderilecek event'leri ve ilgili kullanicilari topla
        to_notify: list[tuple[Event, list[str]]] = []
        events_to_mark: list[str] = []

        async with db.session(read_only=True) as session:
            repo = EventRepository(session)
            events = await repo.list_approved_by_date(utc_today)

            interest_repo = EventInterestRepository(session)

            for evt in events:
                evt_dt = datetime.combine(utc_today, evt.time, tzinfo=timezone.utc)
                diff = (evt_dt - now).total_seconds()
                if not (540 <= diff <= 660):  # 9-11 dakika arasi
                    continue

                meta = evt.meta or {}
                if meta.get("10min_reminder_sent"):
                    continue

                # Ilgi gosterenleri topla
                interests = await interest_repo.list_by_event(evt.id)
                interested_ids = [i.slack_id for i in interests]
                to_notify.append((evt, interested_ids))
                events_to_mark.append(evt.id)

        # Slack bildirimleri gonder (read session kapalı)
        for evt, interested_ids in to_notify:
            loc = _location_display(evt)
            count = len(interested_ids)
            cal_url = _calendar_url(evt)

            builder = MessageBuilder()
            builder.add_header("10 Dakika Sonra Basliyor!")
            builder.add_text(
                f"*{evt.name}*\n\n"
                f"*Saat:* {evt.time.strftime('%H:%M')}\n"
                f"*Sure:* {evt.duration_minutes} dakika\n"
                f"*Lokasyon:* {loc}\n"
                f"*Duzenleyen:* <@{evt.creator_slack_id}>\n"
                f"*Ilgi:* {count} kisi"
            )
            if evt.link:
                builder.add_button("Katil", "event_10min_link", url=evt.link)
            builder.add_button("Google Takvime Ekle", "event_10min_cal", url=cal_url)

            blocks = builder.build()
            for ch in get_announcement_channels(evt):
                try:
                    slack_client.bot_client.chat_postMessage(
                        channel=ch,
                        text=f"10 Dakika Sonra: {evt.name}",
                        blocks=blocks,
                    )
                except Exception as e:
                    _logger.error("[SCHED] 10min reminder failed channel=%s: %s", ch, e)

            # E-posta gonder
            for slack_id in interested_ids:
                await send_reminder_email_async(slack_id, evt, "10min")

            _logger.info("[SCHED] 10min reminder sent: %s", evt.id)

        # Meta guncelle (ayri write session)
        if events_to_mark:
            async with db.session() as write_session:
                for event_id in events_to_mark:
                    write_evt = await write_session.get(Event, event_id)
                    if write_evt:
                        m = dict(write_evt.meta or {})
                        m["10min_reminder_sent"] = True
                        write_evt.meta = m


event_scheduler = EventScheduler()
