import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models  # noqa: F401 — ensures all models are registered with Base
from database import init_db
from routers import health, podcasts, episodes, feeds, settings, history, backup, gpu

app = FastAPI(title="PodClean API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(podcasts.router, prefix="/api")
app.include_router(episodes.router, prefix="/api")
app.include_router(feeds.router)
app.include_router(settings.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(backup.router, prefix="/api")
app.include_router(gpu.router, prefix="/api")


@app.on_event("startup")
def on_startup():
    os.makedirs(os.getenv("STORAGE_ROOT", "/data/podclean"), exist_ok=True)
    init_db()
