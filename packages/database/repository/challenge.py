from __future__ import annotations

import random

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from packages.database.models.challenge import (
    Challenge,
    ChallengeCategory,
    ChallengeJuryMember,
    ChallengeStatus,

    ChallengeTeamMember,
    ChallengeType,
)
from packages.database.repository.base import BaseRepository

_DONE_STATUSES = (ChallengeStatus.COMPLETED, ChallengeStatus.EVALUATED)


class ChallengeTypeRepository(BaseRepository[ChallengeType]):
    model = ChallengeType

    async def list_by_category(self, category: ChallengeCategory) -> list[ChallengeType]:
        """Belirli kategorideki tüm challenge type'larını döner."""
        result = await self.session.execute(
            select(ChallengeType).where(ChallengeType.category == category)
        )
        return list(result.scalars().all())

    async def pick_random_for_participants(
        self,
        category: ChallengeCategory,
        participant_slack_ids: list[str],
    ) -> ChallengeType | None:
        """
        Verilen kategori ve katılımcılar için:
        - Katılımcıların hiçbirinin daha önce tamamlamadığı bir ChallengeType seçer.
        - Tüm type'lar yapılmışsa herhangi birini rastgele seçer (fallback).
        - Hiç type yoksa None döner.
        """
        all_types = await self.list_by_category(category)
        if not all_types:
            return None

        # Katılımcıların tamamladığı challenge type ID'lerini bul
        used_stmt = (
            select(Challenge.challenge_type_id)
            .join(ChallengeTeamMember, ChallengeTeamMember.challenge_id == Challenge.id)
            .where(
                ChallengeTeamMember.slack_id.in_(participant_slack_ids),
                Challenge.status.in_(_DONE_STATUSES),
                Challenge.challenge_type_id.is_not(None),
            )
            .distinct()
        )
        used_result = await self.session.execute(used_stmt)
        used_ids = {row[0] for row in used_result.fetchall()}

        available = [t for t in all_types if t.id not in used_ids]
        pool = available if available else all_types
        return random.choice(pool)


class ChallengeRepository(BaseRepository[Challenge]):
    model = Challenge

    def _base_list_with_members(self, status: ChallengeStatus):
        return (
            select(self.model)
            .where(self.model.status == status)
            .options(
                joinedload(self.model.challenge_team_members),
                joinedload(self.model.challenge_jury_members),
                joinedload(self.model.challenge_type),
            )
        )

    async def list_not_started(self) -> list[Challenge]:
        """ChallengeStatus.NOT_STARTED kayıtları (takım + jüri ilişkileriyle)."""
        result = await self.session.execute(self._base_list_with_members(ChallengeStatus.NOT_STARTED))
        return list(result.unique().scalars().all())

    async def list_started(self) -> list[Challenge]:
        """ChallengeStatus.STARTED kayıtları."""
        result = await self.session.execute(self._base_list_with_members(ChallengeStatus.STARTED))
        return list(result.unique().scalars().all())

    async def list_completed(self) -> list[Challenge]:
        """ChallengeStatus.COMPLETED kayıtları."""
        result = await self.session.execute(self._base_list_with_members(ChallengeStatus.COMPLETED))
        return list(result.unique().scalars().all())

    async def list_not_completed(self) -> list[Challenge]:
        """ChallengeStatus.NOT_COMPLETED kayıtları."""
        result = await self.session.execute(self._base_list_with_members(ChallengeStatus.NOT_COMPLETED))
        return list(result.unique().scalars().all())

    async def list_in_evaluation(self) -> list[Challenge]:
        """ChallengeStatus.IN_EVALUATION kayıtları."""
        result = await self.session.execute(self._base_list_with_members(ChallengeStatus.IN_EVALUATION))
        return list(result.unique().scalars().all())

    async def list_evaluated(self) -> list[Challenge]:
        """ChallengeStatus.EVALUATED kayıtları."""
        result = await self.session.execute(self._base_list_with_members(ChallengeStatus.EVALUATED))
        return list(result.unique().scalars().all())

    async def list_evaluation_delayed(self) -> list[Challenge]:
        """ChallengeStatus.EVALUATION_DELAYED kayıtları."""
        result = await self.session.execute(self._base_list_with_members(ChallengeStatus.EVALUATION_DELAYED))
        return list(result.unique().scalars().all())

    async def history_by_slack_id(self, slack_id: str) -> list[Challenge]:
        """
        Belirli bir kullanıcının (slack_id) katıldığı tüm challenge'ları
        kategorisi ve tipiyle birlikte döner; başlangıç tarihine göre DESC sıralı.
        """
        from sqlalchemy import desc
        stmt = (
            select(Challenge)
            .join(ChallengeTeamMember, ChallengeTeamMember.challenge_id == Challenge.id)
            .where(
                ChallengeTeamMember.slack_id == slack_id
            )
            .options(
                joinedload(Challenge.challenge_type),
            )
            .order_by(desc(Challenge.challenge_started_at))
        )
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())


class ChallengeTeamMemberRepository(BaseRepository[ChallengeTeamMember]):
    model = ChallengeTeamMember


class ChallengeJuryMemberRepository(BaseRepository[ChallengeJuryMember]):
    model = ChallengeJuryMember


