from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Episode, JobType, ProcessingJob

router = APIRouter(tags=["history"])


class ProcessingJobResponse(BaseModel):
    id: str
    episode_id: str
    episode_title: str
    podcast_id: str
    job_type: str
    celery_task_id: Optional[str]
    triggered_by: str
    device_used: Optional[str]
    whisper_model_used: Optional[str]
    llm_model_used: Optional[str]
    duration_seconds: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[ProcessingJobResponse]


@router.get("/history", response_model=HistoryResponse)
def list_history(
    podcast_id: Optional[str] = None,
    job_type: Optional[JobType] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
):
    query = (
        db.query(ProcessingJob)
        .join(Episode, ProcessingJob.episode_id == Episode.id)
        .order_by(ProcessingJob.created_at.desc())
    )
    if podcast_id:
        query = query.filter(Episode.podcast_id == podcast_id)
    if job_type:
        query = query.filter(ProcessingJob.job_type == job_type)

    total = query.count()
    jobs = query.offset((page - 1) * per_page).limit(per_page).all()

    items = []
    for job in jobs:
        items.append(
            ProcessingJobResponse(
                id=job.id,
                episode_id=job.episode_id,
                episode_title=job.episode.title if job.episode else "",
                podcast_id=job.episode.podcast_id if job.episode else "",
                job_type=job.job_type,
                celery_task_id=job.celery_task_id,
                triggered_by=job.triggered_by,
                device_used=job.device_used,
                whisper_model_used=job.whisper_model_used,
                llm_model_used=job.llm_model_used,
                duration_seconds=job.duration_seconds,
                created_at=job.created_at,
                completed_at=job.completed_at,
            )
        )

    return HistoryResponse(total=total, page=page, per_page=per_page, items=items)
