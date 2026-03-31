"""Alembic async environment — settings'ten URL alır, tüm modelleri yükler."""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Tüm ORM modellerini metadata'ya kaydetmek için base import ediyoruz.
from packages.database.models.base import Base

config = context.config
target_metadata = Base.metadata

if config.config_file_name:
    fileConfig(config.config_file_name)


def _build_url() -> str:
    """
    DB URL'ini şu sırayla arar:
      1. DATABASE_URL  env var (CI/CD için tek satır bağlantı)
      2. packages.settings üzerinden (tam .env gerektirir)
      3. POSTGRES_* env varları (template formatı)
    """
    # 1. Hazır URL
    if url := os.getenv("DATABASE_URL"):
        # asyncpg driver'ı zorunlu
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # 2. Ana settings (tüm .env dolu ise)
    try:
        from packages.settings import get_settings
        s = get_settings()
        return (
            f"postgresql+asyncpg://{s.username}:{s.password}"
            f"@{s.host}:{s.port}/{s.database}"
        )
    except Exception:
        pass

    # 3. POSTGRES_* env varları (template formatı)
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ["POSTGRES_DB"]
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


# ---------------------------------------------------------------------------
# Offline mode — SQL script üretir, DB'ye bağlanmaz
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    context.configure(
        url=_build_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode — gerçek async bağlantıyla çalışır
# ---------------------------------------------------------------------------

def _do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    engine = create_async_engine(_build_url(), echo=False)
    async with engine.connect() as conn:
        await conn.run_sync(_do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
