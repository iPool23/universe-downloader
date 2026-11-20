"""Mide el arranque de Universe Downloader, fase por fase.

    python medir_arranque.py                      # desde el código (python src/main.py)
    python medir_arranque.py --exe RUTA\\UniverseDownloader.exe   # app compilada o instalada
    python medir_arranque.py --imports            # qué módulos pesan al importar el motor
    opciones: --repeticiones N (3 por defecto)

Cómo funciona: lanza la app con UNIVERSE_TIMING=1. La app anota cuánto tarda cada fase desde el
instante en que se la lanzó (UNIVERSE_TIMING_T0) y, con UNIVERSE_TIMING_EXIT=1, se cierra sola en
cuanto la interfaz termina de cargar. UNIVERSE_ALLOW_MULTIPLE=1 permite medir aunque la app
instalada esté abierta. No toca ninguna otra instancia.

La primera pasada suele ser más lenta (archivos sin caché): se informa aparte de la mediana.
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


def lanzar(cmd, cwd):
    out = Path(tempfile.gettempdir()) / f"ud-arranque-{os.getpid()}.json"
    out.unlink(missing_ok=True)
    env = dict(os.environ, UNIVERSE_TIMING="1", UNIVERSE_TIMING_EXIT="1", UNIVERSE_ALLOW_MULTIPLE="1",
               UNIVERSE_TIMING_OUT=str(out), UNIVERSE_TIMING_T0=repr(time.time()), PYTHONIOENCODING="utf-8")
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        proc.wait(timeout=120)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise SystemExit("La app no terminó de arrancar en 120 s (¿ventana bloqueada por un diálogo?)")
    if not out.exists():
        raise SystemExit("La app no dejó marcas: ¿es una versión sin UNIVERSE_TIMING? (anterior a la 3.2)")
    marks = json.loads(out.read_text(encoding="utf-8"))
    out.unlink(missing_ok=True)
    return marks


def medir(cmd, cwd, repeticiones):
    pasadas = []
    for i in range(repeticiones):
        marks = lanzar(cmd, cwd)
        pasadas.append(marks)
        print(f"  pasada {i + 1}: " + " · ".join(f"{name} {t:.2f}" for name, t in marks))
    nombres = [name for name, _ in pasadas[0]]
    print(f"\n  {'fase':<26} {'mediana (s)':>12} {'tramo (s)':>10}")
    anterior = 0.0
    resumen = {}
    for idx, name in enumerate(nombres):
        valores = [p[idx][1] for p in pasadas if idx < len(p)]
        med = statistics.median(valores)
        print(f"  {name:<26} {med:>12.2f} {med - anterior:>10.2f}")
        resumen[name] = round(med, 2)
        anterior = med
    return resumen


def medir_imports():
    """Tiempo propio de importación agrupado por paquete (python -X importtime)."""
    proc = subprocess.run([sys.executable, "-X", "importtime", "-c", "import src.app"], cwd=REPO,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    propio = {}
    total = 0
    for line in proc.stderr.splitlines():
        if not line.startswith("import time:") or "self [us]" in line:
            continue
        try:
            self_us, _cumulative, name = line[len("import time:"):].split("|")
            us = int(self_us)
        except ValueError:
            continue
        paquete = name.strip().split(".")[0]
        propio[paquete] = propio.get(paquete, 0) + us
        total += us
    print(f"  importar el motor (src.app): {total / 1e6:.2f} s en total\n")
    print(f"  {'paquete':<22} {'ms':>8} {'%':>6}")
    for paquete, us in sorted(propio.items(), key=lambda kv: -kv[1])[:18]:
        print(f"  {paquete:<22} {us / 1000:>8.0f} {us * 100 / total:>5.1f}%")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", help="ruta de UniverseDownloader.exe (compilada o instalada)")
    ap.add_argument("--imports", action="store_true", help="desglose de importaciones del motor")
    ap.add_argument("--repeticiones", type=int, default=3)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.imports:
        print("== Importaciones del motor (desde el código)")
        medir_imports()
        return
    if args.exe:
        exe = Path(args.exe)
        print(f"== Arranque de {exe}")
        medir([str(exe)], exe.parent, args.repeticiones)
    else:
        print("== Arranque desde el código (python src/main.py)")
        medir([sys.executable, "src/main.py"], REPO, args.repeticiones)


if __name__ == "__main__":
    main()
