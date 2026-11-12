"""SQLAlchemy repository implementation for UserRepository port."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vocara.domain.entities import User
from vocara.domain.ports import UserRepository
from vocara.infrastructure.db.models.user import UserModel
from vocara.infrastructure.db.repositories.base import BaseRepository


class SqlUserRepository(BaseRepository[UserModel], UserRepository):
    """Repository adapter implementing UserRepository against PostgreSQL/SQLite."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserModel, session)

    def _to_entity(self, model: UserModel) -> User:
        """Map ORM model to pure domain User entity."""
        return User(
            id=model.id,
            email=model.email,
            name=model.name,
            avatar_url=model.avatar_url,
            password_hash=model.password_hash,
            google_sub=model.google_sub,
            plan=model.plan,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: User) -> UserModel:
        """Map domain User entity to ORM model."""
        return UserModel(
            id=entity.id,
            email=entity.email,
            name=entity.name,
            avatar_url=entity.avatar_url,
            password_hash=entity.password_hash,
            google_sub=entity.google_sub,
            plan=entity.plan,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_id(self, user_id: str) -> User | None:
        """Lookup user by UUID."""
        model = await self._get_model_by_id(user_id)
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        """Lookup user by normalized email."""
        query = select(UserModel).where(UserModel.email == email.strip().lower())
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_google_sub(self, google_sub: str) -> User | None:
        """Lookup user by Google OpenID subject identifier."""
        query = select(UserModel).where(UserModel.google_sub == google_sub)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def create(self, user: User) -> User:
        """Persist a new user account."""
        model = self._to_model(user)
        created = await self._create_model(model)
        return self._to_entity(created)

    async def update(self, user: User) -> User:
        """Update an existing user account."""
        model = await self._get_model_by_id(user.id)
        if not model:
            return await self.create(user)
        model.email = user.email
        model.name = user.name
        model.avatar_url = user.avatar_url
        model.password_hash = user.password_hash
        model.google_sub = user.google_sub
        model.plan = user.plan
        model.is_active = user.is_active
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

