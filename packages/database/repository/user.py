from __future__ import annotations

from packages.database.models.user import User, UserRole, UserSession
from packages.database.repository.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User


class UserRoleRepository(BaseRepository[UserRole]):
    model = UserRole


class UserSessionRepository(BaseRepository[UserSession]):
    model = UserSession
