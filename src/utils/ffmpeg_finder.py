"""Utilidad para encontrar FFmpeg en el sistema"""
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.config import FFMPEG_LOCATIONS


def find_ffmpeg() -> Optional[str]:
    """
    Busca FFmpeg en ubicaciones comunes del sistema.
    
    Returns:
        str: Ruta al directorio de FFmpeg si se encuentra, None en caso contrario
    """
    import shutil
    
    # First check system PATH
    which_ffmpeg = shutil.which('ffmpeg')
    if which_ffmpeg:
        # Resolve symlinks to get real path
        try:
            real_path = os.path.realpath(which_ffmpeg)
            if os.access(real_path, os.X_OK):
                return str(Path(real_path).parent)
        except Exception:
            pass
        return str(Path(which_ffmpeg).parent)

    for location in FFMPEG_LOCATIONS:
        if os.path.exists(os.path.join(location, 'ffmpeg.exe')):
            return location
    
    return None
