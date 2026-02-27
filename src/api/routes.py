"""Rutas de la API"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask
import uuid
import sys
import asyncio
import json
import shutil
from pathlib import Path
from typing import List
import os
from datetime import datetime
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.models import DownloadRequest, VideoInfo
from src.services import DownloaderService
from src.services.downloader import download_progress, downloads_to_cancel, conversion_progress
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

# @router.get("/downloads", response_model=List[DownloadFile])
# async def list_downloads():
#     files = []
#     # Ensure directory exists
#     downloads_path = Path(DOWNLOADS_DIR)
#     if not downloads_path.exists():
#         return []
# 
#     for f in downloads_path.glob('*'):
#         if f.is_file():
#             # Get basic info
#             size_mb = f.stat().st_size / (1024 * 1024)
#             created = datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
#             
#             # Determine type
#             ext = f.suffix.lower()
#             if ext in ['.mp4', '.mkv', '.webm']:
#                 f_type = 'video'
#             elif ext in ['.mp3', '.m4a', '.wav']:
#                 f_type = 'audio'
#             else:
#                 f_type = 'file'
# 
#             files.append(DownloadFile(
#                 filename=f.name,
#                 size=f"{size_mb:.1f} MB",
#                 created_at=created,
#                 path=str(f),
#                 type=f_type
#             ))
#     
#     # Sort by newest first
#     files.sort(key=lambda x: x.created_at, reverse=True)
#     return files

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

# class OpenFolderRequest(BaseModel):
#     path: str
# 
# @router.post("/open-folder")
# async def open_folder(request: OpenFolderRequest):
#     try:
#         path = os.path.normpath(request.path)
#         if not os.path.exists(path):
#             raise HTTPException(status_code=404, detail="Archivo no encontrado")
#         
#         # Windows command to select file in explorer
#         import subprocess
#         cmd = f'explorer /select,"{path}"'
#         subprocess.Popen(cmd, shell=True)
#         return {"status": "ok"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# H.264 CONVERSION ENDPOINTS
# =====================================================

# Almacén temporal de conversiones completadas
conversion_results: dict = {}

class ConvertRequest(BaseModel):
    filename: str

class ConvertStartResponse(BaseModel):
    convert_id: str
    message: str

def run_convert_task(convert_id: str, file_path: str):
    """Ejecuta la conversión en segundo plano"""
    try:
        output_path, output_name = downloader.convert_to_h264(
            file_path=file_path,
            convert_id=convert_id
        )
        conversion_results[convert_id] = {
            'input_path': str(file_path),
            'output_path': str(output_path),
            'output_name': output_name
        }
    except Exception as e:
        conversion_progress[convert_id] = {
            'status': 'error',
            'percent': 0,
            'error': str(e)
        }

@router.post("/upload-convert", response_model=ConvertStartResponse)
async def upload_and_convert(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Sube un archivo e inicia la conversión a H.264 en segundo plano.
    """
    valid_extensions = {'.mp4', '.webm', '.mkv', '.avi', '.mov'}
    ext = Path(file.filename).suffix.lower()
    
    if ext not in valid_extensions:
        raise HTTPException(status_code=400, detail="Formato de archivo no soportado")
        
    convert_id = str(uuid.uuid4())[:8]
    
    # Save the uploaded file to DOWNLOADS_DIR
    import re
    safe_name = re.sub(r'[^\w\s-]', '', Path(file.filename).stem).strip()
    save_filename = f"upload_{convert_id}_{safe_name}{ext}"
    file_path = Path(DOWNLOADS_DIR) / save_filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando archivo: {str(e)}")
    
    # Inicializar progreso
    conversion_progress[convert_id] = {
        'status': 'starting',
        'percent': 0,
        'message': 'Iniciando conversión...'
    }
    
    background_tasks.add_task(run_convert_task, convert_id, str(file_path))
    return ConvertStartResponse(convert_id=convert_id, message="Conversión iniciada")

@router.post("/convert", response_model=ConvertStartResponse)
async def start_conversion(request: ConvertRequest, background_tasks: BackgroundTasks):
    """
    Inicia una conversión a H.264 para un archivo local existente. (Mantener para test/compatibilidad remota)
    """
    file_path = Path(DOWNLOADS_DIR) / request.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    valid_extensions = {'.mp4', '.webm', '.mkv', '.avi', '.mov'}
    if file_path.suffix.lower() not in valid_extensions:
        raise HTTPException(status_code=400, detail="Formato de archivo no soportado")
    
    convert_id = str(uuid.uuid4())[:8]
    conversion_progress[convert_id] = {
        'status': 'starting',
        'percent': 0,
        'message': 'Iniciando conversión...'
    }
    background_tasks.add_task(run_convert_task, convert_id, str(file_path))
    return ConvertStartResponse(convert_id=convert_id, message="Conversión iniciada")

@router.get("/convert/progress/{convert_id}")
async def get_conversion_progress(convert_id: str):
    """
    Obtiene el progreso de una conversión.
    """
    progress = conversion_progress.get(convert_id, {'status': 'unknown', 'percent': 0})
    return progress

@router.get("/convert/download/{convert_id}")
async def download_conversion_file(convert_id: str):
    """
    Obtiene el archivo convertido pidiendo al navegador que lo descargue 
    formalmente y luego se auto-destruyen ambos archivos (entrada y salida).
    """
    result = conversion_results.get(convert_id)
    if not result:
        raise HTTPException(status_code=404, detail="Conversión no encontrada")
    
    output_path = Path(result['output_path'])
    input_path = Path(result.get('input_path', ''))
    
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Archivo convertido no encontrado")
        
    def cleanup_files():
        try:
            if input_path.exists():
                input_path.unlink()
        except: pass
        try:
            if output_path.exists():
                output_path.unlink()
        except: pass
        # Remover progreso para limpiar ram
        conversion_progress.pop(convert_id, None)
        conversion_results.pop(convert_id, None)

    return FileResponse(
        path=output_path,
        filename=result['output_name'],
        media_type='video/mp4',
        background=BackgroundTask(cleanup_files)
    )

@router.get("/convert/file/{convert_id}")
async def get_conversion_file(convert_id: str):
    """
    Mantiene la ruta local / file direct.
    """
    result = conversion_results.get(convert_id)
    if not result:
        raise HTTPException(status_code=404, detail="Conversión no encontrada")
    
    file_path = Path(result['output_path'])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        path=file_path,
        filename=result['output_name'],
        media_type='video/mp4'
    )
