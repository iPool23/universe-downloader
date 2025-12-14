"""
Aplicación principal FastAPI

Autor: Pool Anthony Deza Millones
GitHub: @iPool23
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.api import router as api_router

from src.config import DOWNLOADS_DIR

# Crear aplicación
app = FastAPI(
    title="Universe Downloader API",
    description="API para descargar videos y audio de YouTube",
    version="1.0.0"
)

# Montar archivos estáticos
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Montar directorio de descargas para reproducción
app.mount("/content", StaticFiles(directory=DOWNLOADS_DIR), name="content")

# Registrar rutas de la API
app.include_router(api_router)


@app.get("/", response_class=HTMLResponse)
async def home():
    """Página principal"""
    html_path = Path(__file__).parent / "views" / "index.html"
    return html_path.read_text(encoding='utf-8')


@app.get("/health")
async def health_check():
    """Endpoint de salud"""
    return {"status": "ok"}
