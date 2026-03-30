from __future__ import annotations

from dataclasses import dataclass, field, replace
from threading import RLock
from typing import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.models.challenge import Challenge

from ...logger import _logger


def _slack_ids_from_team(challenge: Challenge) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for tm in challenge.challenge_team_members:
        sid = (tm.meta or {}).get("slack_id")
        if isinstance(sid, str) and sid and sid not in seen:
            seen.add(sid)
            out.append(sid)
    creator = challenge.creator_slack_id
    if creator and creator not in seen:
        out.insert(0, creator)
    return out


def _slack_ids_from_jury(challenge: Challenge) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for jm in challenge.challenge_jury_members:
        sid = (jm.meta or {}).get("slack_id")
        if isinstance(sid, str) and sid and sid not in seen:
            seen.add(sid)
            out.append(sid)
    return out


@dataclass(slots=True)
class ChannelRecord:
    """
    Kanal başına hafıza: iki Slack ID listesi (katılımcılar / jüri) + opsiyonel admin.
    Kuyruk değil — sadece kayıt tutmak için.
    """

    channel_id: str
    challenge_id: str | None = None
    members: list[str] = field(default_factory=list)
    jury: list[str] = field(default_factory=list)
    admin_slack_id: str | None = None

    def copy(self) -> ChannelRecord:
        return replace(
            self,
            members=list(self.members),
            jury=list(self.jury),
        )


