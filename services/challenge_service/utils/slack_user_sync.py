from __future__ import annotations

from typing import Any

from packages.database.manager import db
from packages.database.models.slack import SlackUser
from packages.database.repository.slack import SlackUserRepository
from packages.slack.client import slack_client
from ..logger import _logger

logger = _logger


def _fields_from_slack_user(user: dict[str, Any]) -> dict[str, Any]:
    profile = user.get("profile") or {}
    display = profile.get("display_name") or profile.get("real_name") or user.get("real_name")
    return {
        "username": user.get("name"),
        "real_name": user.get("real_name"),
        "display_name": display,
        "email": profile.get("email"),
        "is_bot": bool(user.get("is_bot")),
        "is_deleted": bool(user.get("deleted")),
    }


async def get_or_create(slack_id: str) -> SlackUser | None:
    """
    slack_users'da kayıt yoksa Slack API'den profil alıp oluşturur; varsa mevcut kaydı döner.
    """
    async with db.session() as session:
        repo = SlackUserRepository(session)
        if existing := await repo.get_by_slack_id(slack_id):
            return existing

        try:
            resp = slack_client.bot_client.users_info(user=slack_id)
        except Exception:
            logger.exception("Slack users_info failed for %s", slack_id)
            return None

        if not resp.get("ok"):
            logger.error("Slack API error for %s: %s", slack_id, resp.get("error"))
            return None

        fields = _fields_from_slack_user(resp["user"])
        user = await repo.create(SlackUser(slack_id=slack_id, **fields))
        logger.info("Slack user synced: %s (%s)", slack_id, user.username or "—")
        return user
