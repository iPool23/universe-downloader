"""Rutas de la API"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask
import uuid
import sys
import asyncio
import json
import shutil
import time as _time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import os
from datetime import datetime
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.models import DownloadRequest, VideoInfo
from src.services import DownloaderService
from src.services.downloader import (
    download_progress, downloads_to_cancel, conversion_progress, audio_extract_progress, friendly_error,
)
from src.services import updater
from src.services.pdf_service import pdf_service, compress_progress
from src.config import DOWNLOADS_DIR, ENABLE_OUTPAINT, ENABLE_REMBG
from src.version import APP_NAME, APP_VERSION, UPDATES_REPO

router = APIRouter(prefix="/api", tags=["download"])
downloader = DownloaderService()

# =====================================================
# CACHÉ DE ESCANEO DE URLs (TTL de 5 minutos)
# =====================================================
_scan_cache: Dict[str, Tuple[float, dict]] = {}
_SCAN_CACHE_TTL = 300  # 5 minutos en segundos

def _get_cached_scan(url: str):
    """Retorna resultado cacheado si existe y no ha expirado."""
    entry = _scan_cache.get(url)
    if entry:
        timestamp, data = entry
        if _time.time() - timestamp < _SCAN_CACHE_TTL:
            return data
        else:
            del _scan_cache[url]  # Expirado
    return None

def _set_cached_scan(url: str, data: dict):
    """Almacena resultado de escaneo en caché."""
    _scan_cache[url] = (_time.time(), data)
    # Limpiar entradas expiradas si hay muchas
    if len(_scan_cache) > 100:
        now = _time.time()
        expired = [k for k, (t, _) in _scan_cache.items() if now - t >= _SCAN_CACHE_TTL]
        for k in expired:
            del _scan_cache[k]

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
    Usa caché para evitar re-escaneos y asyncio.to_thread()
    para no bloquear el event loop.
    
    Args:
        url: URL del video
        
    Returns:
        VideoInfo: Información del video
    """
    # 1. Verificar caché primero (instantáneo)
    cached = _get_cached_scan(url)
    if cached:
        return cached
    
    try:
        # 2. Ejecutar en hilo separado para no bloquear el event loop
        result = await asyncio.to_thread(downloader.get_video_info, url)
        # 3. Cachear resultado
        _set_cached_scan(url, result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=friendly_error(e))

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
            'error': friendly_error(e),
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
    Limpia los datos de progreso para evitar memory leaks.
    """
    result = download_results.get(download_id)
    if not result:
        raise HTTPException(status_code=404, detail="Descarga no encontrada")
    
    file_path = Path(result['file_path'])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    def cleanup_download_data():
        """Limpia datos de progreso/resultados en memoria Y el archivo en disco tras enviarlo —
        si no, cada video descargado se queda para siempre en el servidor (a diferencia de la
        conversión H.264 y las imágenes, que sí se autodestruyen)."""
        download_progress.pop(download_id, None)
        download_results.pop(download_id, None)
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass
    
    return FileResponse(
        path=file_path,
        filename=result['filename'],
        media_type='application/octet-stream',
        background=BackgroundTask(cleanup_download_data)
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
        except Exception: pass
        try:
            if output_path.exists():
                output_path.unlink()
        except Exception: pass
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


# =====================================================
# AUDIO EXTRACTION ENDPOINTS
# =====================================================

# Almacén temporal de extracciones completadas
audio_extract_results: dict = {}

class ExtractAudioStartResponse(BaseModel):
    extract_id: str
    message: str

def run_extract_audio_task(extract_id: str, file_path: str):
    """Ejecuta la extracción de audio en segundo plano"""
    try:
        output_path, output_name = downloader.extract_audio(
            file_path=file_path,
            extract_id=extract_id
        )
        audio_extract_results[extract_id] = {
            'input_path': str(file_path),
            'output_path': str(output_path),
            'output_name': output_name
        }
    except Exception as e:
        audio_extract_progress[extract_id] = {
            'status': 'error',
            'percent': 0,
            'error': str(e)
        }

@router.post("/upload-extract-audio", response_model=ExtractAudioStartResponse)
async def upload_and_extract_audio(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Sube un video e inicia la extracción de su audio a MP3 en segundo plano.
    """
    valid_extensions = {'.mp4', '.webm', '.mkv', '.avi', '.mov'}
    ext = Path(file.filename).suffix.lower()

    if ext not in valid_extensions:
        raise HTTPException(status_code=400, detail="Formato de archivo no soportado")

    extract_id = str(uuid.uuid4())[:8]

    import re
    safe_name = re.sub(r'[^\w\s-]', '', Path(file.filename).stem).strip()
    save_filename = f"upload_{extract_id}_{safe_name}{ext}"
    file_path = Path(DOWNLOADS_DIR) / save_filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando archivo: {str(e)}")

    audio_extract_progress[extract_id] = {
        'status': 'starting',
        'percent': 0,
        'message': 'Iniciando extracción...'
    }

    background_tasks.add_task(run_extract_audio_task, extract_id, str(file_path))
    return ExtractAudioStartResponse(extract_id=extract_id, message="Extracción iniciada")

