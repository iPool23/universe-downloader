"""
Punto de entrada de la aplicación

Autor: Pool Anthony Deza Millones
GitHub: @iPool23
"""
import uvicorn
import webbrowser
import threading
import time
import sys
import os
from pathlib import Path

# Fix para ejecutar sin consola (windowed mode)
# Cuando no hay consola, stdout/stderr son None y uvicorn falla
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app import app
from src.config import HOST, PORT


def open_browser():
    """Abre el navegador después de iniciar el servidor"""
    time.sleep(1.5)
    webbrowser.open(f'http://{HOST}:{PORT}')


def main():
    """Función principal"""
    # Iniciar navegador en hilo separado
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Iniciar servidor (sin logs cuando está en modo windowed)
    uvicorn.run(app, host=HOST, port=PORT, log_level="error")


if __name__ == "__main__":
    main()
