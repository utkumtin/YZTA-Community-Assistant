from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.mixins import Base, IDMixin, TimestampMixin


class SlackUser(Base, IDMixin, TimestampMixin):
    __tablename__ = "slack_users"
    __prefix__ = "SLU"

    slack_id: Mapped[str] = mapped_column(String(32),unique=True,nullable=False,index=True,)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    real_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    slack_joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),nullable=True,comment="Slack çalışma alanına katılım (UTC); API senkronunda doldurulur.")
    
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)