"""Deja deno en bin/ (Windows) o en mac/bin/ (macOS) para empaquetarlo con la app.

yt-dlp necesita un motor de JavaScript para resolver los desafíos de YouTube. En la PC de desarrollo
suele haber Node, pero la mayoría de usuarios no lo tiene: por eso el instalador trae deno, que es
un solo ejecutable.

    python scripts/setup_deno.py
"""
import hashlib
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

IS_MAC = sys.platform == "darwin"
ROOT = Path(__file__).parent.parent
BIN_DIR = ROOT / "mac" / "bin" if IS_MAC else ROOT / "bin"
EXE_NAME = "deno" if IS_MAC else "deno.exe"
ASSET = "deno-aarch64-apple-darwin.zip" if IS_MAC else "deno-x86_64-pc-windows-msvc.zip"
DENO_URL = f"https://github.com/denoland/deno/releases/latest/download/{ASSET}"


def _get(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "UniverseDownloader-build"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def setup_deno() -> Path:
    target = BIN_DIR / EXE_NAME
    if target.exists():
        print(f"deno ya está en {target}")
        return target
    print(f"Descargando deno desde {DENO_URL} ...")
    data = _get(DENO_URL, 120)
    if IS_MAC:
        expected = _get(DENO_URL + ".sha256sum", 30).decode().split()[0].lower()
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError("la suma SHA-256 de deno no coincide")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        with archive.open(EXE_NAME) as source, open(target, "wb") as dest:
            dest.write(source.read())
    target.chmod(0o755)
    print(f"deno listo: {target} ({target.stat().st_size / 1024 / 1024:.0f} MB)")
    return target


if __name__ == "__main__":
    try:
        setup_deno()
    except Exception as error:   # sin deno la app sigue funcionando donde haya Node
        print(f"No se pudo descargar deno: {error}")
        sys.exit(1)
