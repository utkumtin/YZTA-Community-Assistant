# Event Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slack toplulugunda etkinlik olusturma, admin onayi, duyuru, hatirlatma ve takip sureci saglayan bagimsiz event servisi.

**Architecture:** `services/event_service/` altinda bagimsiz servis modulu. `packages/` ortak altyapisini kullanir (database, slack, smtp, logger, settings). challenge_service ile sifir bagimlilik. Slack Bolt handler'lari sync, DB islemleri async — `run_async()` koprusu ile baglanir. Background scheduler ile 3 gun timeout, gun basi hatirlatma, 10dk oncesi hatirlatma ve COMPLETED gecisi yapilir.

**Tech Stack:** Python 3.12+, PostgreSQL, SQLAlchemy 2.x async, Alembic, slack_bolt (Socket Mode), pydantic-settings, SMTP + Jinja2

**Spec:** `docs/superpowers/specs/2026-04-08-event-service-design.md`

---

## File Map

### New Files to Create

```
packages/database/models/event.py          — Event, EventInterest, EventStatus, LocationType models
packages/database/repository/event.py      — EventRepository, EventInterestRepository

services/event_service/__init__.py         — Empty
services/event_service/logger.py           — Logging config
services/event_service/handlers/__init__.py        — Handler registration
services/event_service/handlers/commands/__init__.py
services/event_service/handlers/commands/event.py  — /event command router + list/my_list/history/cancel/help
services/event_service/handlers/events/__init__.py
services/event_service/handlers/events/event.py    — Modal submissions, button actions (approve/reject/interest)
services/event_service/core/__init__.py
services/event_service/core/scheduler.py   — Background tasks
services/event_service/utils/__init__.py
services/event_service/utils/notifications.py  — Slack notification helpers
services/event_service/utils/email.py      — Email notification helpers
services/event_service/utils/calendar.py   — Google Calendar URL builder

migrations/versions/0003_add_event_tables.py — DB migration
```

### Existing Files to Modify (additions only)

```
packages/settings.py                       — +3 fields (event_channel, event_reminder_enabled, event_approval_timeout_hours)
packages/database/models/base.py           — +1 import line
```

---

## Task 1: Settings — Event Service Ayarlari

**Files:**
- Modify: `packages/settings.py`

- [ ] **Step 1: Add event settings fields to SystemSettings**

Add these fields after the existing `slack_command_channels` field in `packages/settings.py`:

```python
    # Event Service Ayarlari
    event_channel: str = Field(..., description="Serbest Kursu kanal ID'si (C...)")
    event_reminder_enabled: bool = Field(True, description="Hatirlatma sistemi acik/kapali")
    event_approval_timeout_hours: int = Field(72, ge=1, description="Admin onay suresi (saat)")
```

- [ ] **Step 2: Add to .env.template**

Append to `.env.template`:

```
# ------------------------------------------------------------------------------
# Event Service
# ------------------------------------------------------------------------------
EVENT_CHANNEL=C0123456789
# EVENT_REMINDER_ENABLED=true
# EVENT_APPROVAL_TIMEOUT_HOURS=72
```

- [ ] **Step 3: Commit**

```bash
git add packages/settings.py .env.template
git commit -m "feat(event): add event service settings fields"
```

---

## Task 2: DB Models — Event ve EventInterest

**Files:**
- Create: `packages/database/models/event.py`
- Modify: `packages/database/models/base.py`

- [ ] **Step 1: Create event models**

Create `packages/database/models/event.py`:

```python
from __future__ import annotations

from enum import Enum as PyEnum
from datetime import date, time
from sqlalchemy import Date, ForeignKey, Integer, String, Text, Time, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.database.mixins import Base, IDMixin, TimestampMixin


class EventStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class LocationType(str, PyEnum):
    SLACK_CHANNEL = "slack_channel"
    ZOOM = "zoom"
    YOUTUBE = "youtube"
    GOOGLE_MEET = "google_meet"
    DISCORD = "discord"
    OTHER = "other"


class Event(Base, IDMixin, TimestampMixin):
    __tablename__ = "events"
    __prefix__ = "EVT"

    creator_slack_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    time: Mapped[time] = mapped_column(Time, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    location_type: Mapped[str] = mapped_column(String(32), nullable=False)
    channel_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    yzta_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EventStatus] = mapped_column(SAEnum(EventStatus), nullable=False, index=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    interests: Mapped[list["EventInterest"]] = relationship("EventInterest", back_populates="event")


class EventInterest(Base, IDMixin, TimestampMixin):
    __tablename__ = "event_interest"
    __prefix__ = "EVI"

    event_id: Mapped[str] = mapped_column(String(60), ForeignKey("events.id"), nullable=False, index=True)
    slack_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    event: Mapped["Event"] = relationship("Event", back_populates="interests")
```

- [ ] **Step 2: Register models in base.py**

Add this line to `packages/database/models/base.py` after the existing imports:

```python
from packages.database.models import event as _event  # noqa: F401
```

- [ ] **Step 3: Commit**

```bash
git add packages/database/models/event.py packages/database/models/base.py
git commit -m "feat(event): add Event and EventInterest database models"
```

---

## Task 3: Repository — EventRepository ve EventInterestRepository

**Files:**
- Create: `packages/database/repository/event.py`

- [ ] **Step 1: Create event repositories**

Create `packages/database/repository/event.py`:

