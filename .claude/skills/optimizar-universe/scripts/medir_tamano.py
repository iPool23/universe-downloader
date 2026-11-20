"""Desglosa cuánto pesa la app compilada y cuánto aporta cada parte al instalador.

    python medir_tamano.py              # tamaños sin comprimir de build_out\\UniverseDownloader
    python medir_tamano.py --lzma       # además estima lo que cada parte ocupa ya comprimida (lento: 2-4 min)
    opciones: --build CARPETA  --min-mb N (grupos menores se suman en «resto»; 3 por defecto)

Sin comprimir importa para el disco y el arranque; comprimido importa para el instalador y, sobre
todo, para cada actualización, que vuelve a bajar el instalador entero. La estimación usa LZMA con
los ajustes normales de Python: el instalador real (Inno Setup, lzma2/ultra64) sale algo menor, pero
las proporciones entre partes se mantienen.
"""
import argparse
import lzma
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
MB = 1024 * 1024


def grupo(path: Path, base: Path) -> str:
    """Agrupa por la carpeta que ve quien compila: _internal/<paquete>, o el archivo suelto."""
    parts = path.relative_to(base).parts
    if parts[0] == "_internal" and len(parts) > 1:
        # los binarios de bin/ se listan uno por uno: son los que más pesan
        if parts[1] == "bin" and len(parts) > 2:
            return f"bin/{parts[2]}"
        return parts[1] if len(parts) > 2 else f"(suelto) {parts[1]}"
    return parts[0]


def comprimido(files) -> int:
    """Tamaño LZMA de los archivos del grupo, comprimidos en un solo flujo (como en el instalador)."""
    comp = lzma.LZMACompressor(preset=6)
    total = 0
    for f in sorted(files):
        with open(f, "rb") as fh:
            while chunk := fh.read(4 * MB):
                total += len(comp.compress(chunk))
    return total + len(comp.flush())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", default=str(REPO / "build_out" / "UniverseDownloader"))
    ap.add_argument("--lzma", action="store_true")
    ap.add_argument("--min-mb", type=float, default=3)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    base = Path(args.build)
    if not base.is_dir():
        raise SystemExit(f"No existe {base}: compila primero (build.ps1 -NoSetup)")

    grupos = {}
    for f in base.rglob("*"):
        if f.is_file():
            grupos.setdefault(grupo(f, base), []).append(f)
    tamanos = {g: sum(f.stat().st_size for f in fs) for g, fs in grupos.items()}
    total = sum(tamanos.values())

    grandes = {g: t for g, t in tamanos.items() if t >= args.min_mb * MB}
    resto = [f for g, fs in grupos.items() if g not in grandes for f in fs]

    comp = {}
    if args.lzma:
        print("Comprimiendo cada parte para estimar su peso en el instalador…", file=sys.stderr)
        trabajos = {g: grupos[g] for g in grandes}
        trabajos["(resto)"] = resto
        with ThreadPoolExecutor(max_workers=4) as pool:   # lzma suelta el GIL: se reparte entre núcleos
            for g, size in zip(trabajos, pool.map(comprimido, trabajos.values())):
                comp[g] = size

    archivos = sum(len(fs) for fs in grupos.values())
    print(f"== {base}  ·  {total / MB:.0f} MB sin comprimir en {archivos} archivos")
    cab = f"  {'parte':<34} {'MB':>8} {'%':>6}"
    if comp:
        total_c = sum(comp.values())
        cab += f" {'comprimido':>11} {'% inst.':>8}"
    print(cab)
    filas = sorted(grandes.items(), key=lambda kv: -kv[1]) + [("(resto)", sum(f.stat().st_size for f in resto))]
    for g, t in filas:
        linea = f"  {g:<34} {t / MB:>8.1f} {t * 100 / total:>5.1f}%"
        if comp:
            linea += f" {comp[g] / MB:>9.1f} MB {comp[g] * 100 / total_c:>7.1f}%"
        print(linea)
    if comp:
        print(f"  {'TOTAL':<34} {total / MB:>8.1f} {'':>6} {total_c / MB:>9.1f} MB")

    for setup in sorted((REPO / "dist").glob("UniverseDownloader-Setup-*.exe")):
        print(f"\n  instalador real: {setup.name}  {setup.stat().st_size / MB:.1f} MB")


if __name__ == "__main__":
    main()
