from __future__ import annotations

import logging
from logging import Logger
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from packages.settings import get_settings


_s = get_settings()


class DatabaseManager:
    def __init__(self, logger: Logger) -> None:
        self._logger = logger
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None

    def _create_database_url(self) -> str:
        return f"postgresql+asyncpg://{_s.username}:{_s.password}@{_s.host}:{_s.port}/{_s.database}"

    def initilaze(self) -> None:
        if self._engine is not None:
            self._logger.warning("DatabaseManager already initialized")
            return
            
        self._engine = create_async_engine(
            self._create_database_url(),
            echo=False,
            pool_size=_s.db_pool_size,
            max_overflow=_s.db_max_overflow,
            pool_timeout=_s.db_pool_timeout,
            pool_pre_ping=_s.db_pool_pre_ping,
            pool_recycle=_s.db_pool_recycle,
        )

        self._sessionmaker = async_sessionmaker(
            bind=self._engine, 
            expire_on_commit=False, 
            autoflush=False, 
            class_=AsyncSession,
        )

        self._logger.info("SqlAlchemy Engine & Sessionmaker initialized")

    @asynccontextmanager
    async def session(self, read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
        if self._sessionmaker is None:
            self._logger.error("DatabaseManager not initialized. Call initilaze() first.")
            raise RuntimeError("DatabaseManager not initialized. Call initilaze() first.")

        async with self._sessionmaker() as session:
            try: 
                if read_only:
                    yield session
                else:
                    async with session.begin():
                        yield session
            except Exception as e:
                self._logger.error(f"Error in session: {e}")
                await session.rollback()
                raise

    async def shutdown(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
        self._sessionmaker = None
        self._logger.info("SqlAlchemy Engine & Sessionmaker shutdown")


db = DatabaseManager(logging.getLogger("packages.database"))
