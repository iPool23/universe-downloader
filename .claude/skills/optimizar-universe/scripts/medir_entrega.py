"""Mide cuánto cuesta entregar un archivo ya descargado al sitio que elige el usuario.

    python medir_entrega.py            # archivo de prueba de 500 MB
    python medir_entrega.py --mb 1500

Cuando una descarga termina, el archivo está en la carpeta de trabajo del motor y todavía tiene que
llegar a donde el usuario quiere guardarlo. Hay tres formas, y este script las cronometra con un
archivo sintético servido por el motor de verdad:

  blob    la página pide el archivo entero, lo guarda en memoria (response.blob()) y recién entonces
          lo escribe. Cuesta una copia por HTTP, otra a disco y tanta memoria como pese el archivo.
  enlace  la página abre un enlace de descarga y WebView2 lo va escribiendo según llega. Una copia.
  mover   el motor mueve el archivo a su destino. En el mismo disco no copia nada.

Arranca un motor propio en un puerto libre; no usa ni toca la app que esté abierta. El archivo de
prueba y la carpeta de destino son temporales y se borran al terminar.
"""
import argparse
import os
import shutil
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
MB = 1024 * 1024


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mb", type=int, default=500)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    sys.path.insert(0, str(REPO))
    devnull = open(os.devnull, "w")
    real_stdout, sys.stdout = sys.stdout, devnull      # el motor imprime al arrancar: no es parte del informe
    try:
        from src import main as app_main
        from src.api import routes
        from src.config import DOWNLOAD_FOLDER
        port = app_main._free_port()
        app_main.start_server(port)
    finally:
        sys.stdout = real_stdout

    work = DOWNLOAD_FOLDER / "_medir_entrega.bin"
    dest_dir = Path(tempfile.mkdtemp(prefix="ud-medir-entrega-"))
    dest = dest_dir / "resultado.bin"
    block = os.urandom(MB)           # datos que no se comprimen ni se guardan como archivo disperso

    def crear():
        with open(work, "wb") as f:
            for _ in range(args.mb):
                f.write(block)
        routes.download_results["medir"] = {"file_path": str(work), "filename": "resultado.bin"}

    def cronometrar(nombre, fn, memoria):
        dest.unlink(missing_ok=True)
        crear()
        t = time.perf_counter()
        fn()
        s = time.perf_counter() - t
        ok = dest.exists() and dest.stat().st_size == args.mb * MB
        print(f"  {nombre:<8} {s:>7.2f} s  {args.mb / s:>7.0f} MB/s   memoria extra: {memoria:<14} {'' if ok else 'RESULTADO INCOMPLETO'}")
        return s

    url = f"http://127.0.0.1:{port}/api/download/file/medir"

    def blob():
        with urllib.request.urlopen(url) as r:
            data = r.read()                    # como response.blob(): todo a memoria
        dest.write_bytes(data)                 # y después a disco

    def enlace():
        with urllib.request.urlopen(url) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f, 1 * MB)

    def mover():
        shutil.move(str(work), str(dest))

    try:
        mismo_disco = os.path.splitdrive(str(work))[0].lower() == os.path.splitdrive(str(dest))[0].lower()
        print(f"== Entregar un archivo de {args.mb} MB  (trabajo y destino en {'el mismo disco' if mismo_disco else 'discos distintos'})")
        t_blob = cronometrar("blob", blob, f"{args.mb} MB")
        t_enlace = cronometrar("enlace", enlace, "~1 MB")
        t_mover = cronometrar("mover", mover, "ninguna")
        print(f"\n  mover es {t_blob / max(t_mover, 0.001):.0f} veces más rápido que blob y {t_enlace / max(t_mover, 0.001):.0f} veces más que enlace")
    finally:
        work.unlink(missing_ok=True)
        shutil.rmtree(dest_dir, ignore_errors=True)
        routes.download_results.pop("medir", None)
    sys.stdout.flush()   # os._exit no vacía los búferes: sin esto el informe se pierde al redirigir
    os._exit(0)          # el motor queda en un hilo: se termina el proceso entero


if __name__ == "__main__":
    main()
