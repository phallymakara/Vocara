"""SQLAlchemy repository implementation for VoiceRepository port."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from vocara.domain.entities import Voice
from vocara.domain.enums import VoiceType, VoiceVisibility
from vocara.domain.ports import VoiceRepository
from vocara.infrastructure.db.models.voice import VoiceModel
from vocara.infrastructure.db.repositories.base import BaseRepository


class SqlVoiceRepository(BaseRepository[VoiceModel], VoiceRepository):
    """Repository adapter implementing VoiceRepository."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VoiceModel, session)

    def _to_entity(self, model: VoiceModel) -> Voice:
        """Map ORM model to domain entity."""
        return Voice(
            id=model.id,
            name=model.name,
            voice_type=VoiceType(model.voice_type),
            owner_id=model.owner_id,
            language=model.language,
            description=model.description,
            reference_audio_key=model.reference_audio_key,
            preview_audio_key=model.preview_audio_key,
            modifiers=model.modifiers or {},
            visibility=VoiceVisibility(model.visibility),
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Voice) -> VoiceModel:
        """Map domain entity to ORM model."""
        return VoiceModel(
            id=entity.id,
            name=entity.name,
            voice_type=entity.voice_type.value,
            owner_id=entity.owner_id,
            language=entity.language,
            description=entity.description,
            reference_audio_key=entity.reference_audio_key,
            preview_audio_key=entity.preview_audio_key,
            modifiers=entity.modifiers,
            visibility=entity.visibility.value,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_id(self, voice_id: str) -> Voice | None:
        """Retrieve voice by UUID."""
        query = select(VoiceModel).where(
            VoiceModel.id == voice_id,
            VoiceModel.is_active.is_(True),
        )
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_accessible_voices(
        self, owner_id: str, skip: int = 0, limit: int = 50
    ) -> list[Voice]:
        """List built-in public voices and developer's own voices."""
        query = (
            select(VoiceModel)
            .where(
                VoiceModel.is_active.is_(True),
                or_(
                    VoiceModel.owner_id == owner_id,
                    VoiceModel.visibility == VoiceVisibility.PUBLIC.value,
                ),
            )
            .order_by(VoiceModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, voice: Voice) -> Voice:
        """Persist new voice."""
        model = self._to_model(voice)
        created_model = await self._create_model(model)
        return self._to_entity(created_model)

    async def update(self, voice: Voice) -> Voice:
        """Update existing voice attributes."""
        model = await self._get_model_by_id(voice.id)
        if not model:
            return await self.create(voice)

        model.name = voice.name
        model.description = voice.description
        model.visibility = voice.visibility.value
        model.modifiers = voice.modifiers
        model.preview_audio_key = voice.preview_audio_key
        model.reference_audio_key = voice.reference_audio_key
        model.is_active = voice.is_active

        updated_model = await self._update_model(model)
        return self._to_entity(updated_model)

    async def delete(self, voice_id: str) -> bool:
        """Soft-delete voice by setting is_active = False."""
        model = await self._get_model_by_id(voice_id)
        if not model:
            return False
        model.is_active = False
        await self._update_model(model)
        return True