```python
from __future__ import annotations

from datetime import date
from sqlalchemy import select, func

from packages.database.models.event import Event, EventInterest, EventStatus
from packages.database.repository.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    model = Event

    async def list_by_status(self, status: EventStatus) -> list[Event]:
        result = await self.session.execute(
            select(Event).where(Event.status == status).order_by(Event.date, Event.time)
        )
        return list(result.scalars().all())

    async def list_approved_by_date(self, target_date: date) -> list[Event]:
        """Belirli bir tarihteki APPROVED etkinlikleri doner."""
        result = await self.session.execute(
            select(Event)
            .where(Event.status == EventStatus.APPROVED, Event.date == target_date)
            .order_by(Event.time)
        )
        return list(result.scalars().all())

    async def list_current_month(self) -> list[Event]:
        """Bu ayin APPROVED etkinliklerini doner."""
        from datetime import date as date_type
        today = date_type.today()
        first_day = today.replace(day=1)
        if today.month == 12:
            last_day = today.replace(year=today.year + 1, month=1, day=1)
        else:
            last_day = today.replace(month=today.month + 1, day=1)

        result = await self.session.execute(
            select(Event)
            .where(
                Event.status == EventStatus.APPROVED,
                Event.date >= first_day,
                Event.date < last_day,
            )
            .order_by(Event.date, Event.time)
        )
        return list(result.scalars().all())

    async def list_by_creator(self, slack_id: str) -> list[Event]:
        """Kullanicinin olusturdugu tum etkinlikler (aktif olanlar)."""
        result = await self.session.execute(
            select(Event)
            .where(
                Event.creator_slack_id == slack_id,
                Event.status.in_([EventStatus.PENDING, EventStatus.APPROVED]),
            )
            .order_by(Event.date.desc(), Event.time.desc())
        )
        return list(result.scalars().all())

    async def list_history(self) -> list[Event]:
        """Gecmis etkinlikler (COMPLETED + CANCELLED)."""
        result = await self.session.execute(
            select(Event)
            .where(Event.status.in_([EventStatus.COMPLETED, EventStatus.CANCELLED]))
            .order_by(Event.date.desc(), Event.time.desc())
        )
        return list(result.scalars().all())

    async def list_pending_expired(self, cutoff_dt) -> list[Event]:
        """Suresi dolmus PENDING etkinlikler."""
        result = await self.session.execute(
            select(Event)
            .where(Event.status == EventStatus.PENDING, Event.created_at < cutoff_dt)
        )
        return list(result.scalars().all())

    async def list_approved_past(self, now_date: date) -> list[Event]:
        """Tarihi gecmis APPROVED etkinlikler (COMPLETED'a cekilecek)."""
        result = await self.session.execute(
            select(Event)
            .where(Event.status == EventStatus.APPROVED, Event.date < now_date)
        )
        return list(result.scalars().all())


class EventInterestRepository(BaseRepository[EventInterest]):
    model = EventInterest

    async def find_by_event_and_user(self, event_id: str, slack_id: str) -> EventInterest | None:
        result = await self.session.execute(
            select(EventInterest)
            .where(EventInterest.event_id == event_id, EventInterest.slack_id == slack_id)
        )
        return result.scalar_one_or_none()

    async def count_by_event(self, event_id: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(EventInterest).where(EventInterest.event_id == event_id)
        )
        return result.scalar_one()

    async def list_by_event(self, event_id: str) -> list[EventInterest]:
        result = await self.session.execute(
            select(EventInterest).where(EventInterest.event_id == event_id)
        )
        return list(result.scalars().all())
```

- [ ] **Step 2: Commit**

```bash
git add packages/database/repository/event.py
git commit -m "feat(event): add EventRepository and EventInterestRepository"
```

---

## Task 4: Migration — Event Tablolari

**Files:**
- Create: `migrations/versions/0003_add_event_tables.py`

- [ ] **Step 1: Create migration file**

Create `migrations/versions/0003_add_event_tables.py`:

```python
"""Add event tables

Revision ID: 0003
Revises: 0002_add_slack_id_to_members
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003"
down_revision = "0002_add_slack_id_to_members"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.String(60), primary_key=True),
        sa.Column("creator_slack_id", sa.String(32), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("date", sa.Date, nullable=False, index=True),
        sa.Column("time", sa.Time, nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("location_type", sa.String(32), nullable=False),
        sa.Column("channel_id", sa.String(32), nullable=True),
        sa.Column("link", sa.String(500), nullable=True),
        sa.Column("yzta_request", sa.Text, nullable=True),
        sa.Column("status", sa.Enum("pending", "approved", "rejected", "cancelled", "completed", name="eventstatus"), nullable=False, index=True),
        sa.Column("admin_note", sa.Text, nullable=True),
        sa.Column("approved_by", sa.String(32), nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "event_interest",
        sa.Column("id", sa.String(60), primary_key=True),
        sa.Column("event_id", sa.String(60), sa.ForeignKey("events.id"), nullable=False, index=True),
        sa.Column("slack_id", sa.String(32), nullable=False, index=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("event_interest")
    op.drop_table("events")
    op.execute("DROP TYPE IF EXISTS eventstatus")
```

- [ ] **Step 2: Run migration**

```bash
python migrate.py upgrade
```

- [ ] **Step 3: Commit**

```bash
git add migrations/versions/0003_add_event_tables.py
git commit -m "feat(event): add event tables migration"
```

---

## Task 5: Calendar Utility

**Files:**
- Create: `services/event_service/utils/__init__.py`
- Create: `services/event_service/utils/calendar.py`

- [ ] **Step 1: Create __init__.py**

Create empty `services/event_service/utils/__init__.py`.

- [ ] **Step 2: Create calendar.py**

Create `services/event_service/utils/calendar.py`:

