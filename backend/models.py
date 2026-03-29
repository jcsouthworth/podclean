import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, JSON,
    String, Text, ForeignKey, Enum,
)
from sqlalchemy.orm import relationship

from database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TranscriptionBackend(str, PyEnum):
    local = "local"
    cloud = "cloud"


class WhisperModel(str, PyEnum):
    tiny = "tiny"
    small = "small"
    medium = "medium"
    large = "large"


class LLMBackend(str, PyEnum):
    local = "local"
    cloud = "cloud"


class ReviewMode(str, PyEnum):
    before_audio = "before_audio"
    after_processing = "after_processing"
    none = "none"


class AdHandling(str, PyEnum):
    chapters = "chapters"
    splice = "splice"


class EpisodeStatus(str, PyEnum):
    pending = "pending"
    downloading = "downloading"
    transcribing = "transcribing"
    classifying = "classifying"
    awaiting_review = "awaiting_review"
    processing_audio = "processing_audio"
    complete = "complete"
    failed = "failed"
    skipped = "skipped"


class JobType(str, PyEnum):
    full = "full"
    retranscribe = "retranscribe"
    reclassify = "reclassify"
    reaudio = "reaudio"


class TriggeredBy(str, PyEnum):
    schedule = "schedule"
    manual = "manual"


class DeviceUsed(str, PyEnum):
    cpu = "cpu"
    cuda = "cuda"


class DeviceMode(str, PyEnum):
    auto = "auto"
    gpu_required = "gpu_required"
    cpu_only = "cpu_only"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Podcast(Base):
    __tablename__ = "podcasts"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    rss_url = Column(String, nullable=False)
    rss_url_history = Column(JSON, nullable=False, default=lambda: [])
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_checked_at = Column(DateTime, nullable=True)

    # Processing config
    transcription_backend = Column(
        Enum(TranscriptionBackend, native_enum=False),
        nullable=False, default=TranscriptionBackend.local,
    )
    whisper_model = Column(
        Enum(WhisperModel, native_enum=False),
        nullable=False, default=WhisperModel.small,
    )
    llm_backend = Column(
        Enum(LLMBackend, native_enum=False),
        nullable=False, default=LLMBackend.local,
    )
    llm_model = Column(String, nullable=False, default="llama3")
    ad_confidence_threshold = Column(Float, nullable=False, default=0.7)
    review_mode = Column(
        Enum(ReviewMode, native_enum=False),
        nullable=False, default=ReviewMode.none,
    )

    # Output config
    ad_handling = Column(
        Enum(AdHandling, native_enum=False),
        nullable=False, default=AdHandling.chapters,
    )
    max_episodes = Column(Integer, nullable=False, default=10)
    keep_original_audio = Column(Boolean, nullable=False, default=True)
    feed_slug = Column(String, nullable=False, unique=True)

    # Source feed metadata (copied from original RSS on creation)
    artwork_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    author = Column(String, nullable=True)

    # Relationships
    episodes = relationship(
        "Episode", back_populates="podcast", cascade="all, delete-orphan"
    )


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(String(36), primary_key=True, default=_uuid)
    podcast_id = Column(String(36), ForeignKey("podcasts.id"), nullable=False)
    guid = Column(String, nullable=False)
    title = Column(String, nullable=False)
    published_at = Column(DateTime, nullable=True)
    source_url = Column(String, nullable=False)
    source_rss_entry = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # File paths
    original_file = Column(String, nullable=True)
    processed_file = Column(String, nullable=True)

    # Processing state
    status = Column(
        Enum(EpisodeStatus, native_enum=False),
        nullable=False, default=EpisodeStatus.pending,
    )
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    review_approved_at = Column(DateTime, nullable=True)

    # Results
    transcript_file = Column(String, nullable=True)
    transcript_word_count = Column(Integer, nullable=True)
    ad_segments = Column(JSON, nullable=False, default=lambda: [])
    # Written once on first successful processing; never overwritten on reprocessing
    ad_time_removed_ms = Column(Integer, nullable=True)

    # Relationships
    podcast = relationship("Podcast", back_populates="episodes")
    processing_jobs = relationship(
        "ProcessingJob", back_populates="episode", cascade="all, delete-orphan"
    )


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(String(36), primary_key=True, default=_uuid)
    episode_id = Column(String(36), ForeignKey("episodes.id"), nullable=False)
    job_type = Column(Enum(JobType, native_enum=False), nullable=False)
    celery_task_id = Column(String, nullable=True)
    triggered_by = Column(Enum(TriggeredBy, native_enum=False), nullable=False)
    # Recorded at job completion
    device_used = Column(Enum(DeviceUsed, native_enum=False), nullable=True)
    whisper_model_used = Column(String, nullable=True)
    llm_model_used = Column(String, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    episode = relationship("Episode", back_populates="processing_jobs")


class AppSettings(Base):
    """Singleton settings row (id is always 1)."""

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, default=1)

    # Global device mode for all local AI processing
    device_mode = Column(
        Enum(DeviceMode, native_enum=False),
        nullable=False, default=DeviceMode.auto,
    )

    # External service config
    anthropic_api_key = Column(String, nullable=True)
    ollama_base_url = Column(String, nullable=False, default="http://ollama:11434")
    app_base_url = Column(String, nullable=False, default="http://localhost:8000")
    feed_poll_schedule = Column(String, nullable=False, default="*/30 * * * *")

    # Default values applied to newly added podcasts
    default_transcription_backend = Column(
        Enum(TranscriptionBackend, native_enum=False),
        nullable=False, default=TranscriptionBackend.local,
    )
    default_whisper_model = Column(
        Enum(WhisperModel, native_enum=False),
        nullable=False, default=WhisperModel.small,
    )
    default_llm_backend = Column(
        Enum(LLMBackend, native_enum=False),
        nullable=False, default=LLMBackend.local,
    )
    default_llm_model = Column(String, nullable=False, default="llama3")
    default_ad_confidence_threshold = Column(Float, nullable=False, default=0.7)
    default_review_mode = Column(
        Enum(ReviewMode, native_enum=False),
        nullable=False, default=ReviewMode.none,
    )
    default_ad_handling = Column(
        Enum(AdHandling, native_enum=False),
        nullable=False, default=AdHandling.chapters,
    )
    default_max_episodes = Column(Integer, nullable=False, default=10)
    default_keep_original_audio = Column(Boolean, nullable=False, default=True)
