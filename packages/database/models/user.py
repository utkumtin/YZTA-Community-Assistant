from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.database.mixins import Base, IDMixin, TimestampMixin


class User(Base, IDMixin, TimestampMixin):
    __tablename__ = "users"
    __prefix__ = "USR"

    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[str] = mapped_column(String(60), ForeignKey("user_roles.id"), nullable=False, index=True)

    role: Mapped["UserRole"] = relationship("UserRole", back_populates="users")
    sessions: Mapped[list["UserSession"]] = relationship("UserSession", back_populates="user")


class UserRole(Base, IDMixin, TimestampMixin):
    __tablename__ = "user_roles"
    __prefix__ = "UR"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    permissions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)

    users: Mapped[list["User"]] = relationship("User", back_populates="role")


class UserSession(Base, IDMixin, TimestampMixin):
    __tablename__ = "user_sessions"
    __prefix__ = "US"

    user_id: Mapped[str] = mapped_column(String(60), ForeignKey("users.id"), nullable=False, index=True)
    access_jti: Mapped[str] = mapped_column(String(60), nullable=False, unique=True, index=True)
    access_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    access_token_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    access_token_revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="sessions")