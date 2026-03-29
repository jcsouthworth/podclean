import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (
    AdHandling,
    AppSettings,
    DeviceMode,
    LLMBackend,
    ReviewMode,
    TranscriptionBackend,
    WhisperModel,
)

router = APIRouter(tags=["settings"])


class SettingsResponse(BaseModel):
    device_mode: str
    anthropic_api_key: Optional[str]
    ollama_base_url: str
    app_base_url: str
    feed_poll_schedule: str
    default_transcription_backend: str
    default_whisper_model: str
    default_llm_backend: str
    default_llm_model: str
    default_ad_confidence_threshold: float
    default_review_mode: str
    default_ad_handling: str
    default_max_episodes: int
    default_keep_original_audio: bool

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    device_mode: Optional[DeviceMode] = None
    anthropic_api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None
    app_base_url: Optional[str] = None
    feed_poll_schedule: Optional[str] = None
    default_transcription_backend: Optional[TranscriptionBackend] = None
    default_whisper_model: Optional[WhisperModel] = None
    default_llm_backend: Optional[LLMBackend] = None
    default_llm_model: Optional[str] = None
    default_ad_confidence_threshold: Optional[float] = None
    default_review_mode: Optional[ReviewMode] = None
    default_ad_handling: Optional[AdHandling] = None
    default_max_episodes: Optional[int] = None
    default_keep_original_audio: Optional[bool] = None


def _get_settings(db: Session) -> AppSettings:
    settings = db.get(AppSettings, 1)
    if not settings:
        raise HTTPException(status_code=500, detail="App settings not initialised")
    return settings


@router.get("/settings/ollama-models")
async def list_ollama_models(db: Session = Depends(get_db)):
    """Return the list of models currently installed in Ollama."""
    settings = db.get(AppSettings, 1)
    base_url = settings.ollama_base_url if settings else os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url.rstrip('/')}/api/tags")
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return {"models": models}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Could not reach Ollama: {exc}")


@router.get("/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    return _get_settings(db)


@router.patch("/settings", response_model=SettingsResponse)
def update_settings(body: SettingsUpdate, db: Session = Depends(get_db)):
    settings = _get_settings(db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return settings
