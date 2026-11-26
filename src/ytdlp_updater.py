import compileall
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import logging
import operator
import os
import re
import shutil
import sys
import threading
import time
import urllib.request
import zipfile
from pathlib import PurePosixPath

from src.config import DATA_DIR, FROZEN
from src.version import APP_VERSION

RAIZ = DATA_DIR / "yt-dlp"
ESTADO = RAIZ / "estado.json"
PYPI = "https://pypi.org/pypi/yt-dlp/json"
ORIGEN_PERMITIDO = "https://files.pythonhosted.org/"
UA = "UniverseDownloader-ytdlp-updater"
CADA = 24 * 60 * 60
ESPERA_INICIAL = 20
CONSERVAR = 2
TAMANO_MAXIMO = 30 * 1024 * 1024
OPERADORES = {">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt,
              "==": operator.eq, "!=": operator.ne}

log = logging.getLogger("yt-dlp")
_origen = {"version": None, "actualizada": False, "empaquetada": None}


def _clave(version):
    return tuple(int(parte) for parte in re.findall(r"\d+", str(version or ""))) or (0,)


def _leer():
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _escribir(estado):
    RAIZ.mkdir(parents=True, exist_ok=True)
    temporal = ESTADO.with_suffix(".tmp")
    temporal.write_text(json.dumps(estado, indent=2), encoding="utf-8")
    os.replace(temporal, ESTADO)


def _forzado():
    return os.environ.get("UNIVERSE_YTDLP_UPDATE") == "1"


def version_empaquetada():
    try:
        rutas = [ruta for ruta in sys.path if not str(ruta).startswith(str(RAIZ))]
        paquete = importlib.machinery.PathFinder.find_spec("yt_dlp", rutas)
        spec = importlib.machinery.PathFinder.find_spec("yt_dlp.version", list(paquete.submodule_search_locations))
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return modulo.__version__
    except Exception:
        log.exception("no se pudo leer la versión de yt-dlp que trae la app")
        return "0"


def activar():
    if "yt_dlp" in sys.modules:
        return
    try:
        estado = _leer()
        version = estado.get("activa")
        if not version or version in estado.get("malas", []):
            return
        carpeta = RAIZ / version
        if not (carpeta / "yt_dlp" / "__init__.py").is_file():
            return
        empaquetada = version_empaquetada()
        if empaquetada == "0" and estado.get("app") != APP_VERSION:
            return
        if _clave(version) <= _clave(empaquetada):
            return
        sys.path.insert(0, str(carpeta))
        try:
            import yt_dlp
            cargada = yt_dlp.version.__version__
            if _clave(cargada) != _clave(version):
                raise ImportError(f"se cargó {cargada} en vez de {version}")
            _origen.update(version=cargada, actualizada=True, empaquetada=empaquetada)
            log.info("yt-dlp %s (actualizado; la app trae %s)", cargada, empaquetada)
        except Exception:
            log.exception("yt-dlp %s no carga: se usa el que trae la app", version)
            if str(carpeta) in sys.path:
                sys.path.remove(str(carpeta))
            for nombre in [n for n in sys.modules if n == "yt_dlp" or n.startswith("yt_dlp.")]:
                del sys.modules[nombre]
            estado.setdefault("malas", []).append(version)
            estado.pop("activa", None)
            _escribir(estado)
    except Exception:
        log.exception("no se pudo activar el yt-dlp actualizado")


def origen():
    if _origen["version"] is None:
        try:
            import yt_dlp
            _origen["version"] = yt_dlp.version.__version__
        except Exception:
            pass
    if _origen["empaquetada"] is None:
        _origen["empaquetada"] = version_empaquetada()
    return dict(_origen)


def comprobar_en_segundo_plano():
    if not FROZEN and not _forzado():
        return
    threading.Thread(target=_comprobar, daemon=True, name="yt-dlp-update").start()