```python
"""Google Calendar URL olusturucu — API gerektirmez, URL semasi kullanir."""
from __future__ import annotations

from datetime import date, time, datetime, timedelta, timezone
from urllib.parse import quote


def build_google_calendar_url(
    title: str,
    event_date: date,
    event_time: time,
    duration_minutes: int,
    description: str = "",
    location: str = "",
) -> str:
    """Google Calendar 'Add Event' URL'i olusturur."""
    start_dt = datetime.combine(event_date, event_time, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    date_fmt = "%Y%m%dT%H%M%SZ"
    dates = f"{start_dt.strftime(date_fmt)}/{end_dt.strftime(date_fmt)}"

    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": dates,
        "details": description,
        "location": location,
    }
    query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items() if v)
    return f"https://calendar.google.com/calendar/render?{query}"
```

- [ ] **Step 3: Commit**

```bash
git add services/event_service/utils/__init__.py services/event_service/utils/calendar.py
git commit -m "feat(event): add Google Calendar URL builder utility"
```

---

## Task 6: Logger ve Service Scaffolding

**Files:**
- Create: `services/event_service/__init__.py`
- Create: `services/event_service/logger.py`
- Create: `services/event_service/core/__init__.py`
- Create: `services/event_service/handlers/__init__.py`
- Create: `services/event_service/handlers/commands/__init__.py`
- Create: `services/event_service/handlers/events/__init__.py`

- [ ] **Step 1: Create __init__.py files**

Create empty files:
- `services/event_service/__init__.py`
- `services/event_service/core/__init__.py`
- `services/event_service/handlers/commands/__init__.py`
- `services/event_service/handlers/events/__init__.py`

- [ ] **Step 2: Create logger.py**

Create `services/event_service/logger.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.logger.manager import get_logger, start_logging

_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs" / "event_service"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

EVENT_SERVICE_LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "system": {
            "()": "packages.logger.formatters.SystemMessageFormatter",
        },
        "error_json": {
            "()": "packages.logger.formatters.ErrorMessageFormatter",
        },
    },
    "filters": {
        "system_only": {
            "()": "packages.logger.filters.SystemFilter",
        },
        "errors_only": {
            "()": "packages.logger.filters.ErrorFilter",
        },
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "system",
            "filters": ["system_only"],
            "stream": "ext://sys.stdout",
        },
        "console": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "system",
            "filters": ["system_only"],
            "filename": str(_LOG_DIR / "system.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "errors": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "error_json",
            "filters": ["errors_only"],
            "filename": str(_LOG_DIR / "errors.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["stdout", "console", "errors"],
    },
}

start_logging(EVENT_SERVICE_LOGGING)
_logger = get_logger("event_service")

__all__ = ["_logger"]
```

- [ ] **Step 3: Create handlers/__init__.py**

Create `services/event_service/handlers/__init__.py`:

```python
"""
Tum handler modullerini Slack App'e kayit eder.
Bu dosya import edildiginde, commands ve events icindeki
@app.command / @app.view / @app.action dekoratorleri otomatik olarak aktive olur.
"""
from .commands import event as event_commands  # noqa: F401
from .events import event as event_events  # noqa: F401
```

- [ ] **Step 4: Commit**

```bash
git add services/event_service/__init__.py services/event_service/logger.py \
  services/event_service/core/__init__.py services/event_service/handlers/__init__.py \
  services/event_service/handlers/commands/__init__.py services/event_service/handlers/events/__init__.py
git commit -m "feat(event): add service scaffolding and logger"
```

---

## Task 7: Notification Utilities

**Files:**
- Create: `services/event_service/utils/notifications.py`

- [ ] **Step 1: Create notifications.py**

Create `services/event_service/utils/notifications.py`:

