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
    flags = FEATURE_FLAGS.copy()
    # Import diferido: ffmpeg_finder importa de este mismo módulo (FFMPEG_LOCATIONS), así
    # que no se puede importar find_ffmpeg arriba sin crear un ciclo de imports.
    from src.utils.ffmpeg_finder import find_ffmpeg
    flags["ffmpeg"] = find_ffmpeg() is not None
    return flags

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

# Cookies de YouTube (opcional): permiten a yt-dlp autenticarse como una sesión real y evitar
# el bloqueo anti-bot ("Sign in to confirm you're not a bot") que YouTube aplica a IPs de
# servidores cloud. En producción se monta como volumen de solo lectura (ver compose.prod.yml);
# en desarrollo local el archivo simplemente no existe y el código sigue funcionando sin cookies.
YOUTUBE_COOKIES_FILE = Path(os.environ.get("YOUTUBE_COOKIES_FILE", str(BASE_DIR / "cookies" / "youtube.txt")))

# Perfil Chrome aislado y opcional, creado por el servicio temporal youtube-login. Se monta en
# solo lectura en la app para que yt-dlp lea exclusivamente las cookies de youtube.com; nunca se
# comparte el perfil de Chrome de la persona ni el navegador de otras automatizaciones.
YOUTUBE_BROWSER_PROFILE = Path(os.environ["YOUTUBE_BROWSER_PROFILE"]) if os.environ.get("YOUTUBE_BROWSER_PROFILE") else None

# Proxy de salida opcional, aplicado exclusivamente a URLs de YouTube. Permite sacar las
# solicitudes por una IP distinta cuando YouTube bloquea el rango del proveedor cloud, sin
# alterar TikTok, Instagram ni los demás extractores.
YOUTUBE_PROXY = os.environ.get("YOUTUBE_PROXY", "").strip() or None

# Formatos soportados
SUPPORTED_FORMATS = ['mp3', 'mp4']

# Calidad máxima de video (altura en píxeles)
MAX_VIDEO_HEIGHT = 2160  # 4K
