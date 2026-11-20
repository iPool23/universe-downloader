"""
Punto de entrada de la aplicación

Autor: Pool Anthony Deza Millones
GitHub: @iPool23

En Windows la app es una ventana de escritorio propia (pywebview sobre Edge WebView2, que ya trae
el sistema) que muestra la interfaz servida por el motor local. Si pywebview no está disponible,
o en macOS (ventana sin verificar todavía), se usa el modo anterior: navegador + ícono en la bandeja.

    python src/main.py              ventana de escritorio
    python src/main.py --browser    modo anterior (navegador + bandeja)
    python src/main.py --selftest   arranca el motor, comprueba que responde y sale (lo usa build.ps1)
"""
import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

IS_MAC = sys.platform == 'darwin'
IS_WINDOWS = sys.platform == 'win32'

# ---- Marcas de tiempo del arranque (apagadas salvo UNIVERSE_TIMING=1) ----
# Las usa .claude/skills/optimizar-universe/scripts/medir_arranque.py: lanza la app con
# UNIVERSE_TIMING_T0=<instante en que la lanzó>, la app anota cuánto tarda cada fase y, con
# UNIVERSE_TIMING_EXIT=1, se cierra sola cuando la interfaz termina de cargar.
_TIMING = os.environ.get("UNIVERSE_TIMING") == "1"
_T0 = float(os.environ.get("UNIVERSE_TIMING_T0") or time.time())
_marks: list = []


def _mark(name: str):
    if _TIMING:
        _marks.append([name, round(time.time() - _T0, 3)])


def _dump_marks(path):
    if _TIMING:
        import json
        Path(path).write_text(json.dumps(_marks, ensure_ascii=False), encoding="utf-8")


_mark("python en marcha")

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import BASE_DIR, DATA_DIR, FROZEN, HOST, PORT  # noqa: E402
from src.version import APP_ID, APP_NAME, APP_VERSION  # noqa: E402

_mark("configuración importada")

LOG_FILE = DATA_DIR / "app.log"
LOG_MAX_BYTES = 2 * 1024 * 1024