```python
"""Event Service — Slack bildirim yardimcilari."""
from __future__ import annotations

from packages.settings import get_settings
from packages.slack.client import slack_client
from packages.slack.blocks.builder import MessageBuilder, BlockBuilder
from packages.database.models.event import Event, LocationType
from ..utils.calendar import build_google_calendar_url
from ..logger import _logger


def _location_display(event: Event) -> str:
    """Lokasyon gosterimi: Slack kanali ise <#C123>, degilse tip adi."""
    if event.location_type == LocationType.SLACK_CHANNEL.value and event.channel_id:
        return f"<#{event.channel_id}>"
    return {
        "zoom": "Zoom", "youtube": "YouTube", "google_meet": "Google Meet",
        "discord": "Discord", "other": "Diger",
    }.get(event.location_type, event.location_type)


def _calendar_url(event: Event) -> str:
    location = event.link or (_location_display(event))
    return build_google_calendar_url(
        title=event.name,
        event_date=event.date,
        event_time=event.time,
        duration_minutes=event.duration_minutes,
        description=event.description,
        location=location,
    )


def get_announcement_channels(event: Event) -> list[str]:
    """Duyuru kanallarini belirler: event_channel + (farkli ise) channel_id."""
    s = get_settings()
    channels = [s.event_channel]
    if (event.location_type == LocationType.SLACK_CHANNEL.value
            and event.channel_id
            and event.channel_id != s.event_channel):
        channels.append(event.channel_id)
    return channels


def post_announcement(event: Event, interest_count: int = 0) -> None:
    """Onay sonrasi ilk duyuru mesajini gonderir."""
    cal_url = _calendar_url(event)
    loc = _location_display(event)

    builder = MessageBuilder()
    builder.add_header("Yeni Etkinlik Duyurusu")

    lines = [
        f"*{event.name}*",
        "",
        f"*Konu:* {event.topic}",
        f"*Aciklama:* {event.description}",
        "",
        f"*Tarih:* {event.date.strftime('%d %B %Y')}",
        f"*Saat:* {event.time.strftime('%H:%M')}",
        f"*Sure:* {event.duration_minutes} dakika",
        f"*Lokasyon:* {loc}",
    ]
    if event.link:
        lines.append(f"*Link:* <{event.link}>")
    lines.append(f"*Duzenleyen:* <@{event.creator_slack_id}>")
    builder.add_text("\n".join(lines))

    builder.add_divider()
    builder.add_button("Katilacagim", "event_interest_btn", value=event.id, style="primary")
    builder.add_button("Google Takvime Ekle", "event_calendar_btn", value=event.id, url=cal_url)

    if interest_count > 0:
        builder.add_context([f"_{interest_count} kisi ilgi gosterdi_"])

    blocks = builder.build()
    text = f"Yeni Etkinlik: {event.name}"

    for ch in get_announcement_channels(event):
        try:
            slack_client.bot_client.chat_postMessage(channel=ch, text=text, blocks=blocks)
        except Exception as e:
            _logger.error("[EVT-NOTIFY] Duyuru gonderilemedi channel=%s: %s", ch, e)


def post_cancellation(event: Event, cancelled_by_slack_id: str) -> None:
    """Iptal duyurusu gonderir."""
    builder = MessageBuilder()
    builder.add_header("Etkinlik Iptal Edildi")
    builder.add_text(
        f"*{event.name}*\n\n"
        f"*Tarih:* {event.date.strftime('%d %B %Y')} · *Saat:* {event.time.strftime('%H:%M')}\n"
        f"*Duzenleyen:* <@{event.creator_slack_id}>\n"
        f"*Iptal Eden:* <@{cancelled_by_slack_id}>\n\n"
        "Bu etkinlik iptal edilmistir."
    )
    builder.add_context([f"_{event.id}_"])

    blocks = builder.build()
    for ch in get_announcement_channels(event):
        try:
            slack_client.bot_client.chat_postMessage(
                channel=ch, text=f"Etkinlik Iptal: {event.name}", blocks=blocks,
            )
        except Exception as e:
            _logger.error("[EVT-NOTIFY] Iptal duyurusu gonderilemedi channel=%s: %s", ch, e)


def post_update_announcement(event: Event) -> None:
    """Guncelleme duyurusu gonderir."""
    cal_url = _calendar_url(event)
    loc = _location_display(event)

    builder = MessageBuilder()
    builder.add_header("Etkinlik Guncellendi")

    lines = [
        f"*{event.name}*",
        "",
        f"*Tarih:* {event.date.strftime('%d %B %Y')}",
        f"*Saat:* {event.time.strftime('%H:%M')}",
        f"*Sure:* {event.duration_minutes} dakika",
        f"*Lokasyon:* {loc}",
    ]
    if event.link:
        lines.append(f"*Link:* <{event.link}>")
    lines.append(f"*Duzenleyen:* <@{event.creator_slack_id}>")
    builder.add_text("\n".join(lines))

    builder.add_divider()
    builder.add_button("Katilacagim", "event_interest_btn", value=event.id, style="primary")
    builder.add_button("Google Takvime Ekle", "event_calendar_btn", value=event.id, url=cal_url)

    blocks = builder.build()
    for ch in get_announcement_channels(event):
        try:
            slack_client.bot_client.chat_postMessage(
                channel=ch, text=f"Etkinlik Guncellendi: {event.name}", blocks=blocks,
            )
        except Exception as e:
            _logger.error("[EVT-NOTIFY] Guncelleme duyurusu gonderilemedi channel=%s: %s", ch, e)


def send_dm(slack_id: str, text: str, blocks: list | None = None) -> None:
    """Kullaniciya DM gonderir."""
    try:
        slack_client.bot_client.chat_postMessage(channel=slack_id, text=text, blocks=blocks)
    except Exception as e:
        _logger.error("[EVT-NOTIFY] DM gonderilemedi user=%s: %s", slack_id, e)


def post_admin_request(event: Event) -> None:
    """Admin kanalina onay/red butonlu talep mesaji gonderir."""
    s = get_settings()
    loc = _location_display(event)

    builder = MessageBuilder()
    builder.add_header("Yeni Etkinlik Talebi")

    lines = [
        f"*{event.name}*",
        "",
        f"*Konu:* {event.topic}",
        f"*Aciklama:* {event.description}",
        "",
        f"*Tarih:* {event.date.strftime('%d %B %Y')}",
        f"*Saat:* {event.time.strftime('%H:%M')}",
        f"*Sure:* {event.duration_minutes} dakika",
        f"*Lokasyon:* {loc}",
    ]
    if event.link:
        lines.append(f"*Link:* <{event.link}>")
    lines.append(f"*Talep Eden:* <@{event.creator_slack_id}>")
    if event.yzta_request:
        lines.append(f"*YZTA'dan Beklenen:* {event.yzta_request}")
    builder.add_text("\n".join(lines))

    builder.add_divider()
    builder.add_button("Onayla", "event_approve_btn", value=event.id, style="primary")
    builder.add_button("Reddet", "event_reject_btn", value=event.id, style="danger")
    builder.add_context([f"_{event.id} · Gonderim: {event.created_at.strftime('%d %B %Y %H:%M')}_"])

    blocks = builder.build()
    try:
        slack_client.bot_client.chat_postMessage(
            channel=s.slack_admin_channel,
            text=f"Yeni Etkinlik Talebi: {event.name}",
            blocks=blocks,
        )
    except Exception as e:
        _logger.error("[EVT-NOTIFY] Admin talebi gonderilemedi: %s", e)
```

- [ ] **Step 2: Commit**

```bash
git add services/event_service/utils/notifications.py
git commit -m "feat(event): add Slack notification utilities"
```

---

## Task 8: Email Utilities

**Files:**
- Create: `services/event_service/utils/email.py`

- [ ] **Step 1: Create email.py**

