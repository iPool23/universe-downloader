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
from typing import List, Dict, Tuple
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
        raise HTTPException(status_code=500, detail=str(e))

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
    Limpia los datos de progreso para evitar memory leaks.
    """
    result = download_results.get(download_id)
    if not result:
        raise HTTPException(status_code=404, detail="Descarga no encontrada")
    
    file_path = Path(result['file_path'])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    def cleanup_download_data():
        """Limpiar datos de progreso y resultados tras enviar el archivo."""
        download_progress.pop(download_id, None)
        download_results.pop(download_id, None)
    
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
# IMAGE FORMAT CONVERSION ENDPOINT
# =====================================================

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
    target_format = target_format.lower().strip()
    if target_format == 'jpeg':
        target_format = 'jpg'
    
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
        from PIL import Image
        
        img = Image.open(input_path)
        
        # Resize if dimensions specified
        if width > 0 and height > 0:
            img = img.resize((width, height), Image.LANCZOS)
        elif width > 0:
            ratio = width / img.width
            img = img.resize((width, int(img.height * ratio)), Image.LANCZOS)
        elif height > 0:
            ratio = height / img.height
            img = img.resize((int(img.width * ratio), height), Image.LANCZOS)
        
        # Handle transparency: RGBA -> RGB for formats that don't support alpha
        if target_format in ('jpg', 'jpeg'):
            if img.mode in ('RGBA', 'LA', 'PA'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
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


# =====================================================
# OUTPAINTING (AI IMAGE EXPANSION) ENDPOINTS
# =====================================================

@router.get("/outpaint/status")
async def outpaint_status():
    """Verifica si la GPU está disponible y el modelo cargado."""
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
