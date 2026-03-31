from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData, String
from sqlalchemy.orm import DeclarativeBase, declared_attr, mapped_column

# Tutarlı constraint isimleri — autogenerate'in yanlış diff üretmesini önler.
_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=_NAMING_CONVENTION)


class IDMixin:
    __prefix__ = "GEN"

    @declared_attr
    def id(cls):
        prefix = getattr(cls, "__prefix__", cls.__prefix__)
        return mapped_column(String(60), primary_key=True, default=lambda: f"{prefix}-{uuid.uuid4()}")


class TimestampMixin:
    created_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
