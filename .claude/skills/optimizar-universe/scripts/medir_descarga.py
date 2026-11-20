"""Cronometra una descarga real fase por fase, usando el motor igual que lo usa la interfaz.

    python medir_descarga.py URL                       # video completo, mejor calidad
    python medir_descarga.py URL --fin 00:20           # solo un tramo (lo normal para medir rápido)
    python medir_descarga.py URL --calidad 360 --formato mp3 --repeticiones 2

Informa: cuánto tarda el escaneo (y el segundo escaneo, que debería salir de la caché), cuánto pasa
desde que se pulsa «Descargar» hasta el primer avance, cuánto dura cada estado que ve el usuario y
el total. Sirve para saber dónde se va el tiempo antes de tocar nada y para comparar después.

Arranca un motor propio en un puerto libre; no usa ni toca la app que esté abierta. El archivo
descargado se borra al terminar. Si la red bloquea el sitio (YouTube puede pedir iniciar sesión
según la IP), el error se muestra tal cual lo vería el usuario: eso no es un fallo de rendimiento.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


def http(base, path, body=None):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"} if body is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def una_pasada(base, args, n):
    q = urllib.parse.quote(args.url, safe="")
    t = time.perf_counter()
    status, info = http(base, f"/api/scan?url={q}")
    t_scan = time.perf_counter() - t
    if status != 200:
        print(f"  escaneo: {t_scan:.2f} s -> ERROR: {info.get('detail')}")
        return None
    t = time.perf_counter()
    http(base, f"/api/scan?url={q}")
    t_scan2 = time.perf_counter() - t
    calidades = [c["value"] for c in info.get("qualities", [])]
    calidad = args.calidad or (calidades[0] if calidades else None)
    print(f"  «{info.get('title')}»  duración {info.get('duration')} s  calidades {calidades[:6]}")
    print(f"  escaneo: {t_scan:.2f} s   (repetido, desde la caché: {t_scan2 * 1000:.0f} ms)")

    t0 = time.perf_counter()
    _, started = http(base, "/api/download/start", {
        "url": args.url, "format": args.formato, "download_id": f"medir{n}",
        "start_time": args.inicio, "end_time": args.fin,
        "quality": calidad if args.formato == "mp4" else None,
        "audio_quality": 192 if args.formato == "mp3" else None})
    did = started["download_id"]
    estados, ultimo, primer_avance = [], None, None
    while True:
        time.sleep(0.1)
        _, p = http(base, f"/api/download/progress/{did}")
        ahora = time.perf_counter() - t0
        clave = p.get("status") + (f" ({p['phase']})" if p.get("phase") else "")
        if clave != ultimo:
            estados.append([clave, ahora])
            ultimo = clave
        if primer_avance is None and (p.get("downloaded_bytes") or p.get("percent")):
            primer_avance = ahora
        if p.get("status") in ("completed", "error", "cancelled"):
            break
        if ahora > args.limite:
            print(f"  (cortado a los {args.limite} s)")
            http(base, f"/api/download/cancel/{did}", {})
            return None
    total = time.perf_counter() - t0
    if p.get("status") != "completed":
        print(f"  descarga: ERROR a los {total:.1f} s: {p.get('error')}")
        return None

    t = time.perf_counter()
    with urllib.request.urlopen(base + f"/api/download/file/{did}") as r:   # también borra el archivo de trabajo
        size = len(r.read())
    t_file = time.perf_counter() - t
    print(f"  hasta el primer avance: {primer_avance if primer_avance is not None else float('nan'):.2f} s")
    for (estado, inicio), siguiente in zip(estados, estados[1:] + [[None, total]]):
        print(f"    {estado:<28} {siguiente[1] - inicio:>7.2f} s")
    print(f"  descarga: {total:.2f} s   archivo: {size / 1048576:.1f} MB   entregarlo por HTTP: {t_file:.2f} s")
    return {"escaneo": t_scan, "descarga": total, "entrega": t_file, "mb": size / 1048576}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--inicio")
    ap.add_argument("--fin")
    ap.add_argument("--calidad", type=int)
    ap.add_argument("--formato", default="mp4", choices=["mp4", "mp3"])
    ap.add_argument("--repeticiones", type=int, default=1)
    ap.add_argument("--limite", type=int, default=600, help="segundos antes de cancelar la descarga")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    sys.path.insert(0, str(REPO))
    real, sys.stdout = sys.stdout, open(os.devnull, "w")     # el motor y yt-dlp imprimen mucho: fuera del informe
    try:
        from src import main as app_main
        from src.api import routes
        port = app_main._free_port()
        app_main.start_server(port)
    finally:
        salida_motor, sys.stdout = sys.stdout, real
    base = f"http://127.0.0.1:{port}"

    print(f"== {args.url}" + (f"  tramo {args.inicio or '00:00'}–{args.fin or 'fin'}" if args.inicio or args.fin else ""))
    for n in range(args.repeticiones):
        if args.repeticiones > 1:
            print(f"-- pasada {n + 1}")
            routes._scan_cache.clear()        # que cada pasada mida un escaneo de verdad
        sys.stdout = salida_motor             # yt-dlp escribe por print durante la descarga
        try:
            real.flush()
            resultado = None
            sys.stdout = real
            resultado = una_pasada(base, args, n)
        finally:
            sys.stdout = real
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
