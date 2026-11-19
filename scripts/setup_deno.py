"""Deja deno.exe en bin/ para empaquetarlo con la app de Windows.

yt-dlp necesita un motor de JavaScript para resolver los desafíos de YouTube. En la PC de desarrollo
suele haber Node, pero la mayoría de usuarios no lo tiene: por eso el instalador trae deno, que es
un solo ejecutable.

    python scripts/setup_deno.py
"""
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

BIN_DIR = Path(__file__).parent.parent / "bin"
DENO_URL = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"


def setup_deno() -> Path:
    target = BIN_DIR / "deno.exe"
    if target.exists():
        print(f"deno ya está en {target}")
        return target
    print(f"Descargando deno desde {DENO_URL} ...")
    request = urllib.request.Request(DENO_URL, headers={"User-Agent": "UniverseDownloader-build"})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        BIN_DIR.mkdir(exist_ok=True)
        with archive.open("deno.exe") as source, open(target, "wb") as dest:
            dest.write(source.read())
    print(f"deno listo: {target} ({target.stat().st_size / 1024 / 1024:.0f} MB)")
    return target


if __name__ == "__main__":
    try:
        setup_deno()
    except Exception as error:   # sin deno la app sigue funcionando donde haya Node
        print(f"No se pudo descargar deno: {error}")
        sys.exit(1)
