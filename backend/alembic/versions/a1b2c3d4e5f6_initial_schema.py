"""initial schema

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-03-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "podcasts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("rss_url", sa.String(), nullable=False),
        sa.Column("rss_url_history", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("transcription_backend", sa.String(), nullable=False),
        sa.Column("whisper_model", sa.String(), nullable=False),
        sa.Column("llm_backend", sa.String(), nullable=False),
        sa.Column("llm_model", sa.String(), nullable=False),
        sa.Column("ad_confidence_threshold", sa.Float(), nullable=False),
        sa.Column("review_mode", sa.String(), nullable=False),
        sa.Column("ad_handling", sa.String(), nullable=False),
        sa.Column("max_episodes", sa.Integer(), nullable=False),
        sa.Column("keep_original_audio", sa.Boolean(), nullable=False),
        sa.Column("feed_slug", sa.String(), nullable=False),
        sa.UniqueConstraint("feed_slug", name="uq_podcasts_feed_slug"),
    )

    op.create_table(
        "episodes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "podcast_id",
            sa.String(36),
            sa.ForeignKey("podcasts.id"),
            nullable=False,
        ),
        sa.Column("guid", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column("source_rss_entry", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("original_file", sa.String(), nullable=True),
        sa.Column("processed_file", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("review_approved_at", sa.DateTime(), nullable=True),
        sa.Column("transcript_file", sa.String(), nullable=True),
        sa.Column("transcript_word_count", sa.Integer(), nullable=True),
        sa.Column("ad_segments", sa.JSON(), nullable=False),
        sa.Column("ad_time_removed_ms", sa.Integer(), nullable=True),
    )

    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "episode_id",
            sa.String(36),
            sa.ForeignKey("episodes.id"),
            nullable=False,
        ),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("celery_task_id", sa.String(), nullable=True),
        sa.Column("triggered_by", sa.String(), nullable=False),
        sa.Column("device_used", sa.String(), nullable=True),
        sa.Column("whisper_model_used", sa.String(), nullable=True),
        sa.Column("llm_model_used", sa.String(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_mode", sa.String(), nullable=False),
        sa.Column("anthropic_api_key", sa.String(), nullable=True),
        sa.Column("ollama_base_url", sa.String(), nullable=False),
        sa.Column("app_base_url", sa.String(), nullable=False),
        sa.Column("feed_poll_schedule", sa.String(), nullable=False),
        sa.Column("default_transcription_backend", sa.String(), nullable=False),
        sa.Column("default_whisper_model", sa.String(), nullable=False),
        sa.Column("default_llm_backend", sa.String(), nullable=False),
        sa.Column("default_llm_model", sa.String(), nullable=False),
        sa.Column("default_ad_confidence_threshold", sa.Float(), nullable=False),
        sa.Column("default_review_mode", sa.String(), nullable=False),
        sa.Column("default_ad_handling", sa.String(), nullable=False),
        sa.Column("default_max_episodes", sa.Integer(), nullable=False),
        sa.Column("default_keep_original_audio", sa.Boolean(), nullable=False),
    )

    # Seed the singleton settings row with defaults
    op.execute(
        """
        INSERT INTO app_settings (
            id, device_mode, anthropic_api_key, ollama_base_url, app_base_url,
            feed_poll_schedule,
            default_transcription_backend, default_whisper_model,
            default_llm_backend, default_llm_model,
            default_ad_confidence_threshold, default_review_mode,
            default_ad_handling, default_max_episodes,
            default_keep_original_audio
        ) VALUES (
            1, 'auto', NULL, 'http://ollama:11434', 'http://localhost:8000',
            '*/30 * * * *',
            'local', 'small',
            'local', 'llama3',
            0.7, 'none',
            'chapters', 10,
            1
        )
        """
    )


def downgrade() -> None:
    op.drop_table("processing_jobs")
    op.drop_table("episodes")
    op.drop_table("podcasts")
    op.drop_table("app_settings")
