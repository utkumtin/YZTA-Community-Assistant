"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_challenge_category = sa.Enum(
    "learn", "practice", "real_world", "no_code_low_code",
    name="challengecategory",
)
_challenge_status = sa.Enum(
    "not_started", "started", "completed", "not_completed",
    "in_evaluation", "evaluated", "evaluation_delayed",
    name="challengestatus",
)


def upgrade() -> None:
    # ------------------------------------------------------------------
    # user_roles
    # ------------------------------------------------------------------
    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(60), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("permissions", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_roles"),
    )
    # unique=True + index=True → SQLAlchemy tek UniqueIndex üretir (ix_ prefix)
    op.create_index("ix_user_roles_name", "user_roles", ["name"], unique=True)

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.String(60), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("role_id", sa.String(60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["user_roles.id"],
                                name="fk_users_role_id_user_roles"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role_id", "users", ["role_id"])

    # ------------------------------------------------------------------
    # user_sessions
    # ------------------------------------------------------------------
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(60), nullable=False),
        sa.Column("user_id", sa.String(60), nullable=False),
        sa.Column("access_jti", sa.String(60), nullable=False),
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("access_token_revoked", sa.Boolean, nullable=False),
        sa.Column("access_token_revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],
                                name="fk_user_sessions_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_user_sessions"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_access_jti", "user_sessions", ["access_jti"], unique=True)

    # ------------------------------------------------------------------
    # slack_users
    # ------------------------------------------------------------------
    op.create_table(
        "slack_users",
        sa.Column("id", sa.String(60), nullable=False),
        sa.Column("slack_id", sa.String(32), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("real_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("is_bot", sa.Boolean, nullable=False),
        sa.Column("is_deleted", sa.Boolean, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.Column("slack_joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_slack_users"),
    )
    op.create_index("ix_slack_users_slack_id", "slack_users", ["slack_id"], unique=True)

    # ------------------------------------------------------------------
    # challenge_types
    # ------------------------------------------------------------------
    op.create_table(
        "challenge_types",
        sa.Column("id", sa.String(60), nullable=False),
        sa.Column("category", _challenge_category, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("deadline_hours", sa.Integer, nullable=True),
        sa.Column("checklist", JSONB, nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_challenge_types"),
    )
    op.create_index("ix_challenge_types_category", "challenge_types", ["category"])

    # ------------------------------------------------------------------
    # challenges
    # ------------------------------------------------------------------
    op.create_table(
        "challenges",
        sa.Column("id", sa.String(60), nullable=False),
        sa.Column("challenge_type_id", sa.String(60), nullable=True),
        sa.Column("creator_slack_id", sa.String(32), nullable=False),
        sa.Column("status", _challenge_status, nullable=False),
        sa.Column("challenge_channel_id", sa.String(32), nullable=True),
        sa.Column("challenge_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("challenge_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evaluation_channel_id", sa.String(32), nullable=True),
        sa.Column("evaluation_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evaluation_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evaluation_results", sa.Boolean, nullable=False),
        sa.Column("evaluation_score", sa.Float, nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["challenge_type_id"], ["challenge_types.id"],
                                name="fk_challenges_challenge_type_id_challenge_types"),
        sa.PrimaryKeyConstraint("id", name="pk_challenges"),
    )
    op.create_index("ix_challenges_challenge_type_id", "challenges", ["challenge_type_id"])
    op.create_index("ix_challenges_creator_slack_id", "challenges", ["creator_slack_id"])
    op.create_index("ix_challenges_status", "challenges", ["status"])

    # ------------------------------------------------------------------
    # challenge_team_members
    # ------------------------------------------------------------------
    op.create_table(
        "challenge_team_members",
        sa.Column("id", sa.String(60), nullable=False),
        sa.Column("challenge_id", sa.String(60), nullable=False),
        sa.Column("user_id", sa.String(60), nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"],
                                name="fk_challenge_team_members_challenge_id_challenges"),
        sa.ForeignKeyConstraint(["user_id"], ["slack_users.id"],
                                name="fk_challenge_team_members_user_id_slack_users"),
        sa.PrimaryKeyConstraint("id", name="pk_challenge_team_members"),
    )
    op.create_index("ix_challenge_team_members_challenge_id", "challenge_team_members", ["challenge_id"])
    op.create_index("ix_challenge_team_members_user_id", "challenge_team_members", ["user_id"])

    # ------------------------------------------------------------------
    # challenge_jury_members
    # ------------------------------------------------------------------
    op.create_table(
        "challenge_jury_members",
        sa.Column("id", sa.String(60), nullable=False),
        sa.Column("challenge_id", sa.String(60), nullable=False),
        sa.Column("user_id", sa.String(60), nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"],
                                name="fk_challenge_jury_members_challenge_id_challenges"),
        sa.ForeignKeyConstraint(["user_id"], ["slack_users.id"],
                                name="fk_challenge_jury_members_user_id_slack_users"),
        sa.PrimaryKeyConstraint("id", name="pk_challenge_jury_members"),
    )
    op.create_index("ix_challenge_jury_members_challenge_id", "challenge_jury_members", ["challenge_id"])
    op.create_index("ix_challenge_jury_members_user_id", "challenge_jury_members", ["user_id"])


def downgrade() -> None:
    op.drop_table("challenge_jury_members")
    op.drop_table("challenge_team_members")
    op.drop_table("challenges")
    op.drop_table("challenge_types")
    op.drop_table("slack_users")
    op.drop_table("user_sessions")
    op.drop_table("users")
    op.drop_table("user_roles")
    # Enum tipleri tablolar silindikten sonra ayrıca düşürülmeli
    _challenge_status.drop(op.get_bind(), checkfirst=True)
    _challenge_category.drop(op.get_bind(), checkfirst=True)
