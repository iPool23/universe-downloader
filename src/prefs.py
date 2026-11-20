"""Preferencias del usuario que deben sobrevivir de una sesión a otra.

Viven en un archivo de la carpeta de datos y no en el almacenamiento de la página (localStorage)
porque la ventana abre el motor en un puerto distinto cada vez: para el navegador cada puerto es un
sitio diferente, y lo que la página guardó en una sesión no lo encuentra en la siguiente.
"""
import json
import threading

from src.config import DATA_DIR

_FILE = DATA_DIR / "preferencias.json"
_lock = threading.Lock()


def load() -> dict:
    try:
        data = json.loads(_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def update(**changes) -> dict:
    """Guarda las claves indicadas (None borra la clave) y devuelve las preferencias resultantes."""
    with _lock:
        data = load()
        for key, value in changes.items():
            if value is None:
                data.pop(key, None)
            else:
                data[key] = value
        try:
            _FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass   # sin permiso de escritura: la preferencia vale solo para esta sesión
        return data


def theme() -> str:
    """'dark', 'light' o '' si el usuario nunca eligió (se sigue el tema del sistema)."""
    value = load().get("tema")
    return value if value in ("dark", "light") else ""
