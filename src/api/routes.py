"""Rutas de la API"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
import uuid
import sys
import asyncio
import json
from pathlib import Path
from typing import List
import os
from datetime import datetime
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.models import DownloadRequest, VideoInfo
from src.services import DownloaderService
from src.services.downloader import download_progress, downloads_to_cancel
from src.config import DOWNLOADS_DIR

router = APIRouter(prefix="/api", tags=["download"])
downloader = DownloaderService()

class DownloadFile(BaseModel):
    filename: str
    size: str
    created_at: str
    path: str
    type: str  # 'video' or 'audio'

@router.get("/scan", response_model=VideoInfo)
async def scan_video(url: str):
    """
    Obtiene información del video.
    
    Args:
        url: URL del video
        
    Returns:
        VideoInfo: Información del video
    """
    try:
        return downloader.get_video_info(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/downloads", response_model=List[DownloadFile])
async def list_downloads():
    files = []
    # Ensure directory exists
    downloads_path = Path(DOWNLOADS_DIR)
    if not downloads_path.exists():
        return []

    for f in downloads_path.glob('*'):
        if f.is_file():
            # Get basic info
            size_mb = f.stat().st_size / (1024 * 1024)
            created = datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            
            # Determine type
            ext = f.suffix.lower()
            if ext in ['.mp4', '.mkv', '.webm']:
                f_type = 'video'
            elif ext in ['.mp3', '.m4a', '.wav']:
                f_type = 'audio'
            else:
                f_type = 'file'

            files.append(DownloadFile(
                filename=f.name,
                size=f"{size_mb:.1f} MB",
                created_at=created,
                path=str(f),
                type=f_type
            ))
    
    # Sort by newest first
    files.sort(key=lambda x: x.created_at, reverse=True)
    return files

class DownloadStartResponse(BaseModel):
    download_id: str
    message: str

# Almacén temporal de descargas completadas
download_results: dict = {}

def run_download_task(download_id: str, request: DownloadRequest):
    """Ejecuta la descarga en segundo plano"""
    try:
        file_path, filename = downloader.download(
            url=request.url,
            format_type=request.format,
            unique_id=download_id,
            start_time=request.start_time,
            end_time=request.end_time,
            quality=request.quality,
            audio_quality=request.audio_quality
        )
        download_results[download_id] = {
            'file_path': str(file_path),
            'filename': filename
        }
    except Exception as e:
        download_progress[download_id] = {
            'status': 'error',
            'error': str(e),
            'percent': 0
        }

@router.post("/download/start", response_model=DownloadStartResponse)
async def start_download(request: DownloadRequest, background_tasks: BackgroundTasks):
    """
    Inicia una descarga en segundo plano.
    """
    download_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(run_download_task, download_id, request)
    return DownloadStartResponse(download_id=download_id, message="Descarga iniciada")

@router.get("/download/progress/{download_id}")
async def get_download_progress(download_id: str):
    """
    Obtiene el progreso de una descarga.
    """
    progress = download_progress.get(download_id, {'status': 'unknown', 'percent': 0})
    return progress

@router.post("/download/cancel/{download_id}")
async def cancel_download(download_id: str):
    """
    Cancela una descarga en progreso.
    """
    progress = download_progress.get(download_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Descarga no encontrada")
    
    if progress.get('status') in ['completed', 'error', 'cancelled']:
        return {"message": "La descarga ya ha terminado", "cancelled": False}
    
    # Marcar para cancelar
    downloads_to_cancel.add(download_id)
    return {"message": "Descarga cancelada", "cancelled": True}

@router.get("/download/file/{download_id}")
async def get_download_file(download_id: str):
    """
    Obtiene el archivo descargado una vez completada la descarga.
    """
    result = download_results.get(download_id)
    if not result:
        raise HTTPException(status_code=404, detail="Descarga no encontrada")
    
    file_path = Path(result['file_path'])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        path=file_path,
        filename=result['filename'],
        media_type='application/octet-stream'
    )

@router.post("/download")
async def download_video(request: DownloadRequest):
    """
    Descarga un video o audio de YouTube.
    
    Args:
        request: Datos de la solicitud de descarga
        
    Returns:
        FileResponse: Archivo descargado
        
    Raises:
        HTTPException: Si ocurre un error durante la descarga
    """
    try:
        unique_id = str(uuid.uuid4())[:8]
        file_path, filename = downloader.download(
            url=request.url,
            format_type=request.format,
            unique_id=unique_id,
            start_time=request.start_time,
            end_time=request.end_time,
            quality=request.quality
        )
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class OpenFolderRequest(BaseModel):
    path: str

@router.post("/open-folder")
async def open_folder(request: OpenFolderRequest):
    try:
        path = os.path.normpath(request.path)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        # Windows command to select file in explorer
        # Using shell=True might help with window focus slightly, but it's Windows managed.
        import subprocess
        cmd = f'explorer /select,"{path}"'
        subprocess.Popen(cmd, shell=True)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
