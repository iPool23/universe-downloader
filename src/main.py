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
import logging
from pathlib import Path

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

from src.app import app
from src.config import HOST, PORT

# Variables globales para el servidor y el tray
server = None
tray_icon = None


def get_icon_path():
    """Obtiene la ruta del icono"""
    if getattr(sys, 'frozen', False):
        # Si es un ejecutable (PyInstaller)
        base_dir = Path(sys._MEIPASS)
    else:
        # Si es script normal
        base_dir = Path(__file__).parent.parent
        
    icon_path = base_dir / "public" / "imgs" / "favicon.ico"
    if icon_path.exists():
        return str(icon_path)
    return None


def open_browser_action():
    """Abre el navegador en la aplicación"""
    webbrowser.open(f'http://{HOST}:{PORT}')


def exit_action():
    """Cierra la aplicación completamente"""
    global tray_icon, server
    
    # Detener el icono del tray
    if tray_icon:
        tray_icon.stop()
    
    # Forzar salida del proceso
    os._exit(0)


def create_tray_icon():
    """Crea el icono en la bandeja del sistema"""
    global tray_icon
    
    try:
        import pystray
        from PIL import Image
    except ImportError:
        print("pystray o Pillow no están instalados")
        return None
    
    # Cargar icono
    icon_path = get_icon_path()
    if icon_path:
        try:
            image = Image.open(icon_path)
        except:
            # Crear icono por defecto si falla
            image = Image.new('RGB', (64, 64), color='#6366f1')
    else:
        # Crear icono por defecto
        image = Image.new('RGB', (64, 64), color='#6366f1')
    
    # Crear menú
    menu = pystray.Menu(
        pystray.MenuItem("🌐 Abrir en navegador", lambda: open_browser_action()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌ Cerrar aplicación", lambda: exit_action())
    )
    
    # Crear icono
    tray_icon = pystray.Icon(
        "Downloader",
        image,
        "Downloader",
        menu
    )
    
    return tray_icon


def run_server():
    """Ejecuta el servidor uvicorn"""
    global server
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="error")
    server = uvicorn.Server(config)
    server.run()


def open_browser():
    """Abre el navegador después de iniciar el servidor"""
    time.sleep(1.5)
    webbrowser.open(f'http://{HOST}:{PORT}')


def main():
    """Función principal con soporte para system tray"""
    # Iniciar navegador en hilo separado
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Crear icono del tray
    icon = create_tray_icon()
    
    if icon:
        # Iniciar servidor en hilo separado
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Ejecutar el tray icon en el hilo principal (requerido en Windows)
        icon.run()
    else:
        # Fallback: ejecutar sin tray icon
        uvicorn.run(app, host=HOST, port=PORT, log_level="error")


if __name__ == "__main__":
    main()
