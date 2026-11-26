"""Configuración de la aplicación"""
from pathlib import Path
import importlib.util
import os
import platform
import sys


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


ENABLE_REMBG = _module_available("rembg")
ENABLE_OUTPAINT = _module_available("torch") and _module_available("diffusers")
ENABLE_AI_FEATURES = ENABLE_REMBG or ENABLE_OUTPAINT
FEATURE_FLAGS = {
    "rembg": ENABLE_REMBG,
    "outpaint": ENABLE_OUTPAINT,
}

SYSTEM_NAME = platform.system()
IS_WINDOWS = SYSTEM_NAME == "Windows"
IS_MAC = SYSTEM_NAME == "Darwin"
MAC_RESOURCES_DIR = Path(__file__).parent.parent / "mac"
FFMPEG_EXECUTABLE_NAMES = ("ffmpeg.exe", "ffmpeg") if IS_WINDOWS else ("ffmpeg", "ffmpeg.exe")
FFPROBE_EXECUTABLE_NAMES = ("ffprobe.exe", "ffprobe") if IS_WINDOWS else ("ffprobe", "ffprobe.exe")


def get_feature_flags() -> dict:
    flags = FEATURE_FLAGS.copy()
    # Import diferido: ffmpeg_finder importa de este mismo módulo (FFMPEG_LOCATIONS), así
    # que no se puede importar find_ffmpeg arriba sin crear un ciclo de imports.
    from src.utils.ffmpeg_finder import find_ffmpeg
    flags["ffmpeg"] = find_ffmpeg() is not None
    return flags

# Directorios
FROZEN = getattr(sys, "frozen", False)

# Recursos de solo lectura: el repo en desarrollo, la carpeta de PyInstaller en la app instalada.
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent))


def _data_dir() -> Path:
    """Carpeta de datos que se puede escribir.

    En desarrollo es el repo (como siempre). En la app instalada NO puede ser la carpeta del
    programa: el instalador la reemplaza en cada actualización y se perdería todo.
    """
    if not FROZEN:
        return BASE_DIR
    if IS_WINDOWS:
        return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "UniverseDownloader"
    if IS_MAC:
        return Path.home() / "Library" / "Application Support" / "UniverseDownloader"
    return Path.home() / ".universe-downloader"


DATA_DIR = _data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_FOLDER = DATA_DIR / "downloads"
DOWNLOAD_FOLDER.mkdir(exist_ok=True)
DOWNLOADS_DIR = str(DOWNLOAD_FOLDER)

# Servidor
HOST = "127.0.0.1"
PORT = 8000

# FFmpeg locations
FFMPEG_LOCATIONS = [
    str(BASE_DIR / 'bin'),
    str(MAC_RESOURCES_DIR / 'bin'),
    str(BASE_DIR / 'ffmpeg' / 'bin'),
    r'C:\ffmpeg\bin',
    r'C:\Program Files\ffmpeg\bin',
    os.path.expanduser(r'~\scoop\apps\ffmpeg\current\bin'),
    os.path.expanduser(r'~\scoop\apps\ffmpeg\current\bin'),
    os.path.expanduser(r'~\AppData\Local\Microsoft\WinGet\Links'),
    '/opt/homebrew/bin',
    '/usr/local/bin',
]

# Formatos soportados
SUPPORTED_FORMATS = ['mp3', 'mp4']

# Calidad máxima de video (altura en píxeles)
MAX_VIDEO_HEIGHT = 2160  # 4K
