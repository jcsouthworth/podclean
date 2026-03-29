import os
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import (
    AdHandling,
    AppSettings,
    Episode,
    EpisodeStatus,
    LLMBackend,
    Podcast,
    ReviewMode,
    TranscriptionBackend,
    WhisperModel,
)
from services.rss import fetch_podcast_metadata, slugify
from tasks.pipeline import poll_feeds

router = APIRouter(tags=["podcasts"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unique_slug(name: str, db: Session) -> str:
    base = slugify(name) or "podcast"
    slug = base
    counter = 1
    while db.query(Podcast).filter(Podcast.feed_slug == slug).first():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def _episode_counts(podcast: Podcast) -> dict:
    counts: dict[str, int] = {s.value: 0 for s in EpisodeStatus}
    for ep in podcast.episodes:
        counts[ep.status] = counts.get(ep.status, 0) + 1
    return counts


def _feed_url(podcast: Podcast, app_base_url: str) -> str:
    return f"{app_base_url.rstrip('/')}/feeds/{podcast.feed_slug}/rss.xml"


def _app_base_url(db: Session) -> str:
    settings = db.get(AppSettings, 1)
    return settings.app_base_url if settings else "http://localhost:8000"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PodcastCreate(BaseModel):
    rss_url: str
    name: Optional[str] = None
    transcription_backend: Optional[TranscriptionBackend] = None
    whisper_model: Optional[WhisperModel] = None
    llm_backend: Optional[LLMBackend] = None
    llm_model: Optional[str] = None
    ad_confidence_threshold: Optional[float] = None
    review_mode: Optional[ReviewMode] = None
    ad_handling: Optional[AdHandling] = None
    max_episodes: Optional[int] = None
    keep_original_audio: Optional[bool] = None


class PodcastUpdate(BaseModel):
    name: Optional[str] = None
    rss_url: Optional[str] = None
    enabled: Optional[bool] = None
    transcription_backend: Optional[TranscriptionBackend] = None
    whisper_model: Optional[WhisperModel] = None
    llm_backend: Optional[LLMBackend] = None
    llm_model: Optional[str] = None
    ad_confidence_threshold: Optional[float] = None
    review_mode: Optional[ReviewMode] = None
    ad_handling: Optional[AdHandling] = None
    max_episodes: Optional[int] = None
    keep_original_audio: Optional[bool] = None


class PodcastResponse(BaseModel):
    id: str
    name: str
    rss_url: str
    rss_url_history: list
    enabled: bool
    created_at: datetime
    last_checked_at: Optional[datetime]
    transcription_backend: str
    whisper_model: str
    llm_backend: str
    llm_model: str
    ad_confidence_threshold: float
    review_mode: str
    ad_handling: str
    max_episodes: int
    keep_original_audio: bool
    feed_slug: str
    feed_url: str
    episode_counts: dict
    artwork_url: Optional[str]
    description: Optional[str]
    author: Optional[str]

    model_config = {"from_attributes": True}


def _podcast_response(podcast: Podcast, db: Session) -> PodcastResponse:
    base_url = _app_base_url(db)
    return PodcastResponse(
        id=podcast.id,
        name=podcast.name,
        rss_url=podcast.rss_url,
        rss_url_history=podcast.rss_url_history or [],
        enabled=podcast.enabled,
        created_at=podcast.created_at,
        last_checked_at=podcast.last_checked_at,
        transcription_backend=podcast.transcription_backend,
        whisper_model=podcast.whisper_model,
        llm_backend=podcast.llm_backend,
        llm_model=podcast.llm_model,
        ad_confidence_threshold=podcast.ad_confidence_threshold,
        review_mode=podcast.review_mode,
        ad_handling=podcast.ad_handling,
        max_episodes=podcast.max_episodes,
        keep_original_audio=podcast.keep_original_audio,
        feed_slug=podcast.feed_slug,
        feed_url=_feed_url(podcast, base_url),
        episode_counts=_episode_counts(podcast),
        artwork_url=podcast.artwork_url,
        description=podcast.description,
        author=podcast.author,
    )


# ---------------------------------------------------------------------------
# Podcast CRUD
# ---------------------------------------------------------------------------


@router.get("/podcasts", response_model=list[PodcastResponse])
def list_podcasts(db: Session = Depends(get_db)):
    podcasts = db.query(Podcast).order_by(Podcast.created_at).all()
    return [_podcast_response(p, db) for p in podcasts]


@router.post("/podcasts", response_model=PodcastResponse, status_code=201)
def create_podcast(body: PodcastCreate, db: Session = Depends(get_db)):
    # Fetch RSS metadata if name not provided
    meta = fetch_podcast_metadata(body.rss_url)
    name = body.name or meta["name"]
    artwork_url = meta.get("artwork")
    description = meta.get("description")
    author = meta.get("author")

    settings = db.get(AppSettings, 1)

    podcast = Podcast(
        name=name,
        rss_url=body.rss_url,
        rss_url_history=[],
        feed_slug=_unique_slug(name, db),
        artwork_url=artwork_url,
        description=description,
        author=author,
        transcription_backend=body.transcription_backend
        or (settings.default_transcription_backend if settings else TranscriptionBackend.local),
        whisper_model=body.whisper_model
        or (settings.default_whisper_model if settings else WhisperModel.small),
        llm_backend=body.llm_backend
        or (settings.default_llm_backend if settings else LLMBackend.local),
        llm_model=body.llm_model
        or (settings.default_llm_model if settings else "llama3"),
        ad_confidence_threshold=body.ad_confidence_threshold
        or (settings.default_ad_confidence_threshold if settings else 0.7),
        review_mode=body.review_mode
        or (settings.default_review_mode if settings else ReviewMode.none),
        ad_handling=body.ad_handling
        or (settings.default_ad_handling if settings else AdHandling.chapters),
        max_episodes=body.max_episodes
        or (settings.default_max_episodes if settings else 10),
        keep_original_audio=body.keep_original_audio
        if body.keep_original_audio is not None
        else (settings.default_keep_original_audio if settings else True),
    )
    db.add(podcast)
    db.commit()
    db.refresh(podcast)

    # Kick off an immediate feed poll so episodes are discovered right away
    poll_feeds.delay()

    return _podcast_response(podcast, db)


@router.get("/podcasts/{podcast_id}", response_model=PodcastResponse)
def get_podcast(podcast_id: str, db: Session = Depends(get_db)):
    podcast = db.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    return _podcast_response(podcast, db)


@router.patch("/podcasts/{podcast_id}", response_model=PodcastResponse)
def update_podcast(podcast_id: str, body: PodcastUpdate, db: Session = Depends(get_db)):
    podcast = db.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")

    data = body.model_dump(exclude_unset=True)

    # RSS URL rotation — preserve history before overwriting
    if "rss_url" in data and data["rss_url"] != podcast.rss_url:
        history = list(podcast.rss_url_history or [])
        history.append(
            {
                "url": podcast.rss_url,
                "replaced_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        podcast.rss_url_history = history

    for field, value in data.items():
        setattr(podcast, field, value)

    db.commit()
    db.refresh(podcast)
    return _podcast_response(podcast, db)


@router.delete("/podcasts/{podcast_id}", status_code=204)
def delete_podcast(podcast_id: str, db: Session = Depends(get_db)):
    podcast = db.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    db.delete(podcast)
    db.commit()


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


@router.post("/podcasts/poll")
def trigger_poll():
    """Manually trigger a full RSS feed poll across all enabled podcasts."""
    poll_feeds.delay()
    return {"status": "queued"}


@router.post("/podcasts/{podcast_id}/refresh-metadata", response_model=PodcastResponse)
def refresh_metadata(podcast_id: str, db: Session = Depends(get_db)):
    """Re-fetch artwork, description, and author from the source RSS feed."""
    podcast = db.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    meta = fetch_podcast_metadata(podcast.rss_url)
    podcast.artwork_url = meta.get("artwork")
    podcast.description = meta.get("description")
    podcast.author = meta.get("author")
    db.commit()
    db.refresh(podcast)
    return _podcast_response(podcast, db)


@router.post("/podcasts/{podcast_id}/purge-transcripts")
def purge_transcripts(podcast_id: str, db: Session = Depends(get_db)):
    """Delete transcript JSON files on disk and null transcript_file for all episodes."""
    podcast = db.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")

    purged = 0
    for ep in podcast.episodes:
        if ep.transcript_file and os.path.exists(ep.transcript_file):
            try:
                os.unlink(ep.transcript_file)
                purged += 1
            except OSError:
                pass
        ep.transcript_file = None

    db.commit()
    return {"purged": purged}


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/podcasts/{podcast_id}/stats")
def podcast_stats(podcast_id: str, db: Session = Depends(get_db)):
    podcast = db.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")

    total_ms = (
        db.query(func.sum(Episode.ad_time_removed_ms))
        .filter(
            Episode.podcast_id == podcast_id,
            Episode.ad_time_removed_ms.isnot(None),
        )
        .scalar()
        or 0
    )

    return {
        "podcast_id": podcast_id,
        "total_ms": total_ms,
        "formatted": _format_ms(total_ms),
    }


@router.get("/stats/time-saved")
def sitewide_time_saved(db: Session = Depends(get_db)):
    total_ms = (
        db.query(func.sum(Episode.ad_time_removed_ms))
        .filter(Episode.ad_time_removed_ms.isnot(None))
        .scalar()
        or 0
    )
    return {"total_ms": total_ms, "formatted": _format_ms(total_ms)}


def _format_ms(ms: int) -> str:
    total_seconds = ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
