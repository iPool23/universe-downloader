"""Mide cuánto tarda cada vista previa del editor de imagen y en qué se va ese tiempo.

    python medir_vista_previa.py                 # fotos de 2, 12 y 24 megapíxeles a WebP, JPG y PNG
    python medir_vista_previa.py --mp 12 --formatos webp avif --repeticiones 5
    python medir_vista_previa.py --imagen C:\\Windows\\Web\\Wallpaper\\Windows\\img0.jpg
    python medir_vista_previa.py --ajustes --imagen foto1.jpg foto2.jpg

Cada vez que se mueve un control, el editor manda la imagen entera al motor y este la decodifica,
la convierte y devuelve el resultado. Sin --ajustes, el script separa ese tiempo en tres partes:

  decodificar  abrir la imagen original (lo mismo en cada ajuste: se podría hacer una sola vez)
  codificar    generar el formato de salida (cambia con cada ajuste: no se puede evitar)
  resto        enviar la imagen por HTTP, guardarla en disco y devolver la respuesta

«decodificar» y «resto» son lo que se ahorraría si el motor recordara la imagen entre ajustes.

Con --ajustes no arranca el motor: compara opciones del codificador (el esfuerzo de WebP, el nivel
de compresión de PNG, la pasada extra de JPG) y dice cuánto tarda cada una y cuánto pesa el
resultado frente a la opción que usa hoy la app, marcada con «hoy».

Con --rafaga N mide lo que pasa al mover un control varias veces seguidas: cuánto tarda en llegar
la última vista previa (la única que se va a ver), cuánto rato deja el motor de responder a otras
peticiones mientras convierte (el avance de una descarga, por ejemplo) y cuánto tarda un lote.

    python medir_vista_previa.py --rafaga 3 --imagen C:\\Windows\\Web\\Wallpaper\\Windows\\img0.jpg

Sin --imagen las fotos de prueba se generan aquí (degradado con ruido): es el peor caso para un
compresor, así que conviene repetir con fotos reales antes de decidir nada.
"""
import argparse
import io
import os
import statistics
import sys
import time
import urllib.request
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
MB = 1024 * 1024

AJUSTES = {
    "webp": [(f"method={m}", {"format": "WEBP", "quality": 85, "method": m}, m == 4) for m in range(7)],
    "png": [
        ("compress_level=1", {"format": "PNG", "compress_level": 1}, False),
        ("compress_level=3", {"format": "PNG", "compress_level": 3}, False),
        ("compress_level=6", {"format": "PNG", "compress_level": 6}, False),
        ("optimize=True", {"format": "PNG", "optimize": True}, True),
    ],
    "jpg": [
        ("optimize=False", {"format": "JPEG", "quality": 85}, False),
        ("optimize=True", {"format": "JPEG", "quality": 85, "optimize": True}, True),
    ],
}


def foto(megapixeles: float):
    from PIL import Image
    w = int((megapixeles * 1_000_000 * 4 / 3) ** 0.5)
    h = int(w * 3 / 4)
    canales = []
    for i, sigma in enumerate((34, 28, 40)):
        grad = Image.linear_gradient("L").rotate(90 * i).resize((w, h))
        ruido = Image.effect_noise((w, h), sigma)
        canales.append(Image.blend(grad, ruido, 0.35))
    img = Image.merge("RGB", canales)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    return buf.getvalue(), w, h


def fotos(args):
    from PIL import Image
    if args.imagen:
        for ruta in args.imagen:
            datos = Path(ruta).read_bytes()
            with Image.open(io.BytesIO(datos)) as img:
                yield datos, img.width, img.height, Path(ruta).name
    else:
        for mp in args.mp:
            datos, w, h = foto(mp)
            yield datos, w, h, "generada"


def enviar(base, datos, formato, calidad=85):
    limite = uuid.uuid4().hex
    cuerpo = (f"--{limite}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"foto.jpg\"\r\n"
              f"Content-Type: image/jpeg\r\n\r\n").encode() + datos + f"\r\n--{limite}--\r\n".encode()
    req = urllib.request.Request(f"{base}/api/convert-image?target_format={formato}&quality={calidad}", data=cuerpo,
                                 headers={"Content-Type": f"multipart/form-data; boundary={limite}"})
    t = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as r:
        salida = r.read()
    return time.perf_counter() - t, len(salida)


def etapas(datos, formato, calidad=85):
    from PIL import Image
    t = time.perf_counter()
    img = Image.open(io.BytesIO(datos))
    img.load()
    decodificar = time.perf_counter() - t
    buf = io.BytesIO()
    t = time.perf_counter()
    if formato == "jpg":
        img.convert("RGB").save(buf, "JPEG", quality=calidad, optimize=True)
    elif formato == "png":
        img.save(buf, "PNG", optimize=True)
    elif formato == "webp":
        img.save(buf, "WEBP", quality=calidad, method=4)
    elif formato == "avif":
        img.save(buf, "AVIF", quality=calidad)
    return decodificar, time.perf_counter() - t


def comparar_ajustes(args):
    from PIL import Image
    for datos, w, h, nombre in fotos(args):
        img = Image.open(io.BytesIO(datos))
        img.load()
        img = img.convert("RGB")
        print(f"\n  {nombre} · {w}×{h} ({w * h / 1e6:.1f} MP)")
        print(f"  {'formato':<8} {'ajuste':<18} {'tiempo':>9} {'peso':>10}   frente a hoy")
        for formato in args.formatos:
            filas = []
            for etiqueta, opciones, es_hoy in AJUSTES.get(formato, []):
                tiempos, peso = [], 0
                for _ in range(args.repeticiones):
                    buf = io.BytesIO()
                    t = time.perf_counter()
                    img.save(buf, **opciones)
                    tiempos.append(time.perf_counter() - t)
                    peso = buf.tell()
                filas.append((etiqueta, statistics.median(tiempos), peso, es_hoy))
            hoy = next(f for f in filas if f[3])
            for etiqueta, segundos, peso, es_hoy in filas:
                nota = "hoy" if es_hoy else f"{(segundos / hoy[1] - 1) * 100:+.0f} % de tiempo, {(peso / hoy[2] - 1) * 100:+.1f} % de peso"
                print(f"  {formato:<8} {etiqueta:<18} {segundos * 1000:>7.0f}ms {peso / MB:>8.2f}MB   {nota}")