@router.get("/extract-audio/progress/{extract_id}")
async def get_extract_audio_progress(extract_id: str):
    """
    Obtiene el progreso de una extracción de audio.
    """
    progress = audio_extract_progress.get(extract_id, {'status': 'unknown', 'percent': 0})
    return progress

@router.get("/extract-audio/download/{extract_id}")
async def download_extracted_audio(extract_id: str):
    """
    Obtiene el archivo de audio extraído y luego se auto-destruyen
    ambos archivos (video de entrada y audio de salida).
    """
    result = audio_extract_results.get(extract_id)
    if not result:
        raise HTTPException(status_code=404, detail="Extracción no encontrada")

    output_path = Path(result['output_path'])
    input_path = Path(result.get('input_path', ''))

    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Archivo de audio no encontrado")

    def cleanup_files():
        try:
            if input_path.exists():
                input_path.unlink()
        except Exception: pass
        try:
            if output_path.exists():
                output_path.unlink()
        except Exception: pass
        audio_extract_progress.pop(extract_id, None)
        audio_extract_results.pop(extract_id, None)

    return FileResponse(
        path=output_path,
        filename=result['output_name'],
        media_type='audio/mpeg',
        background=BackgroundTask(cleanup_files)
    )


# =====================================================
# IMAGE FORMAT CONVERSION ENDPOINT
# =====================================================

def _normalize_image_format(target_format: str) -> str:
    target_format = target_format.lower().strip()
    return 'jpg' if target_format == 'jpeg' else target_format


