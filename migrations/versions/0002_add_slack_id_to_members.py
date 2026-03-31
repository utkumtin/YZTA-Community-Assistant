"""add slack_id column to challenge_team_members and challenge_jury_members

Önceki şemada slack_id, meta JSONB alanı içinde {"slack_id": "..."} olarak
saklanıyordu. Bu migration:
  1. Her iki tabloya String(32) slack_id kolonu ekler.
  2. Mevcut meta verisinden backfill yapar.
  3. İndeksleri oluşturur.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-01 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # challenge_team_members — slack_id kolonu ekle
    # ------------------------------------------------------------------
    op.add_column(
        "challenge_team_members",
        sa.Column("slack_id", sa.String(32), nullable=True),
    )
    op.create_index(
        "ix_challenge_team_members_slack_id",
        "challenge_team_members",
        ["slack_id"],
    )

    # ------------------------------------------------------------------
    # challenge_jury_members — slack_id kolonu ekle
    # ------------------------------------------------------------------
    op.add_column(
        "challenge_jury_members",
        sa.Column("slack_id", sa.String(32), nullable=True),
    )
    op.create_index(
        "ix_challenge_jury_members_slack_id",
        "challenge_jury_members",
        ["slack_id"],
    )

    # ------------------------------------------------------------------
    # Backfill: meta->>'slack_id'  →  slack_id kolonu
    # ------------------------------------------------------------------
    op.execute(
        """
        UPDATE challenge_team_members
        SET    slack_id = meta->>'slack_id'
        WHERE  meta IS NOT NULL
          AND  meta->>'slack_id' IS NOT NULL
          AND  slack_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE challenge_jury_members
        SET    slack_id = meta->>'slack_id'
        WHERE  meta IS NOT NULL
          AND  meta->>'slack_id' IS NOT NULL
          AND  slack_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_challenge_jury_members_slack_id", "challenge_jury_members")
    op.drop_column("challenge_jury_members", "slack_id")

    op.drop_index("ix_challenge_team_members_slack_id", "challenge_team_members")
    op.drop_column("challenge_team_members", "slack_id")