class ChannelRegistry:
    """
    Challenge ve evaluation kanalları için merkezi bellek.
    Ekle / çıkar / var mı sorgusu; thread-safe.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._challenge: dict[str, ChannelRecord] = {}
        self._evaluation: dict[str, ChannelRecord] = {}

    # --- challenge kanalları -------------------------------------------------

    def register_challenge(self, record: ChannelRecord) -> None:
        if not record.channel_id:
            raise ValueError("channel_id gerekli")
        with self._lock:
            self._challenge[record.channel_id] = record.copy()
            _logger.debug("channel_registry challenge register %s", record.channel_id)

    def unregister_challenge(self, channel_id: str) -> bool:
        with self._lock:
            if channel_id not in self._challenge:
                return False
            del self._challenge[channel_id]
            _logger.debug("channel_registry challenge unregister %s", channel_id)
            return True

    def has_challenge(self, channel_id: str) -> bool:
        with self._lock:
            return channel_id in self._challenge

    def get_challenge(self, channel_id: str) -> ChannelRecord | None:
        with self._lock:
            r = self._challenge.get(channel_id)
            return r.copy() if r else None

    def get_challenge_by_challenge_id(self, challenge_id: str) -> ChannelRecord | None:
        with self._lock:
            for rec in self._challenge.values():
                if rec.challenge_id == challenge_id:
                    return rec.copy()
            return None

    def challenge_channels(self) -> Mapping[str, ChannelRecord]:
        with self._lock:
            return {k: v.copy() for k, v in self._challenge.items()}

    # --- evaluation kanalları ------------------------------------------------

    def register_evaluation(self, record: ChannelRecord) -> None:
        if not record.channel_id:
            raise ValueError("channel_id gerekli")
        with self._lock:
            self._evaluation[record.channel_id] = record.copy()
            _logger.debug("channel_registry evaluation register %s", record.channel_id)

    def unregister_evaluation(self, channel_id: str) -> bool:
        with self._lock:
            if channel_id not in self._evaluation:
                return False
            del self._evaluation[channel_id]
            _logger.debug("channel_registry evaluation unregister %s", channel_id)
            return True

    def has_evaluation(self, channel_id: str) -> bool:
        with self._lock:
            return channel_id in self._evaluation

    def get_evaluation(self, channel_id: str) -> ChannelRecord | None:
        with self._lock:
            r = self._evaluation.get(channel_id)
            return r.copy() if r else None

    def evaluation_channels(self) -> Mapping[str, ChannelRecord]:
        with self._lock:
            return {k: v.copy() for k, v in self._evaluation.items()}

    # --- genel ---------------------------------------------------------------

    def has_any(self, channel_id: str) -> bool:
        with self._lock:
            return channel_id in self._challenge or channel_id in self._evaluation

    def clear(self) -> None:
        with self._lock:
            self._challenge.clear()
            self._evaluation.clear()

    def transition_challenge_to_evaluation(
        self,
        challenge_id: str,
        evaluation_channel_id: str,
        *,
        jury: list[str] | None = None,
    ) -> ChannelRecord | None:
        """
        Challenge → evaluation: `challenge_id` ile challenge kaydını bulur, challenge
        haritasından siler, aynı üyeler + jüri ile evaluation kaydı ekler (tek atomik işlem).

        ``evaluation_channel_id`` genelde değerlendirme kanalı oluşturulduktan sonra gelir.
        ``jury`` verilmezse önceki kayıttaki ``jury`` listesi korunur (çoğunlukla boştuysa
        çağıranın ``jury=[...]`` geçmesi beklenir).
        """
        if not evaluation_channel_id:
            raise ValueError("evaluation_channel_id gerekli")

        with self._lock:
            old_key: str | None = None
            old: ChannelRecord | None = None
            for cid, rec in self._challenge.items():
                if rec.challenge_id == challenge_id:
                    old_key, old = cid, rec
                    break
            if old is None or old_key is None:
                _logger.warning(
                    "transition_challenge_to_evaluation: challenge_id=%s bulunamadı",
                    challenge_id,
                )
                return None

            del self._challenge[old_key]

            jury_list = list(jury) if jury is not None else list(old.jury)
            new_rec = ChannelRecord(
                channel_id=evaluation_channel_id,
                challenge_id=challenge_id,
                members=list(old.members),
                jury=jury_list,
                admin_slack_id=old.admin_slack_id,
            )
            self._evaluation[evaluation_channel_id] = new_rec.copy()
            _logger.info(
                "channel_registry challenge→evaluation %s challenge_chan=%s eval_chan=%s",
                challenge_id,
                old_key,
                evaluation_channel_id,
            )
            return new_rec.copy()


async def _on_startup(
    registry: ChannelRegistry,
    session: AsyncSession,
    admin_slack_id: str | None = None,
) -> None:
    """
    Uygulama açılışında DB'den kanal kayıtlarını yükler.

    - STARTED, COMPLETED → ``challenge_channel_id`` (challenge registry)
    - IN_EVALUATION, EVALUATION_DELAYED → ``evaluation_channel_id`` (evaluation registry)
    """
    from packages.database.repository.challenge import ChallengeRepository

    repo = ChallengeRepository(session)
    started = await repo.list_started()
    completed = await repo.list_completed()
    in_evaluation = await repo.list_in_evaluation()
    evaluation_delayed = await repo.list_evaluation_delayed()

    registry.clear()

    for ch in started + completed:
        cid = ch.challenge_channel_id
        if not cid:
            continue
        registry.register_challenge(
            ChannelRecord(
                channel_id=cid,
                challenge_id=ch.id,
                members=_slack_ids_from_team(ch),
                jury=_slack_ids_from_jury(ch),
                admin_slack_id=admin_slack_id,
            )
        )

    for ch in in_evaluation + evaluation_delayed:
        eid = ch.evaluation_channel_id
        if not eid:
            continue
        registry.register_evaluation(
            ChannelRecord(
                channel_id=eid,
                challenge_id=ch.id,
                members=_slack_ids_from_team(ch),
                jury=_slack_ids_from_jury(ch),
                admin_slack_id=admin_slack_id,
            )
        )

    _logger.info(
        "channel_registry _on_startup: challenge=%s evaluation=%s",
        len(registry.challenge_channels()),
        len(registry.evaluation_channels()),
    )