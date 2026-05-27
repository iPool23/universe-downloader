"""Configuración de la aplicación"""
from pathlib import Path
import importlib.util
import os
import platform


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
    return FEATURE_FLAGS.copy()

# Directorios
BASE_DIR = Path(__file__).parent.parent
DOWNLOAD_FOLDER = BASE_DIR / "downloads"
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
]

# Formatos soportados
SUPPORTED_FORMATS = ['mp3', 'mp4']

# Calidad máxima de video (altura en píxeles)
MAX_VIDEO_HEIGHT = 2160  # 4K
