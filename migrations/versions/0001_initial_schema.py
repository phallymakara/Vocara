"""Initial schema migration for Vocara.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-30 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. API Keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("hashed_secret", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("char_quota_per_month", sa.Integer(), nullable=False, server_default="100000"),
        sa.Column("chars_used_this_month", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])
    op.create_index("ix_api_keys_owner_id", "api_keys", ["owner_id"])

    # 2. Voices table
    op.create_table(
        "voices",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("voice_type", sa.String(length=20), nullable=False, server_default="cloned"),
        sa.Column("owner_id", sa.String(length=64), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="km-KH"),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("reference_audio_key", sa.String(length=255), nullable=True),
        sa.Column("preview_audio_key", sa.String(length=255), nullable=True),
        sa.Column("modifiers", sa.JSON(), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False, server_default="private"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_voices_owner_id", "voices", ["owner_id"])

    # 3. Jobs table
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("job_type", sa.String(length=30), nullable=False, server_default="tts_batch"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("voice_id", sa.String(length=36), nullable=True),
        sa.Column("input_text", sa.Text(), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="km-KH"),
        sa.Column("speed", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("output_format", sa.String(length=10), nullable=False, server_default="mp3"),
        sa.Column("output_audio_key", sa.String(length=255), nullable=True),
        sa.Column("audio_duration_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_jobs_owner_id", "jobs", ["owner_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    # 4. Usage Records table
    op.create_table(
        "usage_records",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("api_key_id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("operation", sa.String(length=50), nullable=False),
        sa.Column("characters_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_usage_records_api_key_id", "usage_records", ["api_key_id"])
    op.create_index("ix_usage_records_owner_id", "usage_records", ["owner_id"])

    # 5. Webhooks table
    op.create_table(
        "webhooks",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column("secret", sa.String(length=64), nullable=False),
        sa.Column("event_types", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_webhooks_owner_id", "webhooks", ["owner_id"])


def downgrade() -> None:
    op.drop_table("webhooks")
    op.drop_table("usage_records")
    op.drop_table("jobs")
    op.drop_table("voices")
    op.drop_table("api_keys")
