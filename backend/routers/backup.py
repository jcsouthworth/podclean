from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import Response

from services.backup import create_backup, restore_backup

router = APIRouter(tags=["backup"])


@router.get("/settings/backup")
def download_backup():
    """Download a zip archive containing podclean.db and .env."""
    try:
        data = create_backup()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backup failed: {exc}")
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="podclean-backup.zip"',
        },
    )


@router.post("/settings/restore")
async def upload_restore(file: UploadFile):
    """
    Restore from a backup zip.  Replaces the database and .env in place.
    Restart the service after restoring for the new .env to take effect.
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload must be a .zip file")
    data = await file.read()
    try:
        restore_backup(data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Restore failed: {exc}")
    return {
        "status": "restored",
        "message": "Restart the service for .env changes to take effect.",
    }
