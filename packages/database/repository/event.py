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