Create `services/event_service/utils/email.py`:

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add services/event_service/utils/email.py
git commit -m "feat(event): add email notification utilities"
```

---

## Task 9: Slash Command Router + Simple Commands (help, list, my_list, history, cancel, add_me)

**Files:**
- Create: `services/event_service/handlers/commands/event.py`

- [ ] **Step 1: Create command router**

Create `services/event_service/handlers/commands/event.py`:

```python
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
    from services.challenge_service.core.event_loop import run_async
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
            # Her event icin ilgi sayisini al
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
                f"  @{evt.creator_slack_id} · {evt.date.strftime('%d %B')} {evt.time.strftime('%H:%M')} · {loc}"
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

    # Ilgi gosterenlere e-posta
    async def _notify_interested():
        async with db.session(read_only=True) as session:
            interest_repo = EventInterestRepository(session)
            interests = await interest_repo.list_by_event(event_id)
            return [i.slack_id for i in interests]

    try:
        interested_ids = _run_async(_notify_interested())
        from ...utils.email import send_cancellation_email
        for sid in interested_ids:
            # E-posta icin kullanici bilgisi gerekli — simdilik slack_id ile
            # gercek implementasyonda SlackUser'dan email alinabilir
            pass
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
```

- [ ] **Step 2: Commit**

```bash
git add services/event_service/handlers/commands/event.py
git commit -m "feat(event): add /event command router with list, my_list, history, add_me, cancel, update, help"
```

---

## Task 10: Event Handlers — Modal Submissions ve Button Actions

**Files:**
- Create: `services/event_service/handlers/events/event.py`

- [ ] **Step 1: Create event handlers**

Create `services/event_service/handlers/events/event.py`:

```python
"""
Event Service — Modal submission ve buton action handler'lari.
- event_create_modal: Yeni etkinlik formu gonderimi
- event_update_modal: Guncelleme formu gonderimi
- event_approve_btn / event_reject_btn: Admin onay/red butonlari
- event_interest_btn: Katilacagim butonu
"""
from __future__ import annotations

import json
from datetime import datetime, time, timezone

from slack_bolt import Ack, App
from sqlalchemy import select

from packages.database.manager import db
from packages.database.models.event import Event, EventInterest, EventStatus
from packages.database.repository.event import EventRepository, EventInterestRepository
from packages.settings import get_settings
from packages.slack.client import slack_client
from ...logger import _logger
from ...utils.notifications import (
    post_admin_request, post_announcement, post_update_announcement, send_dm,
)
from ...utils.email import send_admin_notification, send_user_status_email
from ...utils.calendar import build_google_calendar_url
from ...utils.notifications import _location_display
from packages.slack.blocks.builder import MessageBuilder

app: App = slack_client.app
settings = get_settings()


def _run_async(coro, timeout=30.0):
    from services.challenge_service.core.event_loop import run_async
    return run_async(coro, timeout=timeout)


def _extract_form_values(values: dict) -> dict:
    """Modal form degerlerini cikarir."""
    location_type = values.get("event_location", {}).get("val", {}).get("selected_option", {}).get("value", "other")
    return {
        "name": values.get("event_name", {}).get("val", {}).get("value", ""),
        "topic": values.get("event_topic", {}).get("val", {}).get("value", ""),
        "description": values.get("event_description", {}).get("val", {}).get("value", ""),
        "date": values.get("event_date", {}).get("val", {}).get("selected_date"),
        "time": values.get("event_time", {}).get("val", {}).get("selected_time"),
        "duration_minutes": int(values.get("event_duration", {}).get("val", {}).get("selected_option", {}).get("value", "60")),
        "location_type": location_type,
        "channel_id": values.get("event_channel", {}).get("val", {}).get("selected_channel"),
        "link": values.get("event_link", {}).get("val", {}).get("value"),
        "yzta_request": values.get("event_yzta", {}).get("val", {}).get("value"),
    }


def _validate_form(data: dict) -> str | None:
    """Backend validasyonu. Hata mesaji doner, gecerliyse None."""
    if data["location_type"] == "slack_channel" and not data.get("channel_id"):
        return "Slack Kanali secildiginde kanal alani zorunludur."
    if data["location_type"] != "slack_channel" and not data.get("link"):
        return "Harici platform secildiginde link alani zorunludur."
    if not data.get("date") or not data.get("time"):
        return "Tarih ve saat zorunludur."
    return None


# ---------------------------------------------------------------------------
# event_create_modal — Yeni etkinlik formu gonderimi
# ---------------------------------------------------------------------------

@app.view("event_create_modal")
def handle_create_modal(ack: Ack, body: dict, client, view):
    user_id = body["user"]["id"]
    values = view["state"]["values"]
    data = _extract_form_values(values)

    error = _validate_form(data)
    if error:
        ack(response_action="errors", errors={"event_location": error})
        return
    ack()

    # Parse date/time
    evt_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
    evt_time = datetime.strptime(data["time"], "%H:%M").time()

    async def _create():
        async with db.session() as session:
            event = Event(
                creator_slack_id=user_id,
                name=data["name"],
                topic=data["topic"],
                description=data["description"],
                date=evt_date,
                time=evt_time,
                duration_minutes=data["duration_minutes"],
                location_type=data["location_type"],
                channel_id=data.get("channel_id"),
                link=data.get("link"),
                yzta_request=data.get("yzta_request"),
                status=EventStatus.PENDING,
            )
            session.add(event)
            await session.flush()
            return event

    try:
        event = _run_async(_create())
    except Exception as e:
        _logger.error("[EVT] Create failed: %s", e)
        return

    # Admin kanalina bildirim
    post_admin_request(event)
    send_admin_notification(event)

    # Kullaniciya ephemeral + DM
    loc = _location_display(event)
    confirm_text = (
        f"Etkinlik talebiniz basariyla iletildi!\n\n"
        f"*{event.name}*\n"
        f"{event.date.strftime('%d %B %Y')} · {event.time.strftime('%H:%M')} · {loc}\n\n"
        f"Admin onayini bekliyor. Sonuc Slack DM ve e-posta ile bildirilecek.\n"
        f"_Talep ID: {event.id}_"
    )
    # Ephemeral — modal submission'da channel yok, DM gonder
    send_dm(user_id, confirm_text)

    _logger.info("[EVT] Event created: %s by %s", event.id, user_id)


