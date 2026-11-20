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

from fastapi import FastAPI, HTTPException
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

from src.config import DOWNLOADS_DIR, FROZEN, get_feature_flags
from src.version import APP_NAME, APP_VERSION

# Rutas
BASE_DIR = Path(__file__).parent.parent
PUBLIC_DIR = BASE_DIR / "public"

# Crear aplicación
app = FastAPI(
    title=f"{APP_NAME} API",
    description="Motor local de Universe Downloader",
    version=APP_VERSION
)

# Montar archivos estáticos
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Montar directorio de descargas para reproducción
app.mount("/content", StaticFiles(directory=DOWNLOADS_DIR), name="content")

# Las rutas de la API se cargan en segundo plano. Importarlas arrastra yt-dlp, pikepdf, curl_cffi y
# el resto de lo pesado (dos tercios del arranque del motor), y la interfaz no las necesita para
# pintarse: así la página se sirve enseguida y las funciones quedan listas un momento después.
# Una petición a /api/ que llegue antes espera a que terminen de cargar; no falla.
api_ready = threading.Event()
api_error = None


def _load_api():
    global api_error
    try:
        from src.api import router as api_router
        app.include_router(api_router)
    except Exception as error:   # se verá en el registro y en la primera petición a la API
        api_error = error
        logging.getLogger("motor").exception("no se pudieron cargar las rutas de la API")
    finally:
        api_ready.set()


class WaitForApi:
    """ASGI puro (sin BaseHTTPMiddleware, que frena las respuestas de archivos grandes)."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and not api_ready.is_set() and scope["path"].startswith("/api/"):
            import asyncio
            await asyncio.to_thread(api_ready.wait, 60)
        await self.inner(scope, receive, send)


app.add_middleware(WaitForApi)
threading.Thread(target=_load_api, daemon=True, name="api").start()


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


# Solo en la app instalada: en desarrollo la carpeta de trabajo es downloads/ del repo y no se toca.
if FROZEN:
    threading.Thread(target=_cleanup_orphaned_downloads, daemon=True).start()


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Favicon"""
    favicon_path = PUBLIC_DIR / "imgs" / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    raise HTTPException(status_code=404)


@app.get("/", response_class=HTMLResponse)
async def home():
    """Página principal"""
    html_path = Path(__file__).parent / "views" / "index.html"
    html = html_path.read_text(encoding='utf-8')
    feature_flags = json.dumps(get_feature_flags(), ensure_ascii=False, separators=(",", ":"))
    html = html.replace('{"rembg":true,"outpaint":true,"ffmpeg":true}', feature_flags)
    # versión: la muestra la barra lateral y evita que la ventana use estilos o scripts de la versión anterior
    html = html.replace('__APP_VERSION__', APP_VERSION)
    # el tema guardado va en la propia página: se pinta bien desde el primer cuadro
    from src import prefs
    theme = prefs.theme()
    return html.replace('__APP_THEME__', theme).replace('<body>', '<body class="dark-mode">' if theme == 'dark' else '<body>', 1)


@app.get("/health")
async def health_check():
    """Endpoint de salud"""
    return {"status": "ok"}
