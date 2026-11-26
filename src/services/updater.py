"""Actualizaciones desde GitHub Releases.

Flujo: la app consulta la última release; si es más nueva que APP_VERSION la interfaz muestra un
aviso. Al aceptar, descarga el instalador (en Mac, el zip del .app), comprueba su SHA256 contra
SHA256SUMS.txt de la misma release y lo ejecuta; el instalador reemplaza la app y la vuelve a abrir.

Solo se descarga desde https://github.com/<repo>/releases/download/… y nunca sin suma verificada.
"""

import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

log = logging.getLogger("updater")

API = "https://api.github.com/repos/{repo}/releases/latest"
DOWNLOAD_PREFIX = "https://github.com/{repo}/releases/download/"
UA = "UniverseDownloader-updater"
ASSET_RE = re.compile(r"^UniverseDownloader-Setup-(?P<ver>\d+(?:\.\d+)*)\.exe$")
MAC_ASSET_RE = re.compile(r"^UniverseDownloader-(?P<ver>\d+(?:\.\d+)*)-mac-arm64\.zip$")
SUMS_NAME = "SHA256SUMS.txt"
MAX_BYTES = 2 * 1024 ** 3


def parse_version(v):
    """'v1.2.10' -> (1, 2, 10)"""
    return tuple(int(x) for x in re.findall(r"\d+", str(v))) or (0,)


def is_newer(latest, current):
    return parse_version(latest) > parse_version(current)


def app_bundle():
    exe = Path(sys.executable).resolve()
    return next((p for p in exe.parents if p.suffix == ".app"), None)


def can_install():
    """Solo la app instalada se actualiza sola (en desarrollo se usa git)."""
    if not getattr(sys, "frozen", False):
        return False
    if sys.platform == "win32":
        return True
    if sys.platform == "darwin":
        bundle = app_bundle()
        return bool(bundle) and "/AppTranslocation/" not in str(bundle) and os.access(bundle.parent, os.W_OK)
    return False


def pick_asset(assets):
    """El archivo de la release para este sistema: el instalador de Windows o el zip del .app."""
    pattern = MAC_ASSET_RE if sys.platform == "darwin" else ASSET_RE
    for a in assets:
        if pattern.match(a.get("name", "")):
            return a
    return None


def _open(url, timeout=15):
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout)


def check(repo, current_version):
    """Devuelve la actualización disponible o None. Nunca lanza: si falla, lo anota y devuelve None."""
    try:
        with _open(API.format(repo=repo)) as r:
            rel = json.load(r)
    except Exception as e:
        log.info("sin acceso a las actualizaciones: %s", e)
        return None
    ver = rel.get("tag_name", "")
    if not is_newer(ver, current_version):
        return None
    info = {"version": ver.lstrip("v"), "notes": rel.get("body") or "", "page": rel.get("html_url", ""),
            "name": "", "url": "", "sums_url": "", "size": 0}
    asset = pick_asset(rel.get("assets", []))
    sums = next((a for a in rel.get("assets", []) if a.get("name") == SUMS_NAME), None)
    if not asset or not sums:
        # release sin instalador verificable para este sistema: se avisa, pero se instala a mano
        log.warning("release %s sin archivo para este sistema o sin %s", ver, SUMS_NAME)
        return info
    prefix = DOWNLOAD_PREFIX.format(repo=repo)
    urls = [asset.get("browser_download_url", ""), sums.get("browser_download_url", "")]
    if not all(u.startswith(prefix) for u in urls):
        log.warning("release %s: direcciones de descarga inesperadas", ver)
        return info
    info.update(name=asset["name"], url=urls[0], sums_url=urls[1], size=int(asset.get("size") or 0))
    return info


def expected_sha256(sums_url, name):
    with _open(sums_url) as r:
        for line in r.read().decode("utf-8", "ignore").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[-1].lstrip("*") == name:
                return parts[0].lower()
    return None


def download(url, dest, on_progress=None, max_bytes=MAX_BYTES):
    """Descarga a dest (en partes) y devuelve el SHA256 del archivo."""
    h = hashlib.sha256()
    done = 0
    with _open(url, timeout=60) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            done += len(chunk)
            if done > max_bytes:
                raise RuntimeError("la descarga es más grande de lo esperado")
            f.write(chunk)
            h.update(chunk)
            if on_progress:
                on_progress(done, total)
    return h.hexdigest()


def fetch_and_verify(upd, on_progress=None):
    """Descarga el instalador a %TEMP% y comprueba la suma. Devuelve la ruta."""
    if not upd.get("url") or not upd.get("sums_url"):
        raise RuntimeError("esta versión no trae un instalador que se pueda verificar")
    want = expected_sha256(upd["sums_url"], upd["name"])
    if not want:
        raise RuntimeError(f"{SUMS_NAME} no tiene la suma de {upd['name']}")
    dest = Path(tempfile.gettempdir()) / "universe-downloader-update" / upd["name"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    got = download(upd["url"], dest, on_progress)
    if got != want:
        dest.unlink(missing_ok=True)
        raise RuntimeError("la suma SHA256 del instalador no coincide: descarga descartada")
    return dest


def run_installer(path):
    """Lanza el instalador en un proceso aparte y vuelve a abrir la app al terminar.

    Un .cmd espera un par de segundos (la app se cierra sola justo después de llamar aquí),
    ejecuta el instalador mostrando solo el progreso y reabre el exe instalado.
    En Mac un script espera a que la app cierre, cambia el .app por el del zip y la reabre.
    """
    if sys.platform == "darwin":
        return _mac_swap(path)
    flags = "/SILENT /SUPPRESSMSGBOXES /NORESTART /SP- /CLOSEAPPLICATIONS"
    lines = ["@echo off", "ping -n 3 127.0.0.1 >nul", f'start "" /wait "{path}" {flags}']
    if getattr(sys, "frozen", False):
        lines.append(f'start "" "{Path(sys.executable).resolve()}"')
    bat = Path(path).parent / "instalar.cmd"
    bat.write_text("\r\n".join(lines) + "\r\n", encoding="mbcs")
    subprocess.Popen(["cmd", "/c", str(bat)], close_fds=True, cwd=str(bat.parent),
                     creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)


def _mac_swap(zip_path):
    import shlex
    bundle = app_bundle()
    if not bundle:
        raise RuntimeError("no se encontró la app instalada")
    work = Path(tempfile.mkdtemp(prefix="universe-downloader-upd-"))
    app, old, out = shlex.quote(str(bundle)), shlex.quote(str(bundle) + ".old"), shlex.quote(str(work / "out"))
    script = work / "actualizar.sh"
    script.write_text(f"""#!/bin/sh
i=0; while kill -0 {os.getpid()} 2>/dev/null && [ $i -lt 60 ]; do sleep 1; i=$((i+1)); done
ditto -x -k {shlex.quote(str(zip_path))} {out} || exit 1
NEW=$(find {out} -maxdepth 1 -name "*.app" | head -n 1)
[ -n "$NEW" ] || exit 1
codesign --verify --deep --strict "$NEW" || exit 1
rm -rf {old}
mv {app} {old} || exit 1
if ! mv "$NEW" {app}; then mv {old} {app}; open {app}; exit 1; fi
rm -rf {old}
xattr -dr com.apple.quarantine {app} 2>/dev/null
open {app}
rm -rf {shlex.quote(str(work))}
""", encoding="utf-8")
    os.chmod(script, 0o755)
    subprocess.Popen(["/bin/sh", str(script)], start_new_session=True, close_fds=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