def _setup_output():
    """Sin consola (app instalada) stdout/stderr son None y uvicorn falla: se mandan a un registro
    en la carpeta de datos, que además sirve para diagnosticar. Se reinicia al pasar de 2 MB."""
    if sys.stdout is not None and sys.stderr is not None and not FROZEN:
        return
    try:
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > LOG_MAX_BYTES:
            LOG_FILE.unlink()
        stream = open(LOG_FILE, 'a', encoding='utf-8', buffering=1)
        stream.write(f"\n=== {APP_NAME} {APP_VERSION} · {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    except OSError:
        stream = open(os.devnull, 'w')
    sys.stdout = sys.stderr = stream


_setup_output()


# Suprimir errores de conexión cerrada (común en Windows)
class ConnectionResetFilter(logging.Filter):
    def filter(self, record):
        msg = str(record.getMessage())
        return 'ConnectionResetError' not in msg and 'WinError 10054' not in msg


for logger_name in ['asyncio', 'uvicorn.error', 'uvicorn.access']:
    logging.getLogger(logger_name).addFilter(ConnectionResetFilter())


def get_icon_path():
    """Obtiene la ruta del icono"""
    candidates = [BASE_DIR / "public" / "imgs" / "favicon.ico", BASE_DIR / "mac" / "icon.icns"]
    if IS_MAC:
        candidates.reverse()
    for icon_path in candidates:
        if icon_path.exists():
            return str(icon_path)
    return None


# =====================================================
# MOTOR LOCAL (FastAPI + uvicorn)
# =====================================================

def _free_port() -> int:
    """Un puerto libre de 127.0.0.1: la ventana no depende de que el 8000 esté desocupado."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def start_server(port: int, timeout: float = 60.0):
    """Arranca uvicorn en un hilo y espera a que acepte conexiones. Devuelve el servidor."""
    import uvicorn
    from src.app import app
    _mark("motor importado")

    server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True, name="motor").start()
    deadline = time.time() + timeout
    while not server.started:
        if time.time() > deadline:
            raise RuntimeError("el motor local no arrancó a tiempo")
        time.sleep(0.05)
    _mark("motor escuchando")
    return server


# =====================================================
# VENTANA DE ESCRITORIO (pywebview)
# =====================================================

def _windows_identity():
    """La barra de tareas agrupa la ventana con el acceso directo del instalador (mismo AppUserModelID)."""
    try:
        from ctypes import windll
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


_instance_mutex = None   # el candado vive mientras viva el proceso


def _already_running() -> bool:
    """Una sola instancia: si ya hay una abierta, se trae al frente y esta termina.

    Abrir la app dos veces dejaba dos motores en segundo plano. El candado es un mutex con nombre
    de Windows: lo crea la primera instancia y las siguientes lo encuentran ya creado. La app
    instalada y el código en desarrollo usan candados distintos, para no bloquearse entre sí.
    UNIVERSE_ALLOW_MULTIPLE=1 lo desactiva (solo para pruebas).
    """
    global _instance_mutex
    if os.environ.get("UNIVERSE_ALLOW_MULTIPLE") == "1":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        # use_last_error: el código de error se lee del mismo hilo y llamada; con windll.kernel32
        # .GetLastError() otra llamada intermedia puede pisarlo y el candado fallaría sin avisar.
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        name = "Local\\UniverseDownloader.SingleInstance" + ("" if FROZEN else ".Dev")
        ctypes.set_last_error(0)
        _instance_mutex = kernel32.CreateMutexW(None, False, name)
        if ctypes.get_last_error() != 183:   # ERROR_ALREADY_EXISTS
            return False

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.FindWindowW.restype = wintypes.HWND
        user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        hwnd = user32.FindWindowW(None, APP_NAME)
        if hwnd:
            window = wintypes.HWND(hwnd)
            user32.GetForegroundWindow.restype = wintypes.HWND
            if user32.IsIconic(window):
                user32.ShowWindow(window, 9)   # SW_RESTORE: estaba minimizada
            user32.SetForegroundWindow(window)
            # Windows puede negarle el foco a un proceso que no viene de un clic del usuario:
            # se intenta por otra vía y, si tampoco, la app parpadea en la barra de tareas.
            if user32.GetForegroundWindow() != hwnd:
                user32.SwitchToThisWindow(window, True)
            if user32.GetForegroundWindow() != hwnd:
                user32.FlashWindow(window, True)
        return True
    except Exception:
        logging.getLogger("ventana").exception("no se pudo comprobar si la app ya estaba abierta")
        return False


def _engine_alive(port: int) -> bool:
    """Hay un motor de la app respondiendo en ese puerto (modo navegador)."""
    import json
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://{HOST}:{port}/health", timeout=1.5) as r:
            return json.load(r).get("status") == "ok"
    except Exception:
        return False


def _big_icon(hwnd):
    """Ícono de 256 px en la barra de tareas (WinForms pone uno chico y se ve borroso)."""
    try:
        from ctypes import c_int, c_uint, c_void_p, c_wchar_p, windll
        ico = get_icon_path()
        if not ico or not ico.endswith('.ico'):
            return
        user32 = windll.user32
        user32.LoadImageW.restype = c_void_p
        user32.LoadImageW.argtypes = [c_void_p, c_wchar_p, c_uint, c_int, c_int, c_uint]
        user32.SendMessageW.argtypes = [c_void_p, c_uint, c_void_p, c_void_p]
        big = user32.LoadImageW(None, ico, 1, 256, 256, 0x10)     # IMAGE_ICON, LR_LOADFROMFILE
        small = user32.LoadImageW(None, ico, 1, 32, 32, 0x10)
        if big:
            user32.SendMessageW(c_void_p(hwnd), 0x80, c_void_p(1), c_void_p(big))    # WM_SETICON, ICON_BIG
        if small:
            user32.SendMessageW(c_void_p(hwnd), 0x80, c_void_p(0), c_void_p(small))  # ICON_SMALL
    except Exception:
        logging.getLogger("ventana").exception("no se pudo poner el ícono")


def _system_dark() -> bool:
    """Tema del sistema, para que la ventana no destelle en blanco antes de pintar la página."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
    except Exception:
        return False


def _downloads_dir() -> str:
    """Carpeta Descargas del usuario (la que Windows tenga configurada, aunque la haya movido)."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
            return winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
    except Exception:
        return str(Path.home() / "Downloads")


class Api:
    """Lo que la página le pide a la ventana (window.pywebview.api.*).

    Sirve para guardar resultados sin pasarlos por la página: la ventana pregunta dónde y el motor
    mueve el archivo (POST /api/save). pywebview expone los métodos públicos; lo interno va con "_".
    """

    def __init__(self):
        self._window = None
        self._prefs = DATA_DIR / "preferencias.json"
        self._last_dir = None
        try:
            import json
            saved = json.loads(self._prefs.read_text(encoding="utf-8")).get("ultima_carpeta")
            if saved and Path(saved).is_dir():
                self._last_dir = saved
        except Exception:
            pass

    def _remember(self, directory: str):
        self._last_dir = directory
        try:
            import json
            self._prefs.write_text(json.dumps({"ultima_carpeta": directory}, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def elegir_destino(self, filename: str) -> str:
        """Cuadro «Guardar como». Devuelve la ruta elegida, o "" si se canceló."""
        import webview
        ext = Path(filename).suffix
        types = (f"Archivo {ext[1:].upper()} (*{ext})", "Todos los archivos (*.*)") if ext else ()
        res = self._window.create_file_dialog(webview.FileDialog.SAVE, directory=self._last_dir or _downloads_dir(),
                                              save_filename=filename, file_types=types)
        if not res:
            return ""
        path = res if isinstance(res, str) else res[0]
        if ext and not path.lower().endswith(ext.lower()):
            path += ext
        self._remember(str(Path(path).parent))
        return path

    def elegir_carpeta(self) -> str:
        """Cuadro para elegir una carpeta (lotes: se pregunta una vez). "" si se canceló."""
        import webview
        res = self._window.create_file_dialog(webview.FileDialog.FOLDER, directory=self._last_dir or _downloads_dir())
        if not res:
            return ""
        path = res if isinstance(res, str) else res[0]
        self._remember(path)
        return path

    def mostrar_en_carpeta(self, path: str) -> bool:
        """Abre el Explorador con el archivo seleccionado."""
        import subprocess
        target = Path(path)
        if not target.exists():
            return False
        if IS_WINDOWS:
            subprocess.Popen(["explorer", "/select,", str(target)])
        else:
            subprocess.Popen(["open", "-R", str(target)])
        return True


def run_window() -> int:
    """La app como ventana propia. Al cerrarla termina todo el proceso."""
    import webview
    _mark("webview importado")

    if IS_WINDOWS:
        _windows_identity()
        if _already_running():
            return 0

    port = _free_port()
    start_server(port)

    # Los archivos terminados salen con el cuadro «Guardar como» de Windows; los enlaces externos
    # (página de una versión nueva) se abren en el navegador del sistema.
    webview.settings['ALLOW_DOWNLOADS'] = True
    webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True
    debug_port = os.environ.get("UNIVERSE_UI_DEBUG_PORT")
    if debug_port:
        webview.settings['REMOTE_DEBUGGING_PORT'] = int(debug_port)

    api = Api()
    window = webview.create_window(
        APP_NAME, f"http://{HOST}:{port}/", width=1180, height=780, min_size=(900, 600),
        background_color="#1b1b1a" if _system_dark() else "#f6f6f4", text_select=True, js_api=api,
    )
    api._window = window
    _mark("ventana creada")

    def shown():
        _mark("ventana visible")
        if IS_WINDOWS:
            try:
                _big_icon(int(window.native.Handle.ToInt64()))
            except Exception:
                logging.getLogger("ventana").exception("sin acceso a la ventana nativa")

    def loaded():
        # la página ya pintó: fin del arranque para quien lo mide
        if _TIMING and not any(m[0] == "interfaz cargada" for m in _marks):
            _mark("interfaz cargada")
            _dump_marks(os.environ.get("UNIVERSE_TIMING_OUT") or DATA_DIR / "arranque.json")
            if os.environ.get("UNIVERSE_TIMING_EXIT") == "1":
                os._exit(0)

    window.events.shown += shown
    window.events.loaded += loaded
    # private_mode=False + carpeta propia: el tema elegido (localStorage) se conserva entre sesiones
    webview.start(private_mode=False, storage_path=str(DATA_DIR / "interfaz"),
                  debug=os.environ.get("UNIVERSE_UI_DEBUG") == "1")
    os._exit(0)   # cierra también el motor y cualquier descarga en curso


# =====================================================
# MODO ANTERIOR: NAVEGADOR + BANDEJA DEL SISTEMA
# =====================================================

def run_browser() -> int:
    """Abre la interfaz en el navegador y deja un ícono en la bandeja para cerrar la app."""
    import uvicorn
    from src.app import app

    url = f'http://{HOST}:{PORT}'
    # Una sola instancia también aquí: si el motor ya responde, se abre esa en el navegador y esta
    # termina. Antes cada apertura dejaba otro proceso con su ícono en la bandeja.
    if os.environ.get("UNIVERSE_ALLOW_MULTIPLE") != "1" and _engine_alive(PORT):
        webbrowser.open(url)
        return 0
    threading.Thread(target=lambda: (time.sleep(1.5), webbrowser.open(url)), daemon=True).start()

    icon = None
    try:
        import pystray
        from PIL import Image
        icon_path = get_icon_path()
        try:
            image = Image.open(icon_path) if icon_path else Image.new('RGB', (64, 64), color='#F9BB54')
        except Exception:
            image = Image.new('RGB', (64, 64), color='#F9BB54')
        menu = pystray.Menu(
            pystray.MenuItem("Abrir en navegador", lambda: webbrowser.open(url)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Cerrar aplicación", lambda: os._exit(0)),
        )
        icon = pystray.Icon(APP_NAME, image, APP_NAME, menu)
    except ImportError:
        print("pystray o Pillow no están instalados: sin ícono en la bandeja")

    if icon:
        server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=PORT, log_level="error"))
        threading.Thread(target=server.run, daemon=True).start()
        icon.run()
    else:
        uvicorn.run(app, host=HOST, port=PORT, log_level="error")
    return 0


# =====================================================
# AUTOCOMPROBACIÓN (build.ps1)
# =====================================================

def selftest() -> int:
    """Arranca el motor en un puerto libre y comprueba lo esencial. Escribe selftest.txt en la carpeta de datos."""
    import json
    import urllib.request

    out = DATA_DIR / "selftest.txt"
    lines = [f"{APP_NAME} {APP_VERSION}"]
    ok = True
    try:
        port = _free_port()
        start_server(port)
        base = f"http://{HOST}:{port}"
        with urllib.request.urlopen(f"{base}/health", timeout=10) as r:
            lines.append(f"motor: {json.load(r).get('status')}")
        with urllib.request.urlopen(f"{base}/", timeout=10) as r:
            html = r.read().decode("utf-8")
        lines.append(f"interfaz: {len(html)} bytes")
        with urllib.request.urlopen(f"{base}/static/js/app.js", timeout=10) as r:
            lines.append(f"app.js: {len(r.read())} bytes")
        with urllib.request.urlopen(f"{base}/api/app/info", timeout=10) as r:
            lines.append(f"versión: {json.load(r).get('version')}")

        from src.api.routes import downloader
        import yt_dlp
        lines.append(f"yt-dlp: {yt_dlp.version.__version__}")
        lines.append(f"ffmpeg: {downloader.ffmpeg_path or 'NO ENCONTRADO'}")
        lines.append(f"js runtime: {', '.join(downloader.js_runtimes) or 'ninguno'}")
        if not downloader.ffmpeg_path:
            ok = False
        if IS_WINDOWS:
            import webview  # noqa: F401  (que la ventana se pueda crear en la app empaquetada)
            lines.append("ventana: pywebview disponible")
    except Exception as e:
        ok = False
        lines.append(f"ERROR: {type(e).__name__}: {e}")
    lines.append("Listo" if ok else "FALLÓ")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if ok else 1


def main() -> int:
    argv = sys.argv[1:]
    if "--selftest" in argv:
        return selftest()
    if "--browser" not in argv and IS_WINDOWS:
        try:
            import webview  # noqa: F401
        except ImportError:
            print("pywebview no está instalado: se abre en el navegador")
        else:
            return run_window()
    return run_browser()


if __name__ == "__main__":
    code = main()
    # os._exit no vacía los búferes: sin esto, la salida redirigida (build.ps1, app.log) se pierde
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except Exception:
            pass
    os._exit(code or 0)