# ---------------------------------------------------------------------------
# event_update_modal — Guncelleme formu gonderimi
# ---------------------------------------------------------------------------

@app.view("event_update_modal")
def handle_update_modal(ack: Ack, body: dict, client, view):
    user_id = body["user"]["id"]
    meta = json.loads(view.get("private_metadata") or "{}")
    event_id = meta.get("event_id")
    if not event_id:
        ack()
        return

    values = view["state"]["values"]
    data = _extract_form_values(values)

    error = _validate_form(data)
    if error:
        ack(response_action="errors", errors={"event_location": error})
        return
    ack()

    evt_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
    evt_time = datetime.strptime(data["time"], "%H:%M").time()

    async def _update():
        async with db.session() as session:
            repo = EventRepository(session)
            evt = await repo.get(event_id)
            if not evt or evt.status != EventStatus.APPROVED:
                return None, {}

            # Onceki degerleri kaydet (diff icin)
            old_values = {
                "name": evt.name, "topic": evt.topic, "description": evt.description,
                "date": str(evt.date), "time": str(evt.time),
                "duration_minutes": evt.duration_minutes,
                "location_type": evt.location_type, "channel_id": evt.channel_id,
                "link": evt.link, "yzta_request": evt.yzta_request,
            }

            evt.name = data["name"]
            evt.topic = data["topic"]
            evt.description = data["description"]
            evt.date = evt_date
            evt.time = evt_time
            evt.duration_minutes = data["duration_minutes"]
            evt.location_type = data["location_type"]
            evt.channel_id = data.get("channel_id")
            evt.link = data.get("link")
            evt.yzta_request = data.get("yzta_request")
            await session.flush()

            # Diff hesapla
            new_values = {
                "name": evt.name, "topic": evt.topic, "description": evt.description,
                "date": str(evt.date), "time": str(evt.time),
                "duration_minutes": evt.duration_minutes,
                "location_type": evt.location_type, "channel_id": evt.channel_id,
                "link": evt.link, "yzta_request": evt.yzta_request,
            }
            diff = {k: (old_values[k], new_values[k]) for k in old_values if old_values[k] != new_values[k]}
            return evt, diff

    try:
        evt, diff = _run_async(_update())
    except Exception as e:
        _logger.error("[EVT] Update failed: %s", e)
        return

    if not evt:
        _logger.warning("[EVT] Update rejected: event=%s", event_id)
        return

    if not diff:
        _logger.info("[EVT] Update no changes: event=%s", event_id)
        return

    # Admin kanalina oncesi/sonrasi diff bildirimi
    diff_lines = []
    field_labels = {
        "name": "Ad", "topic": "Konu", "description": "Aciklama",
        "date": "Tarih", "time": "Saat", "duration_minutes": "Sure",
        "location_type": "Lokasyon", "channel_id": "Kanal", "link": "Link",
        "yzta_request": "YZTA Talep",
    }
    for k, (old, new) in diff.items():
        label = field_labels.get(k, k)
        old_display = old or "—"
        diff_lines.append(f"*{label}:* ~{old_display}~ → *{new}*")

    diff_text = (
        f"Etkinlik Guncellendi\n\n"
        f"*{evt.name}*\n"
        f"*Guncelleyen:* <@{user_id}>\n\n"
        f"*Degisen Alanlar:*\n" + "\n".join(diff_lines) + f"\n\n_{evt.id}_"
    )
    try:
        slack_client.bot_client.chat_postMessage(
            channel=settings.slack_admin_channel, text=diff_text,
        )
    except Exception as e:
        _logger.error("[EVT] Admin update notification failed: %s", e)

    # Duyuru kanallarina guncelleme bildirisi
    post_update_announcement(evt)

    _logger.info("[EVT] Event updated: %s by %s diff=%s", event_id, user_id, list(diff.keys()))


# ---------------------------------------------------------------------------
# Admin Onay/Red butonlari
# ---------------------------------------------------------------------------

@app.action("event_approve_btn")
def handle_approve_btn(ack: Ack, body: dict, client, action):
    ack()
    event_id = action.get("value")
    trigger_id = body.get("trigger_id")
    # Admin onay modali ac (opsiyonel not)
    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "event_admin_approve_modal",
            "private_metadata": event_id,
            "title": {"type": "plain_text", "text": "Etkinlik Onayla"},
            "submit": {"type": "plain_text", "text": "Onayla"},
            "close": {"type": "plain_text", "text": "Iptal"},
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"Etkinlik *{event_id}* onaylanacak."}},
                {"type": "input", "block_id": "admin_note", "optional": True,
                 "element": {"type": "plain_text_input", "action_id": "val", "multiline": True,
                             "placeholder": {"type": "plain_text", "text": "Varsa eklemek istediginiz notu yazin..."}},
                 "label": {"type": "plain_text", "text": "Not (opsiyonel)"}},
            ],
        },
    )


@app.action("event_reject_btn")
def handle_reject_btn(ack: Ack, body: dict, client, action):
    ack()
    event_id = action.get("value")
    trigger_id = body.get("trigger_id")
    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "event_admin_reject_modal",
            "private_metadata": event_id,
            "title": {"type": "plain_text", "text": "Etkinlik Reddet"},
            "submit": {"type": "plain_text", "text": "Reddet"},
            "close": {"type": "plain_text", "text": "Iptal"},
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"Etkinlik *{event_id}* reddedilecek."}},
                {"type": "input", "block_id": "admin_note", "optional": True,
                 "element": {"type": "plain_text_input", "action_id": "val", "multiline": True,
                             "placeholder": {"type": "plain_text", "text": "Varsa eklemek istediginiz notu yazin..."}},
                 "label": {"type": "plain_text", "text": "Not (opsiyonel)"}},
            ],
        },
    )


