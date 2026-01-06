"""Servicio de transcripción de audio/video usando OpenAI Whisper"""
import os
import sys
from pathlib import Path
from typing import Optional, Callable
import glob

# Progreso de transcripciones en curso
transcription_progress: dict = {}

def find_ffmpeg():
    """Busca FFmpeg en ubicaciones comunes de Windows"""
    # Primero verificar si ya está en PATH
    import shutil
    if shutil.which("ffmpeg"):
        return True
    
    # Buscar en ubicaciones comunes
    search_paths = [
        r"C:\Users\*\AppData\Local\Microsoft\WinGet\Packages\*\*\bin",
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        r"C:\Program Files (x86)\ffmpeg\bin",
    ]
    
    for pattern in search_paths:
        matches = glob.glob(pattern)
        for match in matches:
            ffmpeg_path = os.path.join(match, "ffmpeg.exe")
            if os.path.exists(ffmpeg_path):
                # Agregar al PATH
                os.environ["PATH"] = match + os.pathsep + os.environ.get("PATH", "")
                return True
    
    return False

# Intentar encontrar FFmpeg al importar el módulo
find_ffmpeg()

class TranscriberService:
    """Servicio para transcribir audio/video a texto usando Whisper"""
    
    def __init__(self, model_name: str = "base"):
        """
        Inicializa el servicio de transcripción.
        
        Args:
            model_name: Nombre del modelo Whisper a usar 
                       (tiny, base, small, medium, large)
        """
        self.model_name = model_name
        self._model = None
    
    def _load_model(self):
        """Carga el modelo Whisper de forma perezosa con fallback a CPU"""
        if self._model is None:
            try:
                import torch
                import whisper
                
                # Check for CUDA availability first
                device = "cuda" if torch.cuda.is_available() else "cpu"
                
                try:
                    # Try loading on the detected device (likely CUDA)
                    print(f"[WHISPER] Loading model on {device}...")
                    self._model = whisper.load_model(self.model_name, device=device)
                except Exception as e:
                    if device == "cuda":
                        print(f"[WHISPER] Error loading on CUDA: {e}")
                        print("[WHISPER] Falling back to CPU...")
                        self._model = whisper.load_model(self.model_name, device="cpu")
                    else:
                        raise e

            except ImportError:
                raise RuntimeError(
                    "Whisper no está instalado. Ejecute: pip install openai-whisper"
                )
            except Exception as e:
                raise RuntimeError(f"Error al cargar modelo Whisper: {str(e)}")
        return self._model
    
    def transcribe(
        self,
        file_path: str,
        transcribe_id: str,
        language: str = "Spanish",
        output_dir: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Transcribe un archivo de audio/video a texto.
        
        Args:
            file_path: Ruta al archivo de audio/video
            transcribe_id: ID único para rastrear el progreso
            language: Idioma del audio (default: Spanish)
            output_dir: Directorio de salida (default: mismo que el archivo)
            
        Returns:
            tuple: (ruta del archivo txt, nombre del archivo)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        # Actualizar progreso: iniciando
        transcription_progress[transcribe_id] = {
            'status': 'loading_model',
            'percent': 10,
            'message': 'Cargando modelo Whisper...'
        }
        
        # Cargar modelo
        try:
            model = self._load_model()
        except Exception as e:
            transcription_progress[transcribe_id] = {
                'status': 'error',
                'percent': 0,
                'error': str(e)
            }
            raise
        
        # Actualizar progreso: transcribiendo
        transcription_progress[transcribe_id] = {
            'status': 'transcribing',
            'percent': 30,
            'message': 'Transcribiendo audio...'
        }
        
        try:
            # Realizar transcripción
            result = model.transcribe(
                str(file_path),
                language="es",  # Código ISO para español
                verbose=False
            )
            
            # Actualizar progreso: guardando
            transcription_progress[transcribe_id] = {
                'status': 'saving',
                'percent': 90,
                'message': 'Guardando transcripción...'
            }
            
            # Generar nombre del archivo de salida
            output_name = file_path.stem + "_transcripcion.txt"
            if output_dir:
                output_path = Path(output_dir) / output_name
            else:
                output_path = file_path.parent / output_name
            
            # Guardar transcripción
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result['text'].strip())
            
            # Actualizar progreso: completado
            transcription_progress[transcribe_id] = {
                'status': 'completed',
                'percent': 100,
                'message': 'Transcripción completada',
                'output_path': str(output_path),
                'output_name': output_name
            }
            
            return str(output_path), output_name
            
        except Exception as e:
            transcription_progress[transcribe_id] = {
                'status': 'error',
                'percent': 0,
                'error': str(e)
            }
            raise RuntimeError(f"Error durante la transcripción: {str(e)}")
