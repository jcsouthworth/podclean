import json
import logging
import os
import re
import time
from datetime import datetime, timezone

import httpx
import redis as redis_lib

from celery_app import celery_app
from database import SessionLocal
from models import (
    AppSettings,
    DeviceUsed,
    Episode,
    EpisodeStatus,
    JobType,
    Podcast,
    ProcessingJob,
    TriggeredBy,
)

logger = logging.getLogger(__name__)

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "/data/podclean")
_redis = redis_lib.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))


def _set_progress(episode_id: str, stage: str, pct: int | None, started_at: float):
    try:
        _redis.setex(
            f"podclean:progress:{episode_id}",
            7200,
            json.dumps({
                "stage": stage,
                "pct": pct,
                "elapsed": int(time.time() - started_at),
            }),
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _get_db():
    return SessionLocal()


def _enum_val(value) -> str:
    """Extract string value from a str-enum or plain string."""
    return value.value if hasattr(value, "value") else str(value)


def _episode_dir(feed_slug: str, guid: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.\-]", "_", guid)
    if len(safe) > 100:
        import hashlib
        safe = hashlib.md5(guid.encode()).hexdigest()
    path = os.path.join(STORAGE_ROOT, feed_slug, safe)
    os.makedirs(path, exist_ok=True)
    return path


def _download_file(url: str, dest_path: str) -> None:
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with httpx.stream("GET", url, follow_redirects=True, timeout=600.0) as resp:
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=65536):
                f.write(chunk)