def _python_compatible(requisito):
    for simbolo, version in re.findall(r"(>=|<=|==|!=|>|<)\s*(\d+(?:\.\d+)*)", requisito or ""):
        objetivo = _clave(version)
        if not OPERADORES[simbolo](tuple(sys.version_info[:len(objetivo)]), objetivo):
            return False
    return True


def _abrir(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30)


def _bajar(url, tamano):
    if not url.startswith(ORIGEN_PERMITIDO):
        raise ValueError(f"origen no permitido: {url}")
    if tamano and tamano > TAMANO_MAXIMO:
        raise ValueError("el paquete es demasiado grande")
    with _abrir(url) as respuesta:
        contenido = respuesta.read(TAMANO_MAXIMO + 1)
    if len(contenido) > TAMANO_MAXIMO:
        raise ValueError("el paquete es demasiado grande")
    return contenido


def _extraer(contenido, version):
    RAIZ.mkdir(parents=True, exist_ok=True)
    temporal = RAIZ / f".{version}.tmp"
    shutil.rmtree(temporal, ignore_errors=True)
    with zipfile.ZipFile(io.BytesIO(contenido)) as rueda:
        for nombre in rueda.namelist():
            partes = PurePosixPath(nombre).parts
            if not partes or partes[0] != "yt_dlp" or ".." in partes or nombre.endswith("/"):
                continue
            ruta = temporal.joinpath(*partes)
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(rueda.read(nombre))
    texto = (temporal / "yt_dlp" / "version.py").read_text(encoding="utf-8") if (temporal / "yt_dlp" / "version.py").is_file() else ""
    encontrada = re.search(r"__version__\s*=\s*['\"]([^'\"]+)", texto)
    if not (temporal / "yt_dlp" / "__init__.py").is_file() or not encontrada or _clave(encontrada.group(1)) != _clave(version):
        shutil.rmtree(temporal, ignore_errors=True)
        raise ValueError("el paquete descargado no es el esperado")
    compileall.compile_dir(str(temporal / "yt_dlp"), quiet=1)
    destino = RAIZ / version
    shutil.rmtree(destino, ignore_errors=True)
    os.replace(temporal, destino)


def _limpiar(estado):
    carpetas = sorted((c for c in RAIZ.iterdir() if c.is_dir() and not c.name.startswith(".")),
                      key=lambda c: _clave(c.name), reverse=True)
    for carpeta in carpetas[CONSERVAR:]:
        if carpeta.name != estado.get("activa"):
            shutil.rmtree(carpeta, ignore_errors=True)


def _comprobar():
    time.sleep(float(os.environ.get("UNIVERSE_YTDLP_DELAY", ESPERA_INICIAL)))
    try:
        estado = _leer()
        if not _forzado() and time.time() - estado.get("comprobado", 0) < CADA:
            return
        import yt_dlp
        en_uso = yt_dlp.version.__version__
        with _abrir(PYPI) as respuesta:
            datos = json.load(respuesta)
        nueva = datos["info"]["version"]
        estado["comprobado"] = time.time()
        if (_clave(nueva) <= _clave(en_uso) or nueva in estado.get("malas", [])
                or not _python_compatible(datos["info"].get("requires_python"))):
            _escribir(estado)
            log.info("yt-dlp al día (%s; en PyPI %s)", en_uso, nueva)
            return
        rueda = next(u for u in datos["urls"]
                     if u.get("packagetype") == "bdist_wheel" and u["filename"].endswith("-py3-none-any.whl"))
        contenido = _bajar(rueda["url"], rueda.get("size"))
        if hashlib.sha256(contenido).hexdigest() != rueda["digests"]["sha256"]:
            raise ValueError("el SHA-256 no coincide con el que publica PyPI")
        _extraer(contenido, nueva)
        estado.update(activa=nueva, app=APP_VERSION)
        _escribir(estado)
        _limpiar(estado)
        log.info("yt-dlp %s descargado: se usará en la próxima apertura (ahora %s)", nueva, en_uso)
    except Exception:
        log.exception("no se pudo actualizar yt-dlp")
