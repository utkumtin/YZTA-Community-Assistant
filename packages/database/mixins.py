from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, declared_attr, mapped_column


class Base(DeclarativeBase):
    pass


class IDMixin:
    __prefix__ = "GEN"

    @declared_attr
    def id(cls):
        prefix = getattr(cls, "__prefix__", cls.__prefix__)
        return mapped_column(String(60), primary_key=True, default=lambda: f"{prefix}-{uuid.uuid4()}")


class TimestampMixin:
    created_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