def _parse_itunes_duration(raw: str) -> int | None:
    """Parse itunes:duration string to milliseconds."""
    try:
        parts = str(raw).strip().split(":")
        if len(parts) == 1:
            return int(float(parts[0])) * 1000
        elif len(parts) == 2:
            return (int(parts[0]) * 60 + int(parts[1])) * 1000
        elif len(parts) == 3:
            return (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000
    except (ValueError, IndexError):
        pass
    return None


def _finalize_job(
    db,
    episode_id: str,
    start_time: datetime,
    device_used: str | None,
    whisper_model_used: str | None,
    llm_model_used: str | None,
) -> None:
    """Mark the most recent incomplete ProcessingJob for this episode as done."""
    job = (
        db.query(ProcessingJob)
        .filter(
            ProcessingJob.episode_id == episode_id,
            ProcessingJob.completed_at.is_(None),
        )
        .order_by(ProcessingJob.created_at.desc())
        .first()
    )
    if not job:
        return
    now = datetime.now(timezone.utc)
    job.completed_at = now
    job.duration_seconds = int((now - start_time).total_seconds())
    if device_used:
        job.device_used = DeviceUsed.cuda if device_used == "cuda" else DeviceUsed.cpu
    if whisper_model_used:
        job.whisper_model_used = whisper_model_used
    if llm_model_used:
        job.llm_model_used = llm_model_used
    db.commit()


def _run_audio_processing(ep: Episode, podcast: Podcast, db) -> None:
    """Stage 5: Audio processing. Status must already be processing_audio."""
    from tasks.audio import process_audio

    episode_dir = (
        os.path.dirname(ep.original_file)
        if ep.original_file
        else _episode_dir(podcast.feed_slug, ep.guid)
    )

    ad_handling = _enum_val(podcast.ad_handling)
    processed_path = process_audio(
        original_path=ep.original_file,
        episode_dir=episode_dir,
        ad_segments=ep.ad_segments or [],
        ad_handling=ad_handling,
    )

    ep.processed_file = processed_path
    ep.status = EpisodeStatus.complete
    ep.processed_at = datetime.now(timezone.utc)

    ep.ad_time_removed_ms = sum(
        int(s.get("end_ms", 0)) - int(s.get("start_ms", 0))
        for s in (ep.ad_segments or [])
    )

    db.commit()


def _run_storage_management(ep: Episode, podcast: Podcast, db) -> None:
    """Stage 6: Delete original if keep_original_audio=False; enforce max_episodes."""
    if not podcast.keep_original_audio:
        if ep.original_file and os.path.exists(ep.original_file):
            try:
                os.unlink(ep.original_file)
            except OSError as exc:
                logger.warning("Could not delete original file %s: %s", ep.original_file, exc)

    max_ep = podcast.max_episodes
    if max_ep and max_ep > 0:
        complete_eps = (
            db.query(Episode)
            .filter(
                Episode.podcast_id == podcast.id,
                Episode.status == EpisodeStatus.complete,
            )
            .order_by(Episode.published_at.asc())
            .all()
        )
        while len(complete_eps) > max_ep:
            oldest = complete_eps.pop(0)
            for attr in ("original_file", "processed_file", "transcript_file"):
                path = getattr(oldest, attr)
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except OSError as exc:
                        logger.warning("Could not delete %s: %s", path, exc)
        db.commit()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@celery_app.task(name="tasks.pipeline.poll_feeds")
def poll_feeds():
    """Stage 1: Poll all enabled podcast RSS feeds for new episodes."""
    import feedparser

    db = _get_db()
    try:
        podcasts = db.query(Podcast).filter(Podcast.enabled.is_(True)).all()
        for podcast in podcasts:
            try:
                _poll_single_feed(podcast, db)
            except Exception:
                logger.exception("Error polling feed for podcast %s", podcast.id)
    finally:
        db.close()


def _poll_single_feed(podcast: Podcast, db) -> None:
    import feedparser

    feed = feedparser.parse(podcast.rss_url)
    if not feed.entries:
        podcast.last_checked_at = datetime.now(timezone.utc)
        db.commit()
        return

    existing_guids: set[str] = {
        row[0]
        for row in db.query(Episode.guid).filter(Episode.podcast_id == podcast.id)
    }
    is_first_poll = len(existing_guids) == 0

    # Sort newest-first so index 0 is the most recent episode
    entries = sorted(
        feed.entries,
        key=lambda e: getattr(e, "published_parsed", None) or time.gmtime(0),
        reverse=True,
    )

    new_pending: list[Episode] = []

    for i, entry in enumerate(entries):
        guid = entry.get("id") or entry.get("guid") or entry.get("link")
        if not guid or guid in existing_guids:
            continue

        # Find audio enclosure
        source_url: str | None = None
        for enc in entry.get("enclosures", []):
            if enc.get("type", "").startswith("audio"):
                source_url = enc.get("href") or enc.get("url")
                break
        if not source_url:
            continue

        published_at: datetime | None = None
        if getattr(entry, "published_parsed", None):
            published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

        duration_ms: int | None = None
        raw_dur = entry.get("itunes_duration") or getattr(entry, "itunes_duration", None)
        if raw_dur:
            duration_ms = _parse_itunes_duration(str(raw_dur))

        if is_first_poll:
            status = EpisodeStatus.pending if i == 0 else EpisodeStatus.skipped
        else:
            status = EpisodeStatus.pending

        ep = Episode(
            podcast_id=podcast.id,
            guid=guid,
            title=entry.get("title", "Untitled"),
            published_at=published_at,
            source_url=source_url,
            duration_ms=duration_ms,
            status=status,
        )
        db.add(ep)
        db.flush()

        if status == EpisodeStatus.pending:
            new_pending.append(ep)

    podcast.last_checked_at = datetime.now(timezone.utc)
    db.commit()

    for ep in new_pending:
        job = ProcessingJob(
            episode_id=ep.id,
            job_type=JobType.full,
            triggered_by=TriggeredBy.schedule,
        )
        db.add(job)
        db.commit()

        result = process_episode.delay(ep.id)
        job.celery_task_id = result.id
        db.commit()


@celery_app.task(name="tasks.pipeline.process_episode")
def process_episode(episode_id: str):
    """Full processing pipeline: download → transcribe → classify → audio → storage."""
    db = _get_db()
    start_time = datetime.now(timezone.utc)
    device_used: str = "cpu"
    whisper_model_used: str | None = None
    llm_model_used: str | None = None

    try:
        ep = db.get(Episode, episode_id)
        if not ep:
            logger.error("Episode %s not found", episode_id)
            return

        podcast = db.get(Podcast, ep.podcast_id)
        settings = db.get(AppSettings, 1)

        # ----------------------------------------------------------------
        # Stage 2: Download
        # ----------------------------------------------------------------
        ep.status = EpisodeStatus.downloading
        db.commit()

        episode_dir = _episode_dir(podcast.feed_slug, ep.guid)
        original_path = os.path.join(episode_dir, "original.mp3")

        if not os.path.exists(original_path):
            logger.info("Downloading %s", ep.source_url)
            _download_file(ep.source_url, original_path)

        ep.original_file = original_path
        db.commit()

        # ----------------------------------------------------------------
        # Stage 3: Transcription
        # ----------------------------------------------------------------
        ep.status = EpisodeStatus.transcribing
        db.commit()

        from tasks.transcribe import transcribe_audio

        device_mode = _enum_val(settings.device_mode) if settings else "auto"
        whisper_model = _enum_val(podcast.whisper_model)
        whisper_model_used = whisper_model

        transcribe_start = time.time()
        total_secs = (ep.duration_ms / 1000) if ep.duration_ms else 0

        def _transcribe_progress(current_secs, total):
            pct = min(99, int(current_secs / total * 100)) if total else None
            _set_progress(episode_id, "transcribing", pct, transcribe_start)

        _set_progress(episode_id, "transcribing", 0, transcribe_start)
        transcript_path, word_count, device_used = transcribe_audio(
            audio_path=original_path,
            whisper_model=whisper_model,
            device_mode=device_mode,
            episode_dir=episode_dir,
            progress_callback=_transcribe_progress,
            total_duration_secs=total_secs,
        )
        ep.transcript_file = transcript_path
        ep.transcript_word_count = word_count
        db.commit()

        # ----------------------------------------------------------------
        # Stage 4: Ad classification
        # ----------------------------------------------------------------
        ep.status = EpisodeStatus.classifying
        db.commit()

        classify_start = time.time()
        _set_progress(episode_id, "classifying", None, classify_start)

        from tasks.classify import classify_ads

        llm_backend = _enum_val(podcast.llm_backend)
        llm_model = podcast.llm_model
        llm_model_used = llm_model
        ollama_url = settings.ollama_base_url if settings else "http://ollama:11434"
        api_key = settings.anthropic_api_key if settings else None

        ad_segments = classify_ads(
            transcript_path=transcript_path,
            llm_backend=llm_backend,
            llm_model=llm_model,
            confidence_threshold=podcast.ad_confidence_threshold,
            ollama_base_url=ollama_url,
            anthropic_api_key=api_key,
        )
        ep.ad_segments = ad_segments
        db.commit()

        # ----------------------------------------------------------------
        # Review mode branching
        # ----------------------------------------------------------------
        review_mode = _enum_val(podcast.review_mode)
        if review_mode == "before_audio":
            ep.status = EpisodeStatus.awaiting_review
            db.commit()
            _finalize_job(db, episode_id, start_time, device_used, whisper_model_used, llm_model_used)
            return

        # ----------------------------------------------------------------
        # Stage 5: Audio processing
        # ----------------------------------------------------------------
        ep.status = EpisodeStatus.processing_audio
        db.commit()

        _run_audio_processing(ep, podcast, db)

        # ----------------------------------------------------------------
        # Stage 6: Storage management
        # ----------------------------------------------------------------
        _run_storage_management(ep, podcast, db)

        _finalize_job(db, episode_id, start_time, device_used, whisper_model_used, llm_model_used)

    except Exception:
        logger.exception("Fatal error processing episode %s", episode_id)
        db.rollback()
        try:
            ep = db.get(Episode, episode_id)
            if ep:
                import traceback
                ep.status = EpisodeStatus.failed
                ep.error_message = traceback.format_exc()[-1000:]
                db.commit()
        except Exception:
            logger.exception("Could not set failed status for episode %s", episode_id)
    finally:
        db.close()


@celery_app.task(name="tasks.pipeline.reaudio_episode")
def reaudio_episode(episode_id: str):
    """Re-run Stage 5 (audio processing) only. Episode status is already processing_audio."""
    db = _get_db()
    start_time = datetime.now(timezone.utc)

    try:
        ep = db.get(Episode, episode_id)
        if not ep:
            logger.error("Episode %s not found", episode_id)
            return

        podcast = db.get(Podcast, ep.podcast_id)

        # Status is already processing_audio — set by the approve endpoint
        _run_audio_processing(ep, podcast, db)
        _run_storage_management(ep, podcast, db)
        _finalize_job(db, episode_id, start_time, device_used="cpu",
                      whisper_model_used=None, llm_model_used=None)

    except Exception:
        logger.exception("Fatal error in reaudio for episode %s", episode_id)
        db.rollback()
        try:
            ep = db.get(Episode, episode_id)
            if ep:
                import traceback
                ep.status = EpisodeStatus.failed
                ep.error_message = traceback.format_exc()[-1000:]
                db.commit()
        except Exception:
            logger.exception("Could not set failed status for episode %s", episode_id)
    finally:
        db.close()