def _convert_image_file(input_path: Path, output_path: Path, target_format: str, quality: int, width: int, height: int) -> None:
    """Convierte una imagen ya guardada en disco. Usado por el endpoint de una imagen y el de lote,
    para no repetir la lógica de Pillow en dos lugares."""
    from PIL import Image

    img = Image.open(input_path)

    if width > 0 and height > 0:
        img = img.resize((width, height), Image.LANCZOS)
    elif width > 0:
        ratio = width / img.width
        img = img.resize((width, int(img.height * ratio)), Image.LANCZOS)
    elif height > 0:
        ratio = height / img.height
        img = img.resize((int(img.width * ratio), height), Image.LANCZOS)

    if target_format in ('jpg', 'jpeg'):
        if img.mode in ('RGBA', 'LA', 'PA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(str(output_path), 'JPEG', quality=quality, optimize=True)

    elif target_format == 'png':
        if img.mode == 'CMYK':
            img = img.convert('RGB')
        img.save(str(output_path), 'PNG', optimize=True)

    elif target_format == 'webp':
        img.save(str(output_path), 'WEBP', quality=quality, method=4)

    elif target_format == 'avif':
        if img.mode == 'CMYK':
            img = img.convert('RGB')
        img.save(str(output_path), 'AVIF', quality=quality)

    img.close()


@router.post("/convert-image")
async def convert_image(
    file: UploadFile = File(...),
    target_format: str = "webp",
    quality: int = 85,
    width: int = 0,
    height: int = 0
):
    """
    Convierte una imagen entre formatos: PNG, JPG, WebP, AVIF.
    Opcionalmente redimensiona la imagen.
    
    Args:
        file: Imagen a convertir
        target_format: Formato destino (png, jpg, webp, avif)
        quality: Calidad de compresión (10-100, solo para formatos lossy)
        width: Ancho deseado en píxeles (0 = mantener original)
        height: Alto deseado en píxeles (0 = mantener original)
    """
    valid_formats = {'png', 'jpg', 'jpeg', 'webp', 'avif'}
    target_format = _normalize_image_format(target_format)

    if target_format not in valid_formats:
        raise HTTPException(status_code=400, detail=f"Formato no soportado: {target_format}")
    
    # Validate input file extension
    input_ext = Path(file.filename).suffix.lower()
    valid_input_exts = {'.png', '.jpg', '.jpeg', '.webp', '.avif', '.bmp', '.tiff', '.tif'}
    if input_ext not in valid_input_exts:
        raise HTTPException(status_code=400, detail="Formato de imagen no soportado")
    
    # Clamp quality
    quality = max(10, min(100, quality))
    
    import uuid as _uuid
    convert_id = str(_uuid.uuid4())[:8]
    
    # Save uploaded file temporarily
    input_path = Path(DOWNLOADS_DIR) / f"img_input_{convert_id}{input_ext}"
    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando archivo: {str(e)}")
    
    # Convert with Pillow
    output_ext = 'jpg' if target_format == 'jpg' else target_format
    original_name = Path(file.filename).stem
    output_filename = f"{original_name}.{output_ext}"
    output_path = Path(DOWNLOADS_DIR) / f"img_output_{convert_id}.{output_ext}"
    
    try:
        _convert_image_file(input_path, output_path, target_format, quality, width, height)
    except Exception as e:
        # Cleanup on error
        if input_path.exists():
            input_path.unlink()
        if output_path.exists():
            output_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error convirtiendo imagen: {str(e)}")
    
    # Cleanup input file and schedule output cleanup after send
    def cleanup():
        try:
            if input_path.exists():
                input_path.unlink()
        except Exception:
            pass
        try:
            if output_path.exists():
                output_path.unlink()
        except Exception:
            pass
    
    # Determine media type
    media_types = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'webp': 'image/webp',
        'avif': 'image/avif',
    }
    
    return FileResponse(
        path=output_path,
        filename=output_filename,
        media_type=media_types.get(target_format, 'application/octet-stream'),
        background=BackgroundTask(cleanup)
    )


