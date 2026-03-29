"""DB + .env zip export and import.

The .env file is mounted into the container at /app/.env (see docker-compose.yml).
The database lives at STORAGE_ROOT/podclean.db.
"""
import io
import os
import zipfile

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "/data/podclean")
DB_PATH = os.path.join(STORAGE_ROOT, "podclean.db")
ENV_FILE_PATH = os.getenv("ENV_FILE_PATH", "/app/.env")


def create_backup() -> bytes:
    """Return a zip archive containing podclean.db and .env."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(DB_PATH):
            zf.write(DB_PATH, "podclean.db")
        if os.path.exists(ENV_FILE_PATH):
            zf.write(ENV_FILE_PATH, ".env")
    buf.seek(0)
    return buf.read()


def restore_backup(data: bytes) -> None:
    """
    Extract a backup zip, replacing the database and .env in place.

    After restoring, the caller should trigger a service restart so the
    application picks up the new .env values.
    """
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        if "podclean.db" in names:
            os.makedirs(STORAGE_ROOT, exist_ok=True)
            with zf.open("podclean.db") as src, open(DB_PATH, "wb") as dst:
                dst.write(src.read())
        if ".env" in names:
            env_dir = os.path.dirname(ENV_FILE_PATH)
            if env_dir:
                os.makedirs(env_dir, exist_ok=True)
            with zf.open(".env") as src, open(ENV_FILE_PATH, "wb") as dst:
                dst.write(src.read())
