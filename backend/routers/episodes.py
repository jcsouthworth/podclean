import json
import os
from datetime import datetime, timezone
from typing import Optional

import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from celery_app import celery_app
from database import get_db
from models import Episode, EpisodeStatus, JobType, ProcessingJob, TriggeredBy
from tasks.pipeline import process_episode, reaudio_episode

_redis = redis_lib.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

router = APIRouter(tags=["episodes"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AdSegment(BaseModel):
    start_ms: int
    end_ms: int
    confidence: float
    reason: str


class SegmentsUpdate(BaseModel):
    ad_segments: list[AdSegment]


class EpisodeResponse(BaseModel):
    id: str
    podcast_id: str
    guid: str
    title: str
    published_at: Optional[datetime]
    source_url: str
    duration_ms: Optional[int]
    original_file: Optional[str]
    processed_file: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]
    review_approved_at: Optional[datetime]
    transcript_file: Optional[str]
    transcript_word_count: Optional[int]
    ad_segments: list
    ad_time_removed_ms: Optional[int]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/episodes", response_model=list[EpisodeResponse])
def list_episodes(
    podcast_id: Optional[str] = None,
    status: Optional[EpisodeStatus] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Episode).order_by(Episode.published_at.desc())
    if podcast_id:
        query = query.filter(Episode.podcast_id == podcast_id)
    if status:
        query = query.filter(Episode.status == status)
    return query.offset((page - 1) * per_page).limit(per_page).all()


@router.get("/episodes/{episode_id}", response_model=EpisodeResponse)
def get_episode(episode_id: str, db: Session = Depends(get_db)):
    ep = db.get(Episode, episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return ep


@router.patch("/episodes/{episode_id}/segments", response_model=EpisodeResponse)
def update_segments(
    episode_id: str, body: SegmentsUpdate, db: Session = Depends(get_db)
):
    ep = db.get(Episode, episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    ep.ad_segments = [seg.model_dump() for seg in body.ad_segments]
    db.commit()
    db.refresh(ep)
    return ep


@router.post("/episodes/{episode_id}/approve", response_model=EpisodeResponse)
def approve_episode(episode_id: str, db: Session = Depends(get_db)):
    """
    Resume the pipeline after review.  Only valid when status=awaiting_review.
    Creates a reaudio ProcessingJob and enqueues it.
    """
    ep = db.get(Episode, episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    if ep.status != EpisodeStatus.awaiting_review:
        raise HTTPException(
            status_code=400,
            detail=f"Episode is not awaiting review (current status: {ep.status})",
        )

    ep.status = EpisodeStatus.processing_audio
    ep.review_approved_at = datetime.now(timezone.utc)

    job = ProcessingJob(
        episode_id=ep.id,
        job_type=JobType.reaudio,
        triggered_by=TriggeredBy.manual,
    )
    db.add(job)
    db.commit()
    db.refresh(ep)

    result = reaudio_episode.delay(ep.id)
    job.celery_task_id = result.id
    db.commit()

    db.refresh(ep)
    return ep


@router.get("/episodes/{episode_id}/progress")
def get_progress(episode_id: str, db: Session = Depends(get_db)):
    """Return live transcription/classification progress for an active episode."""
    ep = db.get(Episode, episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    try:
        raw = _redis.get(f"podclean:progress:{episode_id}")
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return {"stage": ep.status, "pct": None, "elapsed": None}


@router.get("/episodes/{episode_id}/transcript")
def get_transcript(episode_id: str, db: Session = Depends(get_db)):
    """Return the word-level transcript JSON array for an episode."""
    ep = db.get(Episode, episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    if not ep.transcript_file:
        raise HTTPException(status_code=404, detail="No transcript available for this episode")
    if not os.path.exists(ep.transcript_file):
        raise HTTPException(status_code=404, detail="Transcript file not found on disk")
    with open(ep.transcript_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/episodes/{episode_id}/cancel", response_model=EpisodeResponse)
def cancel_episode(episode_id: str, db: Session = Depends(get_db)):
    """Cancel an in-progress episode by revoking its Celery task and marking it failed."""
    ep = db.get(Episode, episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")

    active = {
        EpisodeStatus.pending,
        EpisodeStatus.downloading,
        EpisodeStatus.transcribing,
        EpisodeStatus.classifying,
        EpisodeStatus.processing_audio,
    }
    if ep.status not in active:
        raise HTTPException(
            status_code=400,
            detail=f"Episode is not in a cancellable state (status: {ep.status})",
        )

    # Revoke + terminate the most recent incomplete job's Celery task
    job = (
        db.query(ProcessingJob)
        .filter(
            ProcessingJob.episode_id == episode_id,
            ProcessingJob.completed_at.is_(None),
        )
        .order_by(ProcessingJob.created_at.desc())
        .first()
    )
    if job and job.celery_task_id:
        celery_app.control.revoke(job.celery_task_id, terminate=True, signal="SIGTERM")

    ep.status = EpisodeStatus.failed
    ep.error_message = "Cancelled by user"
    db.commit()
    db.refresh(ep)
    return ep


@router.post("/episodes/{episode_id}/reprocess", response_model=EpisodeResponse)
def reprocess_episode(episode_id: str, db: Session = Depends(get_db)):
    """Manually re-trigger full processing for an episode (any terminal status)."""
    ep = db.get(Episode, episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")

    terminal = {EpisodeStatus.complete, EpisodeStatus.failed, EpisodeStatus.skipped}
    if ep.status not in terminal:
        raise HTTPException(
            status_code=400,
            detail=f"Episode is already being processed (status: {ep.status})",
        )

    ep.status = EpisodeStatus.pending
    ep.error_message = None

    job = ProcessingJob(
        episode_id=ep.id,
        job_type=JobType.full,
        triggered_by=TriggeredBy.manual,
    )
    db.add(job)
    db.commit()
    db.refresh(ep)

    result = process_episode.delay(ep.id)
    job.celery_task_id = result.id
    db.commit()

    db.refresh(ep)
    return ep
