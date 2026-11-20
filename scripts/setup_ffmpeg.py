"""Deja FFmpeg en bin/ para empaquetarlo con la app de Windows.

    python scripts/setup_ffmpeg.py

Se usa la compilación «shared» de BtbN (GPL, con libx264 y libmp3lame): ffmpeg.exe y ffprobe.exe
pesan menos de 1 MB cada uno y comparten las bibliotecas (avcodec, avformat…) como DLL. La
compilación estática que se usaba antes llevaba esas bibliotecas DENTRO de cada ejecutable, así que
el instalador cargaba dos veces lo mismo: 386 MB en disco y 87 MB del instalador, frente a 187 MB y
unos 44 MB. Mismos códecs. ffplay.exe no se copia: la app no lo usa.

Si en bin/ hay ejecutables estáticos de antes, se apartan en bin/estatico/ en vez de borrarlos.
"""
import io
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

BIN_DIR = Path(__file__).parent.parent / "bin"
FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip"
STATIC_LIMIT = 50 * 1024 * 1024   # un ffmpeg.exe mayor que esto es de la compilación estática
SKIP = {"ffplay.exe"}


def is_shared_build() -> bool:
    exe = BIN_DIR / "ffmpeg.exe"
    return exe.exists() and exe.stat().st_size < STATIC_LIMIT and any(BIN_DIR.glob("avcodec-*.dll"))


def setup_ffmpeg() -> bool:
    if is_shared_build():
        print(f"FFmpeg (compartido) ya está en {BIN_DIR}")
        return True

    print(f"Descargando FFmpeg desde {FFMPEG_URL} ...")
    request = urllib.request.Request(FFMPEG_URL, headers={"User-Agent": "UniverseDownloader-build"})
    with urllib.request.urlopen(request, timeout=600) as response:
        data = response.read()

    BIN_DIR.mkdir(exist_ok=True)
    # lo que hubiera de la compilación estática se aparta, no se borra
    old = [BIN_DIR / n for n in ("ffmpeg.exe", "ffprobe.exe", "ffplay.exe") if (BIN_DIR / n).exists()]
    if old:
        backup = BIN_DIR / "estatico"
        backup.mkdir(exist_ok=True)
        for f in old:
            shutil.move(str(f), str(backup / f.name))
        print(f"Ejecutables anteriores apartados en {backup}")
    for stale in BIN_DIR.glob("av*.dll"):   # DLL de una versión anterior de FFmpeg: no deben mezclarse
        stale.unlink()
    for stale in list(BIN_DIR.glob("sw*.dll")) + list(BIN_DIR.glob("postproc-*.dll")):
        stale.unlink()

    copied = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for item in archive.infolist():
            name = item.filename.rsplit("/", 1)[-1]
            if "/bin/" not in item.filename or item.is_dir() or name in SKIP:
                continue
            with archive.open(item) as source, open(BIN_DIR / name, "wb") as dest:
                shutil.copyfileobj(source, dest)
            copied += item.file_size
    print(f"FFmpeg listo en {BIN_DIR} ({copied / 1024 / 1024:.0f} MB)")
    return is_shared_build()


if __name__ == "__main__":
    try:
        ok = setup_ffmpeg()
    except Exception as error:
        print(f"No se pudo preparar FFmpeg: {error}")
        ok = False
    sys.exit(0 if ok else 1)