def arrancar_motor():
    sys.path.insert(0, str(REPO))
    real, sys.stdout = sys.stdout, open(os.devnull, "w")
    try:
        from src import main as app_main
        from src import app as engine
        port = app_main._free_port()
        app_main.start_server(port)
        engine.api_ready.wait(60)
    finally:
        sys.stdout = real
    return f"http://127.0.0.1:{port}"


def enviar_lote(base, datos, formato, cuantas):
    limite = uuid.uuid4().hex
    partes = b"".join(
        (f"--{limite}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"foto{i}.jpg\"\r\n"
         f"Content-Type: image/jpeg\r\n\r\n").encode() + datos + b"\r\n" for i in range(cuantas))
    cuerpo = partes + f"--{limite}--\r\n".encode()
    req = urllib.request.Request(f"{base}/api/convert-images-batch?target_format={formato}&quality=85", data=cuerpo,
                                 headers={"Content-Type": f"multipart/form-data; boundary={limite}"})
    t = time.perf_counter()
    with urllib.request.urlopen(req, timeout=900) as r:
        r.read()
    return time.perf_counter() - t


def medir_rafaga(args):
    import threading
    base = arrancar_motor()
    intervalo = args.intervalo / 1000
    print(f"  {'imagen':<22} {'formato':<8} {'una sola':>9} {'última de ' + str(args.rafaga):>13} {'motor sin responder':>20} {'lote de ' + str(args.lote):>11}")
    for datos, w, h, _ in fotos(args):
        nombre = f"{w}×{h} · {len(datos) / MB:.1f} MB"
        for formato in args.formatos:
            enviar(base, datos, formato)
            sola = statistics.median(enviar(base, datos, formato)[0] for _ in range(args.repeticiones))

            ultimas = []
            for _ in range(args.repeticiones):
                tiempos = [0.0] * args.rafaga

                def una(i):
                    time.sleep(i * intervalo)
                    tiempos[i] = enviar(base, datos, formato, calidad=85 - i)[0]

                hilos = [threading.Thread(target=una, args=(i,)) for i in range(args.rafaga)]
                for hilo in hilos:
                    hilo.start()
                for hilo in hilos:
                    hilo.join()
                ultimas.append(tiempos[-1])

            esperas = []
            ocupado = threading.Event()

            def sondear():
                while not ocupado.is_set():
                    t = time.perf_counter()
                    urllib.request.urlopen(f"{base}/api/app/info", timeout=600).read()
                    esperas.append(time.perf_counter() - t)
                    time.sleep(0.03)

            sonda = threading.Thread(target=sondear)
            sonda.start()
            time.sleep(0.1)
            enviar(base, datos, formato)
            ocupado.set()
            sonda.join()

            lote = enviar_lote(base, datos, formato, args.lote)
            print(f"  {nombre:<22} {formato:<8} {sola * 1000:>7.0f}ms {statistics.median(ultimas) * 1000:>11.0f}ms {max(esperas) * 1000:>18.0f}ms {lote:>9.2f}s")


def desglosar(args):
    base = arrancar_motor()

    print(f"  {'imagen':<22} {'formato':<8} {'total':>8} {'decodificar':>12} {'codificar':>10} {'resto':>8}   se ahorraría recordando la imagen")
    for datos, w, h, _ in fotos(args):
        nombre = f"{w}×{h} · {len(datos) / MB:.1f} MB"
        for formato in args.formatos:
            enviar(base, datos, formato)
            total = statistics.median(enviar(base, datos, formato)[0] for _ in range(args.repeticiones))
            pasos = [etapas(datos, formato) for _ in range(args.repeticiones)]
            dec = statistics.median(p[0] for p in pasos)
            cod = statistics.median(p[1] for p in pasos)
            resto = max(0.0, total - dec - cod)
            ahorro = (dec + resto) / total * 100 if total else 0
            print(f"  {nombre:<22} {formato:<8} {total * 1000:>6.0f}ms {dec * 1000:>10.0f}ms {cod * 1000:>8.0f}ms {resto * 1000:>6.0f}ms   {ahorro:>4.0f} %  ({(dec + resto) * 1000:.0f} ms por ajuste)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mp", type=float, nargs="+", default=[2, 12, 24])
    ap.add_argument("--imagen", nargs="+", help="fotos reales en vez de las generadas")
    ap.add_argument("--formatos", nargs="+", default=["webp", "jpg", "png"])
    ap.add_argument("--repeticiones", type=int, default=3)
    ap.add_argument("--ajustes", action="store_true", help="comparar opciones del codificador en vez de desglosar la petición")
    ap.add_argument("--rafaga", type=int, default=0, help="varios ajustes seguidos: cuánto tarda en llegar el último")
    ap.add_argument("--intervalo", type=int, default=300, help="milisegundos entre los ajustes de la ráfaga")
    ap.add_argument("--lote", type=int, default=8, help="imágenes del lote que se mide junto a la ráfaga")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.ajustes:
        comparar_ajustes(args)
    elif args.rafaga:
        medir_rafaga(args)
    else:
        desglosar(args)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
