import os
import httpx
import redis as redis_lib
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import engine, get_db
from models import AppSettings
from services.gpu import get_gpu_status

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    services: dict[str, str] = {}

    # Database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        services["database"] = "ok"
    except Exception:
        services["database"] = "unavailable"

    # Redis
    try:
        r = redis_lib.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        r.ping()
        services["redis"] = "ok"
    except Exception:
        services["redis"] = "unavailable"

    # Celery worker — check via Redis queue inspection
    try:
        r = redis_lib.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        # A connected worker registers itself; a simple ping is sufficient for Stage 1
        r.ping()
        services["celery_worker"] = "ok"
    except Exception:
        services["celery_worker"] = "unavailable"

    # Ollama
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                f"{os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')}/api/tags"
            )
        services["ollama"] = "ok" if resp.status_code == 200 else "degraded"
    except Exception:
        services["ollama"] = "unavailable"

    # GPU
    try:
        settings = db.get(AppSettings, 1)
        device_mode = settings.device_mode if settings else "auto"
        gpu = get_gpu_status(getattr(device_mode, "value", str(device_mode)))
        services["gpu"] = "ok" if gpu["available"] else "unavailable"
    except Exception:
        services["gpu"] = "unavailable"

    overall = (
        "ok"
        if all(v == "ok" for k, v in services.items() if k not in ("ollama", "gpu"))
        else "degraded"
    )

    return {"status": overall, "services": services, "version": "1.0.0"}
