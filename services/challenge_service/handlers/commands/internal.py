"""
Internal Challenge Commands (submit & evaluate)
Bu komutlar sadece ChannelRegistry'deki kanallardan çalışır:
  - /challenge submit → registry.has_challenge(channel_id)
  - /challenge evaluate → registry.has_evaluation(channel_id)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from slack_bolt import App
from sqlalchemy import select

from packages.database.manager import db
from packages.database.models.challenge import Challenge, ChallengeStatus
from packages.slack.blocks.builder import MessageBuilder
from packages.slack.client import slack_client
from ...api.state import active_state
from ...core.event_loop import run_async
from ...logger import _logger
from ...manager import service_manager
from ...utils.slack_helpers import slack_helper

app: App = slack_client.app


def _is_challenge_channel(channel_id: str) -> bool:
    """ChannelRegistry → challenge kanalı mı?"""
    return service_manager.registry.has_challenge(channel_id)


# ---------------------------------------------------------------------------
# /challenge submit   (sadece challenge kanallarında çalışır)
# ---------------------------------------------------------------------------

def handle_submit(client, body: dict) -> None:
    """
    Teslimat penceresini açar:
    - Kanaldaki aktif STARTED challenge'ı bulur
    - 10 dakikalık teslimat penceresi başlatır
    - Kanala "Teslim Et / Bırak" butonları atar
    """
    channel_id = body["channel_id"]
    user_id = body["user_id"]

    # İzin kontrolü: sadece challenge kanalında çalışır
    if not _is_challenge_channel(channel_id):
        client.chat_postEphemeral(
            channel=channel_id, user=user_id,
            text="⚠️ Bu komut yalnızca aktif bir challenge kanalında kullanılabilir."
        )
        return

    async def _fetch():
        async with db.session(read_only=True) as session:
            stmt = (
                select(Challenge)
                .where(
                    Challenge.challenge_channel_id == channel_id,
                    Challenge.status == ChallengeStatus.STARTED,
                )
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    challenge = run_async(_fetch())
    if not challenge:
        client.chat_postEphemeral(
            channel=channel_id, user=user_id,
            text="❌ Bu kanalda aktif (STARTED) bir challenge bulunamadı."
        )
        return

    # Teslimat penceresi zaten açıksa tekrar açma
    if active_state.is_submission_open(challenge.id):
        client.chat_postEphemeral(
            channel=channel_id, user=user_id,
            text="⏳ Teslimat penceresi zaten açık — butona tıklayarak formu doldurabilirsiniz."
        )
        return

    # 10 dakikalık teslimat penceresi başlat
    deadline = datetime.now(timezone.utc) + timedelta(minutes=10)
    active_state.set_submission_deadline(challenge.id, deadline)

    builder = MessageBuilder()
    builder.add_header("🚀 Proje Teslimatı Başladı")
    builder.add_text(
        "Takım, teslimatı tamamlamak için *10 dakikanız* var.\n"
        "Hazır olduğunuzda aşağıdaki butona basın."
    )
    builder.add_button("📦 Form ile Teslim Et", "open_submission_modal", value=challenge.id, style="primary")
    builder.add_button("🏳️ Projeyi Bırak", "surrender_challenge", value=challenge.id, style="danger")

    slack_helper.post_message(
        channel_id=channel_id,
        text="Teslimat penceresi açıldı!",
        blocks=builder.build()
    )
    _logger.info("[CMD] Submission window opened: challenge=%s channel=%s", challenge.id, channel_id)