@router.post("/convert-images-batch")
async def convert_images_batch(
    files: List[UploadFile] = File(...),
    target_format: str = "webp",
    quality: int = 85,
    width: int = 0,
    height: int = 0
):
    """
    Convierte varias imágenes a la vez al mismo formato/calidad y las entrega juntas
    en un .zip. Las que fallan (formato corrupto, etc.) no detienen a las demás — se
    listan aparte en un manifiesto dentro del zip.
    """
    import zipfile

    valid_formats = {'png', 'jpg', 'jpeg', 'webp', 'avif'}
    target_format = _normalize_image_format(target_format)
    if target_format not in valid_formats:
        raise HTTPException(status_code=400, detail=f"Formato no soportado: {target_format}")
    if not files:
        raise HTTPException(status_code=400, detail="No se recibió ninguna imagen")

    quality = max(10, min(100, quality))
    valid_input_exts = {'.png', '.jpg', '.jpeg', '.webp', '.avif', '.bmp', '.tiff', '.tif'}
    output_ext = 'jpg' if target_format == 'jpg' else target_format

    batch_id = str(uuid.uuid4())[:8]
    temp_paths: List[Path] = []
    errors: List[str] = []
    used_names: Dict[str, int] = {}

    def unique_name(stem: str) -> str:
        name = f"{stem}.{output_ext}"
        count = used_names.get(name, 0)
        used_names[name] = count + 1
        return name if count == 0 else f"{stem}_{count}.{output_ext}"

    zip_path = Path(DOWNLOADS_DIR) / f"img_batch_{batch_id}.zip"
    success_count = 0
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, file in enumerate(files):
                input_ext = Path(file.filename or '').suffix.lower()
                if input_ext not in valid_input_exts:
                    errors.append(f"{file.filename}: formato de imagen no soportado")
                    continue

                input_path = Path(DOWNLOADS_DIR) / f"img_batch_{batch_id}_in_{i}{input_ext}"
                output_path = Path(DOWNLOADS_DIR) / f"img_batch_{batch_id}_out_{i}.{output_ext}"
                temp_paths.extend([input_path, output_path])
                try:
                    with open(input_path, "wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)
                    _convert_image_file(input_path, output_path, target_format, quality, width, height)
                    arcname = unique_name(Path(file.filename).stem)
                    zf.write(output_path, arcname=arcname)
                    success_count += 1
                except Exception as e:
                    errors.append(f"{file.filename}: {str(e)}")

            if errors:
                zf.writestr("errores.txt", "\n".join(errors))
    finally:
        for p in temp_paths:
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass

    if success_count == 0:
        zip_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Ninguna imagen se pudo convertir: " + "; ".join(errors))

    def cleanup():
        try:
            if zip_path.exists():
                zip_path.unlink()
        except Exception:
            pass

    return FileResponse(
        path=zip_path,
        filename="imagenes_convertidas.zip",
        media_type="application/zip",
        background=BackgroundTask(cleanup)
    )


# =====================================================
# OUTPAINTING (AI IMAGE EXPANSION) ENDPOINTS
# =====================================================

@router.get("/outpaint/status")
async def outpaint_status():
    """Verifica si la GPU está disponible y el modelo cargado."""
    if not ENABLE_OUTPAINT:
        raise HTTPException(status_code=404, detail="Outpainting no disponible en esta versión")

    try:
        from src.services.outpainting_service import outpainting_service
        gpu_info = outpainting_service.get_gpu_info()
        return {"status": "ok", "gpu": gpu_info}
    except ImportError:
        return {"status": "error", "message": "PyTorch not installed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/outpaint/load")
async def outpaint_load_model():
    """Carga el modelo SDXL Inpainting en la GPU (descarga ~7GB la primera vez)."""
    if not ENABLE_OUTPAINT:
        raise HTTPException(status_code=404, detail="Outpainting no disponible en esta versión")

    try:
        from src.services.outpainting_service import outpainting_service
        
        if not outpainting_service.is_available():
            raise HTTPException(status_code=400, detail="CUDA not available. GPU NVIDIA required.")
        
        if outpainting_service.is_loaded():
            return {"status": "ok", "message": "Model already loaded"}
        
        # Load in background thread to avoid blocking
        await asyncio.to_thread(outpainting_service.load_model)
        return {"status": "ok", "message": "Model loaded successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading model: {str(e)}")


@router.post("/outpaint/unload")
async def outpaint_unload_model():
    """Descarga el modelo de la GPU para liberar VRAM."""
    if not ENABLE_OUTPAINT:
        raise HTTPException(status_code=404, detail="Outpainting no disponible en esta versión")

    try:
        from src.services.outpainting_service import outpainting_service
        outpainting_service.unload_model()
        return {"status": "ok", "message": "Model unloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outpaint")
async def outpaint_image(
    file: UploadFile = File(...),
    direction: str = "all",
    pixels: int = 128,
    prompt: str = "",
    steps: int = 20,
    guidance: float = 7.5,
):
    """
    Expande una imagen usando IA (SDXL Inpainting outpainting).
    
    Args:
        file: Imagen a expandir
        direction: "up", "down", "left", "right", "all"
        pixels: Píxeles a expandir (32-512)
        prompt: Texto para guiar la generación (opcional)
        steps: Pasos de inferencia (15-50, default 20)
        guidance: Guidance scale (1-20, default 7.5)
    """
    if not ENABLE_OUTPAINT:
        raise HTTPException(status_code=404, detail="Outpainting no disponible en esta versión")

    from PIL import Image as PILImage
    import io
    
    try:
        from src.services.outpainting_service import outpainting_service
    except ImportError:
        raise HTTPException(status_code=500, detail="PyTorch/diffusers not installed")
    
    if not outpainting_service.is_available():
        raise HTTPException(status_code=400, detail="CUDA not available")
    
    # Validate direction
    valid_directions = {"up", "down", "left", "right", "all"}
    if direction not in valid_directions:
        raise HTTPException(status_code=400, detail=f"Invalid direction: {direction}")
    
    # Clamp values
    pixels = max(32, min(512, pixels))
    steps = max(15, min(50, steps))
    guidance = max(1.0, min(20.0, guidance))
    
    # Read uploaded image
    import uuid as _uuid
    op_id = str(_uuid.uuid4())[:8]
    input_path = Path(DOWNLOADS_DIR) / f"outpaint_input_{op_id}.png"
    
    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    try:
        # Open with PIL
        img = PILImage.open(input_path).convert("RGB")
        
        # Load model if needed
        if not outpainting_service.is_loaded():
            await asyncio.to_thread(outpainting_service.load_model)
        
        # Run outpainting in background thread
        result = await asyncio.to_thread(
            outpainting_service.expand,
            image=img,
            direction=direction,
            pixels=pixels,
            prompt=prompt,
            num_inference_steps=steps,
            guidance_scale=guidance,
        )
        
        # Save result to PNG
        output_path = Path(DOWNLOADS_DIR) / f"outpaint_result_{op_id}.png"
        result.save(str(output_path), "PNG")
        
        img.close()
        result.close()
        
        # Cleanup
        def cleanup():
            try:
                if input_path.exists():
                    input_path.unlink()
            except Exception:
                pass
            try:
                if output_path.exists():
                    output_path.unlink()
            except Exception:
                pass
        
        original_name = Path(file.filename).stem if file.filename else "outpainted"
        
        return FileResponse(
            path=output_path,
            filename=f"{original_name}_outpainted.png",
            media_type="image/png",
            background=BackgroundTask(cleanup)
        )
        
    except Exception as e:
        # Cleanup on error
        if input_path.exists():
            input_path.unlink()
        raise HTTPException(status_code=500, detail=f"Outpainting error: {str(e)}")

# =====================================================
# REMOVE BACKGROUND ENDPOINT
# =====================================================
@router.post("/remove-background")
async def remove_background_api(
    file: UploadFile = File(...),
    model: str = Form("u2net"),
    alpha_matting: bool = Form(False),
    erode_size: int = Form(10),
    fg_threshold: int = Form(240),
    bg_threshold: int = Form(10),
    post_process: bool = Form(False),
    decontaminate: bool = Form(False)
):
    """Remueve el fondo de una imagen usando rembg."""
    if not ENABLE_REMBG:
        raise HTTPException(status_code=404, detail="Quitar Fondo no disponible en esta versión")

    from PIL import Image as PILImage
    import shutil
    import uuid as _uuid
    
    try:
        from src.services.rembg_service import rembg_service
    except ImportError:
        raise HTTPException(status_code=500, detail="rembg no instalado")
        
    op_id = str(_uuid.uuid4())[:8]
    input_path = Path(DOWNLOADS_DIR) / f"rembg_input_{op_id}.png"
    
    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")
        
    try:
        img = PILImage.open(input_path).convert("RGBA")
        
        # Ejecutar en hilo de fondo
        result = await asyncio.to_thread(
            rembg_service.remove_background, 
            img, 
            model_name=model, 
            alpha_matting=alpha_matting, 
            erode_size=erode_size, 
            fg_threshold=fg_threshold,
            bg_threshold=bg_threshold,
            post_process=post_process,
            decontaminate=decontaminate
        )
        
        output_path = Path(DOWNLOADS_DIR) / f"rembg_result_{op_id}.png"
        result.save(str(output_path), "PNG")
        
        img.close()
        result.close()
        
        def cleanup():
            try:
                if input_path.exists(): input_path.unlink()
            except Exception: pass
            try:
                if output_path.exists(): output_path.unlink()
            except Exception: pass
            
        original_name = Path(file.filename).stem if file.filename else "image"
        
        return FileResponse(
            path=output_path,
            filename=f"{original_name}_nobg.png",
            media_type="image/png",
            background=BackgroundTask(cleanup)
        )
    except Exception as e:
        if input_path.exists():
            input_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error al quitar fondo: {str(e)}")


# =====================================================
# PDF COMPRESSION ENDPOINTS
# =====================================================

# Almacén temporal de compresiones de PDF completadas
compress_results: dict = {}


def run_compress_pdf_task(
    compress_id: str,
    file_path: str,
    quality: int,
    original_name: str,
    max_size_mb: Optional[float] = None,
):
    """Ejecuta la compresión de PDF en segundo plano"""
    try:
        compress_progress[compress_id].update({
            'status': 'compressing',
            'percent': 0,
            'message': 'Analizando PDF...'
        })

        input_path = Path(file_path)
        output_path = input_path.parent / f"pdfcompress_out_{compress_id}.pdf"

        if max_size_mb:
            max_size_bytes = int(max_size_mb * 1024 * 1024)
            original_size, final_size, quality_used, reached_target = pdf_service.compress_to_target_size(
                input_path, output_path, max_size_bytes=max_size_bytes, compress_id=compress_id
            )
        else:
            original_size, final_size = pdf_service.compress(
                input_path, output_path, quality=quality, compress_id=compress_id
            )
            quality_used = quality
            reached_target = True

        compress_results[compress_id] = {
            'input_path': str(input_path),
            'output_path': str(output_path),
            'output_name': f"{original_name}_comprimido.pdf",
        }
        compress_progress[compress_id].update({
            'status': 'completed',
            'percent': 100,
            'original_size': original_size,
            'final_size': final_size,
            'quality_used': quality_used,
            'reached_target': reached_target,
        })
    except Exception as e:
        compress_progress[compress_id] = {
            'status': 'error',
            'percent': 0,
            'error': str(e)
        }


@router.post("/pdf/compress")
async def start_pdf_compress(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    quality: int = Form(100),
    max_size_mb: Optional[float] = Form(None),
):
    """
    Sube un PDF e inicia su compresión en segundo plano.

    La estructura del archivo siempre se optimiza sin pérdida. Si se envía
    `max_size_mb`, se ignora `quality` y en su lugar se busca automáticamente
    la mejor calidad que quepa en ese límite de peso. De lo contrario, si
    `quality` < 100, se recomprimen las imágenes internas a esa calidad
    (100 = no tocarlas).
    """
    if Path(file.filename).suffix.lower() != '.pdf':
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")

    quality = max(30, min(100, quality))
    if max_size_mb is not None and max_size_mb <= 0:
        raise HTTPException(status_code=400, detail="El peso máximo debe ser mayor que 0")

    compress_id = str(uuid.uuid4())[:8]

    import re
    original_name = re.sub(r'[^\w\s-]', '', Path(file.filename).stem).strip() or 'documento'
    input_path = Path(DOWNLOADS_DIR) / f"pdfcompress_in_{compress_id}.pdf"

    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando archivo: {str(e)}")

    compress_progress[compress_id] = {
        'status': 'starting',
        'percent': 0,
        'message': 'Iniciando compresión...'
    }

    background_tasks.add_task(
        run_compress_pdf_task, compress_id, str(input_path), quality, original_name, max_size_mb
    )
    return {"compress_id": compress_id, "message": "Compresión iniciada"}


@router.get("/pdf/compress/progress/{compress_id}")
async def get_pdf_compress_progress(compress_id: str):
    """Obtiene el progreso de una compresión de PDF."""
    return compress_progress.get(compress_id, {'status': 'unknown', 'percent': 0})


@router.get("/pdf/compress/download/{compress_id}")
async def download_compressed_pdf(compress_id: str):
    """Descarga el PDF comprimido y limpia los archivos temporales tras enviarlo."""
    result = compress_results.get(compress_id)
    if not result:
        raise HTTPException(status_code=404, detail="Compresión no encontrada")

    output_path = Path(result['output_path'])
    input_path = Path(result['input_path'])
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Archivo comprimido no encontrado")

    def cleanup():
        try:
            if input_path.exists():
                input_path.unlink()
        except Exception:
            pass
        try:
            if output_path.exists():
                output_path.unlink()
        except Exception:
            pass
        compress_progress.pop(compress_id, None)
        compress_results.pop(compress_id, None)

    return FileResponse(
        path=output_path,
        filename=result['output_name'],
        media_type='application/pdf',
        background=BackgroundTask(cleanup)
    )


# =====================================================
# APP DE ESCRITORIO: GUARDAR EL RESULTADO MOVIÉNDOLO
# =====================================================
# En la ventana de escritorio el archivo terminado no viaja por HTTP hasta la página: la ventana
# pregunta dónde guardarlo (cuadro nativo) y el motor lo mueve desde la carpeta de trabajo. En el
# mismo disco eso no copia nada, pese lo que pese el archivo. Las rutas de descarga por HTTP de
# cada flujo siguen existiendo para el modo navegador.

class SaveRequest(BaseModel):
    kind: str      # 'download' | 'convert' | 'audio' | 'pdf'
    id: str
    dest: str      # ruta completa elegida en «Guardar como»


def _result_entry(kind: str, item_id: str):
    """(ruta del resultado, ruta del archivo de entrada o None, función que olvida la tarea)."""
    if kind == 'download':
        result = download_results.get(item_id)
        if not result:
            return None

        def forget():
            download_results.pop(item_id, None)
            download_progress.pop(item_id, None)
        return Path(result['file_path']), None, forget

    stores = {
        'convert': (conversion_results, conversion_progress),
        'audio': (audio_extract_results, audio_extract_progress),
        'pdf': (compress_results, compress_progress),
    }
    if kind not in stores:
        return None
    results, progress = stores[kind]
    result = results.get(item_id)
    if not result:
        return None

    def forget():
        results.pop(item_id, None)
        progress.pop(item_id, None)
    input_path = Path(result['input_path']) if result.get('input_path') else None
    return Path(result['output_path']), input_path, forget


def _move_file(src: Path, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(src, dest)          # mismo disco: instantáneo, y reemplaza si el usuario aceptó sobrescribir
    except OSError:
        shutil.copy2(src, dest)        # otro disco: no hay más remedio que copiar
        src.unlink(missing_ok=True)


@router.post("/save")
async def save_result(request: SaveRequest):
    """Mueve el resultado de una tarea a la ruta que eligió el usuario."""
    entry = _result_entry(request.kind, request.id)
    if not entry:
        raise HTTPException(status_code=404, detail="Ese resultado ya no está disponible")
    src, input_path, forget = entry
    if not src.exists():
        forget()
        raise HTTPException(status_code=404, detail="El archivo ya no está en la carpeta de trabajo")
    dest = Path(request.dest)
    if not dest.is_absolute():
        raise HTTPException(status_code=400, detail="La ruta de destino no es válida")
    try:
        await asyncio.to_thread(_move_file, src, dest)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"No se pudo guardar en esa ubicación: {e.strerror or e}")
    if input_path:
        try:
            input_path.unlink(missing_ok=True)
        except OSError:
            pass
    forget()
    return {"saved": True, "path": str(dest), "size": dest.stat().st_size}


class DiscardRequest(BaseModel):
    kind: str
    id: str


@router.post("/discard")
async def discard_result(request: DiscardRequest):
    """El usuario cerró la tarea sin guardar: se borran sus archivos de trabajo ya, sin esperar al barrido."""
    entry = _result_entry(request.kind, request.id)
    if entry:
        src, input_path, forget = entry
        for path in (src, input_path):
            try:
                if path:
                    path.unlink(missing_ok=True)
            except OSError:
                pass
        forget()
    return {"discarded": bool(entry)}


# =====================================================
# APP DE ESCRITORIO: VERSIÓN Y ACTUALIZACIONES
# =====================================================

_UPDATE_CACHE_TTL = 6 * 3600   # una consulta a GitHub cada 6 h como mucho (salvo «Buscar ahora»)
_update: dict = {"checked_at": 0.0, "info": None, "status": "idle", "percent": 0, "error": None}


@router.get("/app/info")
async def app_info():
    """Nombre y versión de la app (los muestra la barra lateral)."""
    return {"name": APP_NAME, "version": APP_VERSION, "can_install": updater.can_install()}


def _update_payload() -> dict:
    info = _update["info"]
    return {
        "current": APP_VERSION,
        "available": bool(info),
        "version": info["version"] if info else None,
        "notes": info["notes"] if info else "",
        "page": info["page"] if info else "",
        "size": info["size"] if info else 0,
        # sin instalador verificable (o en desarrollo / Mac) solo se ofrece abrir la página de la versión
        "can_install": bool(info and info.get("url") and updater.can_install()),
        "status": _update["status"],
        "percent": _update["percent"],
        "error": _update["error"],
    }


@router.get("/update/check")
async def update_check(force: bool = False):
    """Consulta si hay una versión más nueva publicada."""
    fresh = _time.time() - _update["checked_at"] < _UPDATE_CACHE_TTL
    if (force or not fresh) and _update["status"] not in ("downloading", "installing"):
        _update["info"] = await asyncio.to_thread(updater.check, UPDATES_REPO, APP_VERSION)
        _update["checked_at"] = _time.time()
        if _update["status"] == "error":
            _update.update(status="idle", error=None)
    return _update_payload()


def _run_update():
    """Descarga, verifica y lanza el instalador; después la app se cierra para dejarse reemplazar."""
    info = _update["info"]
    try:
        def on_progress(done, total):
            _update["percent"] = int(done * 100 / total) if total else 0

        path = updater.fetch_and_verify(info, on_progress)
        _update.update(status="installing", percent=100)
        updater.run_installer(path)
        _time.sleep(1.2)   # que la interfaz alcance a mostrar «Instalando…»
        os._exit(0)
    except Exception as e:
        _update.update(status="error", error=str(e))


@router.post("/update/install")
async def update_install():
    """Empieza a descargar e instalar la actualización disponible."""
    info = _update["info"]
    if not info:
        raise HTTPException(status_code=404, detail="No hay ninguna actualización pendiente")
    if not (info.get("url") and updater.can_install()):
        raise HTTPException(status_code=400, detail="Esta versión se instala a mano desde la página de descargas")
    if _update["status"] in ("downloading", "installing"):
        return _update_payload()
    _update.update(status="downloading", percent=0, error=None)
    import threading
    threading.Thread(target=_run_update, daemon=True, name="actualizacion").start()
    return _update_payload()


@router.get("/update/progress")
async def update_progress():
    """Progreso de la descarga de la actualización."""
    return _update_payload()
