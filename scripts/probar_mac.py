import io
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

import requests
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
APP = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "dist").resolve()
EXE = APP / "Contents" / "MacOS" / "UniverseDownloader"
FFPROBE = APP / "Contents" / "Frameworks" / "bin" / "ffprobe"
PORT = 47391
BASE = f"http://127.0.0.1:{PORT}"
ARCHIVE = "https://archive.org/details/BigBuckBunny_124"
YOUTUBE = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
ENV_MINIMO = {"HOME": str(Path.home()), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
              "TMPDIR": os.environ.get("TMPDIR", "/tmp"), "LANG": "es_ES.UTF-8"}

resultados = []


def probar(nombre, fn, obligatorio=True):
    t = time.time()
    try:
        detalle = fn()
        ok = True
    except Exception as e:
        detalle, ok = f"{type(e).__name__}: {e}", False
    resultados.append((nombre, ok, obligatorio, round(time.time() - t, 1), detalle))
    marca = "OK " if ok else ("FALLÓ" if obligatorio else "aviso")
    print(f"[{marca}] {nombre} ({resultados[-1][3]} s): {detalle}", flush=True)
    return ok


def esperar(fn, limite, cada=0.5):
    fin = time.time() + limite
    while time.time() < fin:
        valor = fn()
        if valor:
            return valor
        time.sleep(cada)
    raise TimeoutError(f"sin respuesta en {limite} s")


def ffprobe(path):
    out = subprocess.run([str(FFPROBE), "-v", "error", "-show_entries", "stream=codec_name:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True)
    data = json.loads(out.stdout)
    return [s["codec_name"] for s in data["streams"]], float(data["format"]["duration"])


def guardar(kind, item_id, nombre):
    dest = OUT / nombre
    dest.unlink(missing_ok=True)
    r = requests.post(f"{BASE}/api/save", json={"kind": kind, "id": item_id, "dest": str(dest)}, timeout=60)
    r.raise_for_status()
    return dest


def descargar(formato, nombre):
    info = requests.get(f"{BASE}/api/scan", params={"url": ARCHIVE}, timeout=120)
    info.raise_for_status()
    calidades = [c["value"] for c in info.json().get("qualities", [])]
    cuerpo = {"url": ARCHIVE, "format": formato, "download_id": f"mac{formato}", "start_time": None,
              "end_time": "00:08", "quality": (360 if 360 in calidades else max(calidades)) if formato == "mp4" else None,
              "audio_quality": 192 if formato == "mp3" else None}
    did = requests.post(f"{BASE}/api/download/start", json=cuerpo, timeout=60).json()["download_id"]

    def terminado():
        p = requests.get(f"{BASE}/api/download/progress/{did}", timeout=30).json()
        if p.get("status") == "error":
            raise RuntimeError(p.get("error"))
        return p if p.get("status") == "completed" else None

    esperar(terminado, 240)
    dest = guardar("download", did, nombre)
    codecs, duracion = ffprobe(dest)
    if not 6 <= duracion <= 11:
        raise RuntimeError(f"duración inesperada: {duracion:.1f} s")
    return f"{dest.stat().st_size / 1024:.0f} KB, {duracion:.1f} s, {'+'.join(codecs)}"


def convertir_imagen():
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), (227, 154, 23)).save(buf, "PNG")
    r = requests.post(f"{BASE}/api/convert-image", params={"target_format": "webp", "quality": 80},
                      files={"file": ("prueba.png", buf.getvalue(), "image/png")}, timeout=60)
    r.raise_for_status()
    if r.content[:4] != b"RIFF" or r.content[8:12] != b"WEBP":
        raise RuntimeError("la respuesta no es un WebP")
    return f"PNG {len(buf.getvalue())} B -> WebP {len(r.content)} B"


def comprimir_pdf():
    buf = io.BytesIO()
    Image.new("RGB", (1240, 1754), (240, 240, 240)).save(buf, "PDF", resolution=150)
    r = requests.post(f"{BASE}/api/pdf/compress", data={"quality": "60"},
                      files={"file": ("prueba.pdf", buf.getvalue(), "application/pdf")}, timeout=60)
    r.raise_for_status()
    cid = r.json()["compress_id"]

    def terminado():
        p = requests.get(f"{BASE}/api/pdf/compress/progress/{cid}", timeout=30).json()
        if p.get("status") == "error":
            raise RuntimeError(p.get("error"))
        return p if p.get("status") == "completed" else None

    esperar(terminado, 120)
    dest = guardar("pdf", cid, "prueba-comprimido.pdf")
    if dest.read_bytes()[:5] != b"%PDF-":
        raise RuntimeError("el resultado no es un PDF")
    return f"{len(buf.getvalue())} B -> {dest.stat().st_size} B"