@app.view("event_admin_approve_modal")
def handle_admin_approve(ack: Ack, body: dict, client, view):
    ack()
    event_id = view.get("private_metadata")
    admin_id = body["user"]["id"]
    note = view["state"]["values"].get("admin_note", {}).get("val", {}).get("value")

    async def _approve():
        async with db.session() as session:
            repo = EventRepository(session)
            evt = await repo.get(event_id)
            if not evt or evt.status != EventStatus.PENDING:
                return None
            evt.status = EventStatus.APPROVED
            evt.approved_by = admin_id
            if note:
                evt.admin_note = note
            await session.flush()
            return evt

    evt = _run_async(_approve())
    if not evt:
        return

    # Kullaniciya DM
    note_text = f"\n*Admin Notu:* {note}" if note else ""
    loc = _location_display(evt)
    send_dm(
        evt.creator_slack_id,
        f"Etkinliginiz Onaylandi!\n\n"
        f"*{evt.name}*\n"
        f"{evt.date.strftime('%d %B %Y')} · {evt.time.strftime('%H:%M')} · {loc}"
        f"{note_text}\n\n"
        f"Duyuru #serbest-kursu kanalina gonderildi.\n_{evt.id}_"
    )

    # Kullaniciya e-posta
    send_user_status_email("", evt, "approved", note)

    # Duyuru
    post_announcement(evt)

    _logger.info("[EVT] Event approved: %s by admin %s", event_id, admin_id)


@app.view("event_admin_reject_modal")
def handle_admin_reject(ack: Ack, body: dict, client, view):
    ack()
    event_id = view.get("private_metadata")
    admin_id = body["user"]["id"]
    note = view["state"]["values"].get("admin_note", {}).get("val", {}).get("value")

    async def _reject():
        async with db.session() as session:
            repo = EventRepository(session)
            evt = await repo.get(event_id)
            if not evt or evt.status != EventStatus.PENDING:
                return None
            evt.status = EventStatus.REJECTED
            if note:
                evt.admin_note = note
            await session.flush()
            return evt

    evt = _run_async(_reject())
    if not evt:
        return

    note_text = f"\n*Admin Notu:* {note}" if note else ""
    send_dm(
        evt.creator_slack_id,
        f"Etkinliginiz Reddedildi\n\n"
        f"*{evt.name}*\n"
        f"{evt.date.strftime('%d %B %Y')} · {evt.time.strftime('%H:%M')}"
        f"{note_text}\n\n"
        f"Yeni bir etkinlik talebi icin `/event create` komutunu kullanabilirsiniz.\n_{evt.id}_"
    )

    send_user_status_email("", evt, "rejected", note)

    _logger.info("[EVT] Event rejected: %s by admin %s", event_id, admin_id)


# ---------------------------------------------------------------------------
# Katilacagim butonu
# ---------------------------------------------------------------------------

@app.action("event_interest_btn")
def handle_interest_btn(ack: Ack, body: dict, client, action):
    ack()
    event_id = action.get("value")
    user_id = body["user"]["id"]
    channel_id = body.get("channel", {}).get("id", "")

    async def _add_interest():
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
            count = await interest_repo.count_by_event(event_id)
            return evt, count

    try:
        evt, result = _run_async(_add_interest())
    except Exception as e:
        _logger.error("[EVT] Interest button failed: %s", e)
        return

    if result == "not_found":
        client.chat_postEphemeral(channel=channel_id, user=user_id,
                                   text="Etkinlik bulunamadi veya ilgi gosterilemez durumda.")
        return
    if result == "already":
        client.chat_postEphemeral(channel=channel_id, user=user_id,
                                   text=f"Bu etkinlige zaten ilgi gosterdiniz.\n*{evt.name}*\n_{evt.id}_")
        return

    # Basarili
    cal_url = build_google_calendar_url(
        title=evt.name, event_date=evt.date, event_time=evt.time,
        duration_minutes=evt.duration_minutes, description=evt.description,
        location=evt.link or "",
    )
    client.chat_postEphemeral(
        channel=channel_id, user=user_id,
        text=f"Ilgin kaydedildi!\n*{evt.name}*\n_{evt.id}_"
    )

    # DM
    dm_builder = MessageBuilder()
    loc = _location_display(evt)
    dm_builder.add_text(
        f"Ilgin kaydedildi!\n\n"
        f"*{evt.name}*\n"
        f"{evt.date.strftime('%d %B %Y')} · {evt.time.strftime('%H:%M')} · {loc}\n\n"
        f"Etkinlik gunu hatirlatma e-postasi alacaksin.\n_{evt.id}_"
    )
    dm_builder.add_button("Google Takvime Ekle", "event_calendar_btn", value=evt.id, url=cal_url)
    send_dm(user_id, f"Ilgin kaydedildi: {evt.name}", dm_builder.build())

    _logger.info("[EVT] Interest added: event=%s user=%s", event_id, user_id)


# Google Takvim butonu — URL butonu, backend action gerekmiyor ama Slack log'a alir
@app.action("event_calendar_btn")
def handle_calendar_btn(ack: Ack, body: dict, client, action):
    ack()
```

- [ ] **Step 2: Commit**

```bash
git add services/event_service/handlers/events/event.py
git commit -m "feat(event): add modal submissions and button action handlers"
```

---

## Task 11: Scheduler — Background Gorevler

**Files:**
- Create: `services/event_service/core/scheduler.py`

- [ ] **Step 1: Create scheduler**

Create `services/event_service/core/scheduler.py`:

```python
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
from datetime import datetime, date, time, timedelta, timezone

