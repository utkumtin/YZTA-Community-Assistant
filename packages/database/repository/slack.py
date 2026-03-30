from __future__ import annotations

from sqlalchemy import select

from packages.database.models.slack import SlackUser
from packages.database.repository.base import BaseRepository


class SlackUserRepository(BaseRepository[SlackUser]):
    model = SlackUser

    async def get_by_slack_id(self, slack_id: str) -> SlackUser | None:
        stmt = select(self.model).where(self.model.slack_id == slack_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, slack_id: str, **fields) -> SlackUser:
        existing = await self.get_by_slack_id(slack_id)
        if existing:
            return existing
        return await self.create(SlackUser(slack_id=slack_id, **fields))