def convertir_h264():
    origen = OUT / "prueba.mp4"
    with open(origen, "rb") as f:
        r = requests.post(f"{BASE}/api/upload-convert", files={"file": ("prueba.mp4", f, "video/mp4")}, timeout=120)
    r.raise_for_status()
    cid = r.json()["convert_id"]

    def terminado():
        p = requests.get(f"{BASE}/api/convert/progress/{cid}", timeout=30).json()
        if p.get("status") == "error":
            raise RuntimeError(p.get("error"))
        return p if p.get("status") == "completed" else None

    esperar(terminado, 240)
    dest = guardar("convert", cid, "prueba-h264.mp4")
    codecs, duracion = ffprobe(dest)
    if "h264" not in codecs:
        raise RuntimeError(f"códecs inesperados: {codecs}")
    return f"{dest.stat().st_size / 1024:.0f} KB, {'+'.join(codecs)}"


def escanear_youtube():
    r = requests.get(f"{BASE}/api/scan", params={"url": YOUTUBE}, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(r.json().get("detail"))
    return f"«{r.json().get('title')}»"


def probar_app():
    arranque = OUT / "arranque.json"
    arranque.unlink(missing_ok=True)
    env = dict(ENV_MINIMO, UNIVERSE_PORT=str(PORT), UNIVERSE_TIMING="1", UNIVERSE_TIMING_OUT=str(arranque),
               UNIVERSE_TIMING_T0=str(time.time()))
    app = subprocess.Popen([str(EXE)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        def ventana():
            if app.poll() is not None:
                raise RuntimeError(f"la app se cerró sola (código {app.returncode})")
            return arranque.exists() and json.loads(arranque.read_text(encoding="utf-8"))

        if not probar("ventana con la interfaz cargada",
                      lambda: ", ".join(f"{n} {s} s" for n, s in esperar(ventana, 120))):
            return
        time.sleep(1)
        subprocess.run(["screencapture", "-x", str(OUT / "ventana-mac.png")], check=False)
        probar("versión", lambda: requests.get(f"{BASE}/api/app/info", timeout=30).json())
        probar("descarga MP4 (tramo de 8 s)", lambda: descargar("mp4", "prueba.mp4"))
        probar("descarga MP3 (tramo de 8 s)", lambda: descargar("mp3", "prueba.mp3"))
        probar("conversión a H.264", convertir_h264)
        probar("imagen PNG a WebP", convertir_imagen)
        probar("compresión de PDF", comprimir_pdf)
        probar("escaneo de YouTube", escanear_youtube, obligatorio=False)
        probar("consulta de actualizaciones",
               lambda: requests.get(f"{BASE}/api/update/check", params={"force": "true"}, timeout=60).json(),
               obligatorio=False)
    finally:
        app.terminate()
        try:
            app.wait(15)
        except subprocess.TimeoutExpired:
            app.kill()


def probar_actualizacion():
    tmp = Path(tempfile.mkdtemp(prefix="ud-actualizar-"))
    instalada = tmp / "Aplicaciones" / APP.name
    instalada.parent.mkdir()
    subprocess.run(["ditto", str(APP), str(instalada)], check=True)
    marca = instalada / "Contents" / "Resources" / "version-vieja.txt"
    marca.write_text("vieja", encoding="utf-8")
    paquete = tmp / "UniverseDownloader-9.9.9-mac-arm64.zip"
    subprocess.run(["ditto", "-c", "-k", "--keepParent", str(APP), str(paquete)], check=True)
    codigo = (f"import sys; sys.path.insert(0, {str(REPO)!r}); from pathlib import Path; "
              f"from src.services import updater; updater.app_bundle = lambda: Path({str(instalada)!r}); "
              f"updater.run_installer(Path({str(paquete)!r}))")
    subprocess.run([sys.executable, "-c", codigo], check=True, cwd=str(REPO))
    try:
        esperar(lambda: not marca.exists() and instalada.exists()
                and not Path(str(instalada) + ".old").exists(), 90)
        esperar(lambda: subprocess.run(["pgrep", "-f", str(instalada / "Contents" / "MacOS")],
                                       capture_output=True).returncode == 0, 60)
        subprocess.run(["codesign", "--verify", "--deep", "--strict", str(instalada)], check=True)
        return "reemplazó el .app, la firma es válida y la volvió a abrir"
    finally:
        subprocess.run(["pkill", "-f", str(instalada / "Contents" / "MacOS")], check=False)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    probar_app()
    probar("actualización (cambia el .app y lo reabre)", probar_actualizacion)
    resumen = [{"prueba": n, "ok": ok, "obligatoria": ob, "segundos": s, "detalle": str(d)}
               for n, ok, ob, s, d in resultados]
    (OUT / "pruebas-mac.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    fallidas = [n for n, ok, ob, *_ in resultados if ob and not ok]
    print("\nFallaron: " + ", ".join(fallidas) if fallidas else "\nTodas las pruebas obligatorias pasaron")
    return 1 if fallidas else 0


if __name__ == "__main__":
    sys.exit(main())
