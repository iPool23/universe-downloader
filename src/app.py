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
    return html.replace('{"rembg":true,"outpaint":true}', feature_flags)


@app.get("/health")
async def health_check():
    """Endpoint de salud"""
    return {"status": "ok"}
