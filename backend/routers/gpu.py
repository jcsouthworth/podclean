from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import AppSettings
from services.gpu import get_gpu_status

router = APIRouter(tags=["gpu"])


@router.get("/gpu/status")
def gpu_status(db: Session = Depends(get_db)):
    settings = db.get(AppSettings, 1)
    device_mode = settings.device_mode if settings else "auto"
    # DeviceMode is a str-enum; .value gives the plain string ("auto" etc.)
    return get_gpu_status(getattr(device_mode, "value", str(device_mode)))
