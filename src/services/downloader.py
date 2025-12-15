"""Servicio de descarga de videos"""
import yt_dlp
import sys
import os
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple, Callable

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.config import DOWNLOAD_FOLDER, MAX_VIDEO_HEIGHT
from src.utils import find_ffmpeg, sanitize_filename

# Almacén global de progreso de descargas
download_progress: Dict[str, Dict] = {}


class ProgressLogger:
    """Logger que captura el progreso de descarga"""
    def __init__(self, download_id: str):
        self.download_id = download_id
    
    def debug(self, msg):
        pass

    def warning(self, msg):
        ignore_keywords = [
            "PO Token", "SABR", "JS runtime", "missing a url", 
            "falling back", "Unable to download webpage"
        ]
        if any(k in msg for k in ignore_keywords):
            return

    def error(self, msg):
        print(f"ERROR: {msg}")
        if self.download_id in download_progress:
            download_progress[self.download_id]['error'] = msg


class QuietLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        # Ignore common noise warnings
        ignore_keywords = [
            "PO Token", "SABR", "JS runtime", "missing a url", 
            "falling back", "Unable to download webpage"
        ]
        if any(k in msg for k in ignore_keywords):
            return
        print(f"WARNING: {msg}")

    def error(self, msg):
        print(f"ERROR: {msg}")


