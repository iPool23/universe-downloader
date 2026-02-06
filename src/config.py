"""Configuración de la aplicación"""
from pathlib import Path
import os

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
