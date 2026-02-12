from datetime import datetime
from pathlib import Path
import logging
import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.services.file_processor import NFSFTFileProcessor, PisaFTFileProcessor


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/process-file")
async def process_file(file: UploadFile = File(...)):
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato file non valido. Formati supportati: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    file_id = str(uuid.uuid4())
    upload_path = settings.UPLOAD_DIR / f"{file_id}_input{file_ext}"
    output_path = settings.OUTPUT_DIR / f"{file_id}_output.xlsx"

    try:
        with upload_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = upload_path.stat().st_size
        if file_size > settings.MAX_FILE_SIZE:
            upload_path.unlink()
            raise HTTPException(
                status_code=400,
                detail=f"File troppo grande. Dimensione massima: {settings.MAX_FILE_SIZE / 1024 / 1024:.0f}MB",
            )

        processor = NFSFTFileProcessor()
        stats = processor.process_file(upload_path, output_path)

        upload_path.unlink()

        return {
            "success": True,
            "file_id": file_id,
            "summary": stats,
            "download_url": f"/api/download/{file_id}",
        }
    except ValueError as exc:
        if upload_path.exists():
            upload_path.unlink()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Errore elaborazione: %s", str(exc))
        if upload_path.exists():
            upload_path.unlink()
        if output_path.exists():
            output_path.unlink()
        raise HTTPException(status_code=500, detail="Errore durante l'elaborazione del file")


@router.post("/process-file-pisa")
async def process_file_pisa(file: UploadFile = File(...)):
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato file non valido. Formati supportati: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    file_id = str(uuid.uuid4())
    upload_path = settings.UPLOAD_DIR / f"{file_id}_input{file_ext}"
    output_path = settings.OUTPUT_DIR / f"{file_id}_output.xlsx"

    try:
        with upload_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = upload_path.stat().st_size
        if file_size > settings.MAX_FILE_SIZE:
            upload_path.unlink()
            raise HTTPException(
                status_code=400,
                detail=f"File troppo grande. Dimensione massima: {settings.MAX_FILE_SIZE / 1024 / 1024:.0f}MB",
            )

        processor = PisaFTFileProcessor()
        stats = processor.process_file(upload_path, output_path)

        upload_path.unlink()

        return {
            "success": True,
            "file_id": file_id,
            "summary": stats,
            "download_url": f"/api/download/{file_id}",
        }
    except ValueError as exc:
        if upload_path.exists():
            upload_path.unlink()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Errore elaborazione Pisa Pagato: %s", str(exc))
        if upload_path.exists():
            upload_path.unlink()
        if output_path.exists():
            output_path.unlink()
        raise HTTPException(status_code=500, detail="Errore durante l'elaborazione del file")


@router.get("/download/{file_id}")
async def download_file(file_id: str):
    output_path = settings.OUTPUT_DIR / f"{file_id}_output.xlsx"

    if not output_path.exists():
        raise HTTPException(status_code=404, detail="File non trovato o scaduto")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"File_Riepilogativo_NFS_FT_{timestamp}.xlsx"

    return FileResponse(
        path=output_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "NFS/FT File Processor"}