class DownloaderService:
    """Servicio para descargar videos de YouTube"""
    
    def __init__(self):
        self.ffmpeg_path = find_ffmpeg()
        if self.ffmpeg_path:
            # Añadir a PATH para asegurar que yt-dlp lo encuentre
            os.environ["PATH"] += os.pathsep + self.ffmpeg_path

    def _parse_time(self, time_str: str) -> float:
        """Convierte string de tiempo (HH:MM:SS o MM:SS) a segundos"""
        if not time_str:
            return 0
        try:
            parts = list(map(float, time_str.split(':')))
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            elif len(parts) == 2:
                return parts[0] * 60 + parts[1]
            elif len(parts) == 1:
                return parts[0]
            return 0
        except ValueError:
            return 0

    def _get_thumbnail(self, info: Dict, url: str) -> Optional[str]:
        """Intenta obtener el thumbnail del video de varias fuentes"""
        # Primero intentar thumbnail directo
        thumbnail = info.get('thumbnail')
        if thumbnail:
            return thumbnail
        
        # Intentar desde el array de thumbnails
        thumbnails = info.get('thumbnails', [])
        if thumbnails:
            # Tomar el de mayor resolución
            return thumbnails[-1].get('url')
        
        # Para Kick, intentar obtener imagen del canal
        if 'kick.com' in url:
            try:
                # Extraer nombre del canal de la URL
                import re
                match = re.search(r'kick\.com/([^/]+)', url)
                if match:
                    channel_name = match.group(1)
                    from curl_cffi import requests as cf_requests
                    r = cf_requests.get(f'https://kick.com/api/v2/channels/{channel_name}', impersonate='chrome', timeout=5)
                    if r.status_code == 200:
                        data = r.json()
                        # Intentar obtener banner o profile pic
                        banner = data.get('banner_image', {})
                        if banner and banner.get('url'):
                            return banner.get('url')
                        profile_pic = data.get('user', {}).get('profile_pic')
                        if profile_pic:
                            return profile_pic
            except Exception:
                pass
        
        return None

    def get_video_info(self, url: str) -> Dict:
        """Obtiene información del video sin descargar"""
        # Usamos logger silencioso y opciones por defecto
        opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True, # IMPORTANT: Prevent scanning entire playlists
            'logger': QuietLogger(),
            # Removed extractor_args to allow default fallback behavior
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Extraer calidades disponibles
            qualities = self._extract_qualities(info)
            
            # Obtener thumbnail
            thumbnail = self._get_thumbnail(info, url)
            
            return {
                'title': info.get('title'),
                'duration': info.get('duration'),
                'thumbnail': thumbnail,
                'webpage_url': info.get('webpage_url'),
                'qualities': qualities
            }
    
    def _extract_qualities(self, info: Dict) -> list:
        """Extrae las calidades de video disponibles"""
        qualities = set()
        formats = info.get('formats', [])
        
        for fmt in formats:
            height = fmt.get('height')
            if height and isinstance(height, int) and height >= 144:
                # Agregar calidades estándar
                qualities.add(height)
        
        # Ordenar de mayor a menor y formatear
        sorted_qualities = sorted(qualities, reverse=True)
        result = []
        
        for q in sorted_qualities:
            label = f"{q}p"
            if q >= 2160:
                label = f"{q}p (4K)"
            elif q >= 1440:
                label = f"{q}p (2K)"
            elif q >= 1080:
                label = f"{q}p (Full HD)"
            elif q >= 720:
                label = f"{q}p (HD)"
            
            result.append({'value': q, 'label': label})
        
        # Si no hay calidades, agregar una por defecto
        if not result:
            result.append({'value': 720, 'label': '720p (HD)'})
        
        return result
    
    def _get_base_options(self, unique_id: str) -> Dict:
        """Obtiene las opciones base para yt-dlp"""
        opts = {
            'outtmpl': str(DOWNLOAD_FOLDER / f'{unique_id}.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'logger': QuietLogger(),
        }
        
        if self.ffmpeg_path:
            path_obj = Path(self.ffmpeg_path)
            if path_obj.is_dir():
                ffmpeg_exe = path_obj / 'ffmpeg.exe'
                if ffmpeg_exe.exists():
                    opts['ffmpeg_location'] = str(ffmpeg_exe)
                else:
                    opts['ffmpeg_location'] = self.ffmpeg_path
            else:
                opts['ffmpeg_location'] = self.ffmpeg_path
        
        return opts
    
    def _get_audio_options(self, unique_id: str) -> Dict:
        """Obtiene opciones para descarga de audio"""
        opts = self._get_base_options(unique_id)
        opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
        return opts
    
    def _get_video_options(self, unique_id: str, quality: Optional[int] = None) -> Dict:
        """Obtiene opciones para descarga de video"""
        opts = self._get_base_options(unique_id)
        
        max_height = quality if quality else MAX_VIDEO_HEIGHT
        
        if self.ffmpeg_path:
            # Formato más flexible para soportar más plataformas (Kick, Twitch, etc.)
            opts['format'] = f'bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best'
            opts['merge_output_format'] = 'mp4'
        else:
            opts['format'] = f'best[height<={max_height}]/best'
        
        return opts
    
    def download(self, url: str, format_type: str, unique_id: str, start_time: Optional[str] = None, end_time: Optional[str] = None, quality: Optional[int] = None) -> Tuple[Path, str]:
        """
        Descarga un video o audio de YouTube.
        
        Args:
            url: URL del video
            format_type: Tipo de formato ('mp3' o 'mp4')
            unique_id: ID único para el archivo
            quality: Calidad del video en píxeles (ej: 720, 1080)
            
        Returns:
            Tuple[Path, str]: Ruta del archivo descargado y nombre sanitizado
            
        Raises:
            Exception: Si ocurre un error durante la descarga
        """
        # Inicializar progreso
        download_progress[unique_id] = {
            'status': 'starting',
            'percent': 0,
            'speed': '',
            'eta': '',
            'filename': '',
            'error': None
        }
        
        def clean_ansi(text):
            """Elimina códigos de escape ANSI del texto"""
            import re
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            return ansi_escape.sub('', str(text)) if text else ''
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                # Extraer porcentaje (limpiar ANSI)
                percent_str = clean_ansi(d.get('_percent_str', '0%')).strip().replace('%', '')
                try:
                    percent = float(percent_str)
                except:
                    percent = 0
                
                download_progress[unique_id].update({
                    'status': 'downloading',
                    'percent': percent,
                    'speed': clean_ansi(d.get('_speed_str', '')),
                    'eta': clean_ansi(d.get('_eta_str', '')),
                    'downloaded': clean_ansi(d.get('_downloaded_bytes_str', '')),
                    'total': clean_ansi(d.get('_total_bytes_str', d.get('_total_bytes_estimate_str', '')))
                })
            elif d['status'] == 'finished':
                download_progress[unique_id].update({
                    'status': 'processing',
                    'percent': 100
                })
            elif d['status'] == 'error':
                download_progress[unique_id].update({
                    'status': 'error',
                    'error': str(d.get('error', 'Error desconocido'))
                })
        
        # Seleccionar opciones según formato
        if format_type == 'mp3':
            ydl_opts = self._get_audio_options(unique_id)
        else:
            ydl_opts = self._get_video_options(unique_id, quality)
        
        # Agregar hook de progreso
        ydl_opts['progress_hooks'] = [progress_hook]
        ydl_opts['logger'] = ProgressLogger(unique_id)
            
        if start_time and end_time:
            start_sec = self._parse_time(start_time)
            end_sec = self._parse_time(end_time)
            
            def download_range_func(info_dict, ydl_instance):
                return [{'start_time': start_sec, 'end_time': end_sec}]
                
            ydl_opts['download_ranges'] = download_range_func
            # Force re-encoding at cuts for precision and broad compatibility (fixes Facebook/others)
            ydl_opts['force_keyframes_at_cuts'] = True
        
        # Descargar
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Buscar archivo descargado
                downloaded_files = list(DOWNLOAD_FOLDER.glob(f'{unique_id}.*'))
                
                if not downloaded_files:
                    raise Exception("No se pudo descargar el archivo")
                
                file_path = downloaded_files[0]
                
                # Generar nombre de archivo
                title = info.get('title', 'video')
                safe_title = sanitize_filename(title)
                filename = f"{safe_title}.{file_path.suffix[1:]}"
                
                # Marcar como completado
                download_progress[unique_id].update({
                    'status': 'completed',
                    'percent': 100,
                    'filename': filename
                })
                
                return file_path, filename
        except Exception as e:
            download_progress[unique_id].update({
                'status': 'error',
                'error': str(e)
            })
            raise
