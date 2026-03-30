from __future__ import annotations

from typing import Generic, Type, TypeVar, Sequence

from sqlalchemy import func, select, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    model: Type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- READ ----------------------------------------------------------

    async def get(self, id: str) -> ModelT | None:
        return await self.session.get(self.model, id)

    async def get_all(self) -> Sequence[ModelT]:
        result = await self.session.execute(select(self.model))
        return result.scalars().all()

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()

    # ---- WRITE ----------------------------------------------------------

    async def create(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()  # ID vs al
        return entity

    async def update(self, entity: ModelT) -> ModelT:
        # SQLAlchemy zaten tracked entity'yi update eder
        await self.session.flush()
        return entity

    async def delete(self, id: str) -> bool:
        result = await self.session.execute(sql_delete(self.model).where(self.model.id == id))
        return result.rowcount > 0