import os
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models import AppSettings, Episode, EpisodeStatus, Podcast
from services.rss import generate_feed_xml

router = APIRouter(tags=["feeds"])

_RANGE_RE = re.compile(r"bytes=(\d+)-(\d*)")


def _stream_audio(file_path: str, request: Request):
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")

    if range_header:
        m = _RANGE_RE.match(range_header)
        if m:
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else file_size - 1
        else:
            start, end = 0, file_size - 1
        start = max(0, start)
        end = min(file_size - 1, end)
        content_length = end - start + 1

        def _iter():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return StreamingResponse(
            _iter(),
            status_code=206,
            media_type="audio/mpeg",
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length),
                "Accept-Ranges": "bytes",
            },
        )

    def _iter_full():
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        _iter_full(),
        media_type="audio/mpeg",
        headers={
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
        },
    )


@router.get("/feeds/{feed_slug}/rss.xml")
def get_feed(feed_slug: str, db: Session = Depends(get_db)):
    podcast = db.query(Podcast).filter(Podcast.feed_slug == feed_slug).first()
    if not podcast:
        raise HTTPException(status_code=404, detail="Feed not found")

    episodes = (
        db.query(Episode)
        .filter(
            Episode.podcast_id == podcast.id,
            Episode.status == EpisodeStatus.complete,
        )
        .order_by(Episode.published_at.desc())
        .all()
    )

    settings = db.get(AppSettings, 1)
    app_base_url = settings.app_base_url if settings else "http://localhost:8000"

    xml = generate_feed_xml(podcast, episodes, app_base_url)
    return Response(content=xml, media_type="application/rss+xml; charset=utf-8")


@router.get("/feeds/{feed_slug}/episodes/{episode_id}/audio.mp3")
def stream_audio(
    feed_slug: str,
    episode_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    podcast = db.query(Podcast).filter(Podcast.feed_slug == feed_slug).first()
    if not podcast:
        raise HTTPException(status_code=404, detail="Feed not found")

    ep = db.get(Episode, episode_id)
    if not ep or ep.podcast_id != podcast.id:
        raise HTTPException(status_code=404, detail="Episode not found")

    if not ep.processed_file or not os.path.exists(ep.processed_file):
        raise HTTPException(status_code=404, detail="Audio file not available")

    return _stream_audio(ep.processed_file, request)
