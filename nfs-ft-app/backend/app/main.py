import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


app = FastAPI(
    title="1. Query Fatture NFS API",
    description="API per elaborazione file Excel 1. Query Fatture NFS",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", tags=["files"])


@app.get("/")
async def root():
    return {
        "message": "1. Query Fatture NFS API",
        "version": "1.0.0",
        "docs": "/docs",
    }
