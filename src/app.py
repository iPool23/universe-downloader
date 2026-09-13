"""Aplicación principal FastAPI

Autor: Pool Anthony Deza Millones
GitHub: @iPool23
"""
import json
import uvicorn
import webbrowser
import threading
import time
import sys
import os
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Fix para ejecutar sin consola (windowed mode)
# Cuando no hay consola, stdout/stderr son None y uvicorn falla
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

# Suprimir errores de conexión cerrada (común en Windows)
class ConnectionResetFilter(logging.Filter):
    def filter(self, record):
        msg = str(record.getMessage())
        return 'ConnectionResetError' not in msg and 'WinError 10054' not in msg

# Aplicar filtro a los loggers de asyncio y uvicorn
for logger_name in ['asyncio', 'uvicorn.error', 'uvicorn.access']:
    logger = logging.getLogger(logger_name)
    logger.addFilter(ConnectionResetFilter())

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api import router as api_router
from src.config import DOWNLOADS_DIR, get_feature_flags

# Rutas
BASE_DIR = Path(__file__).parent.parent
PUBLIC_DIR = BASE_DIR / "public"

# Crear aplicación
app = FastAPI(
    title="Downloader API",
    description="API para descargar videos y audio de YouTube",
    version="2.1.0"
)

# Montar archivos estáticos
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Montar directorio de descargas para reproducción
app.mount("/content", StaticFiles(directory=DOWNLOADS_DIR), name="content")

# Registrar rutas de la API
app.include_router(api_router)


# Respaldo de limpieza: cada endpoint que entrega un archivo ya lo borra apenas se envía, pero una
# descarga cancelada, una pestaña cerrada a medias o un error dejan el archivo huérfano en disco sin
# nada que lo borre — sin este barrido se quedarían ahí para siempre y terminarían llenando el disco.
DOWNLOAD_MAX_AGE_SECONDS = 2 * 60 * 60  # 2 horas: de sobra para cualquier descarga/conversión real
CLEANUP_INTERVAL_SECONDS = 30 * 60


def _cleanup_orphaned_downloads():
    while True:
        time.sleep(CLEANUP_INTERVAL_SECONDS)
        try:
            now = time.time()
            for entry in Path(DOWNLOADS_DIR).iterdir():
                if entry.name.startswith('.'):
                    continue  # p. ej. .gitkeep: no es un archivo descargado, no se toca
                if entry.is_file() and (now - entry.stat().st_mtime) > DOWNLOAD_MAX_AGE_SECONDS:
                    entry.unlink()
        except Exception:
            pass


threading.Thread(target=_cleanup_orphaned_downloads, daemon=True).start()


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Favicon"""
    favicon_path = PUBLIC_DIR / "imgs" / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    return FileResponse(status_code=404)


@app.get("/", response_class=HTMLResponse)
async def home():
    """Página principal"""
    html_path = Path(__file__).parent / "views" / "index.html"
    html = html_path.read_text(encoding='utf-8')
    feature_flags = json.dumps(get_feature_flags(), ensure_ascii=False, separators=(",", ":"))
    return html.replace('{"rembg":true,"outpaint":true,"ffmpeg":true}', feature_flags)


@app.get("/health")
async def health_check():
    """Endpoint de salud"""
    return {"status": "ok"}