from packages.database.manager import db
from packages.database.models.event import EventStatus
from packages.database.repository.event import EventRepository, EventInterestRepository
from packages.settings import get_settings
from packages.slack.client import slack_client
from packages.slack.blocks.builder import MessageBuilder
from ..logger import _logger
from ..utils.notifications import (
    get_announcement_channels, send_dm, _location_display, _calendar_url,
)
from ..utils.email import send_reminder_email, send_user_status_email


class EventScheduler:
    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None

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
                # Kullaniciya DM
                send_dm(
                    evt.creator_slack_id,
                    f"Etkinlik Talebiniz Zaman Asimina Ugradi\n\n"
                    f"*{evt.name}*\n"
                    f"{evt.date.strftime('%d %B %Y')} · {evt.time.strftime('%H:%M')}\n\n"
                    f"Talebiniz {s.event_approval_timeout_hours // 24} gun icinde yanit alamadigi icin "
                    f"otomatik olarak reddedildi.\n\n"
                    f"Yeni bir etkinlik talebi icin `/event create` komutunu kullanabilirsiniz.\n_{evt.id}_"
                )

    # ---- 2. COMPLETED gecisi ----

    async def _check_completed_transition(self) -> None:
        today = date.today()
        async with db.session() as session:
            repo = EventRepository(session)
            past = await repo.list_approved_past(today)
            for evt in past:
                evt.status = EventStatus.COMPLETED
                _logger.info("[SCHED] Completed: %s", evt.id)

    # ---- 3. Gun basi hatirlatma ----

    async def _check_morning_reminder(self) -> None:
        """Her gun 08:00 UTC'de o gunun etkinliklerini duyurur."""
        now = datetime.now(timezone.utc)
        if now.hour != 8 or now.minute > 1:
            return

        s = get_settings()
        if not s.event_reminder_enabled:
            return

        today = date.today()
        async with db.session(read_only=True) as session:
            repo = EventRepository(session)
            events = await repo.list_approved_by_date(today)
            if not events:
                return

            interest_repo = EventInterestRepository(session)

            # Kanal mesaji olustur
            builder = MessageBuilder()
            builder.add_header(f"Bugunun Etkinlikleri — {today.strftime('%d %B %Y')}")
            builder.add_divider()

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
                builder.add_button("Takvime Ekle", f"event_cal_{evt.id}", url=cal_url)
                builder.add_divider()

            builder.add_context(["_Iyi etkinlikler!_"])
            blocks = builder.build()

            # Duyuru kanallarina gonder
            for evt in events:
                for ch in get_announcement_channels(evt):
                    try:
                        slack_client.bot_client.chat_postMessage(
                            channel=ch,
                            text=f"Bugunun Etkinlikleri — {today.strftime('%d %B %Y')}",
                            blocks=blocks,
                        )
                    except Exception as e:
                        _logger.error("[SCHED] Morning reminder failed channel=%s: %s", ch, e)
                    break  # Ayni mesaji bir kere gonder

            # Ilgi gosterenlere e-posta
            for evt in events:
                interests = await interest_repo.list_by_event(evt.id)
                for interest in interests:
                    send_reminder_email("", evt, "day")

    # ---- 4. 10dk oncesi hatirlatma ----

    async def _check_10min_reminder(self) -> None:
        s = get_settings()
        if not s.event_reminder_enabled:
            return

        now = datetime.now(timezone.utc)
        target_time = (now + timedelta(minutes=10)).time()
        today = date.today()

        async with db.session(read_only=True) as session:
            repo = EventRepository(session)
            events = await repo.list_approved_by_date(today)

            interest_repo = EventInterestRepository(session)

            for evt in events:
                # 10dk penceresi icinde mi? (±1 dakika tolerans)
                evt_dt = datetime.combine(today, evt.time, tzinfo=timezone.utc)
                diff = (evt_dt - now).total_seconds()
                if not (540 <= diff <= 660):  # 9-11 dakika arasi
                    continue

                # Zaten bildirim gonderildi mi? (meta kontrolu)
                meta = evt.meta or {}
                if meta.get("10min_reminder_sent"):
                    continue

                loc = _location_display(evt)
                count = await interest_repo.count_by_event(evt.id)
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

                # Meta'ya bildirim gonderildi isareti koy
                async with db.session() as write_session:
                    write_evt = await write_session.get(Event, evt.id)
                    if write_evt:
                        m = dict(write_evt.meta or {})
                        m["10min_reminder_sent"] = True
                        write_evt.meta = m

                # Ilgi gosterenlere e-posta
                interests = await interest_repo.list_by_event(evt.id)
                for interest in interests:
                    send_reminder_email("", evt, "10min")

                _logger.info("[SCHED] 10min reminder sent: %s", evt.id)


event_scheduler = EventScheduler()
```

- [ ] **Step 2: Commit**

```bash
git add services/event_service/core/scheduler.py
git commit -m "feat(event): add background scheduler (timeout, reminders, completion)"
```

---

## Task 12: Final Commit — Tum __init__.py Dosyalari ve Kontrol

- [ ] **Step 1: Verify all __init__.py files exist**

Ensure these empty files exist:
- `services/event_service/__init__.py`
- `services/event_service/core/__init__.py`
- `services/event_service/handlers/__init__.py`
- `services/event_service/handlers/commands/__init__.py`
- `services/event_service/handlers/events/__init__.py`
- `services/event_service/utils/__init__.py`

- [ ] **Step 2: Run migration to verify**

```bash
python migrate.py upgrade
```

Expected: Migration 0003 applies successfully.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat(event): complete event service implementation"
```
