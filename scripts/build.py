"""
Script para crear ejecutable standalone de Universe Downloader.
Usa el spec file existente (youtubedpl.spec) y opcionalmente descarga FFmpeg.
"""
import argparse
import subprocess
import sys
import os
from pathlib import Path

parser = argparse.ArgumentParser(description="Build Universe Downloader")
parser.add_argument("--lite", action="store_true", help="Build without AI features and heavy model dependencies")
args = parser.parse_args()
LITE_BUILD = args.lite
IS_MAC = sys.platform == 'darwin'

# Asegurar que estamos en el directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

if LITE_BUILD:
    os.environ["UNIVERSE_LITE_BUILD"] = "1"
else:
    os.environ.pop("UNIVERSE_LITE_BUILD", None)

APP_NAME = "UniverseDownloader"
RESOURCE_BIN_DIR = PROJECT_ROOT / "mac" / "bin" if IS_MAC else PROJECT_ROOT / "bin"
ARTIFACT_NAME = f"{APP_NAME}.app" if IS_MAC else f"{APP_NAME}.exe"


def get_path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size

    total_size = 0
    for child in path.rglob("*"):
        if child.is_file():
            total_size += child.stat().st_size
    return total_size

print("=" * 60)
print("  UNIVERSE DOWNLOADER - BUILD")
print("=" * 60)
print(f"  Modo de compilación: {'LIGERO (sin IA)' if LITE_BUILD else 'COMPLETO'}")
print(f"  Plataforma destino: {'macOS' if IS_MAC else 'Windows'}")

# 1. Instalar PyInstaller si no está instalado
print("\n[1/4] Verificando PyInstaller...")
try:
    import PyInstaller
    print(f"  ✓ PyInstaller {PyInstaller.__version__} instalado")
except ImportError:
    print("  Instalando PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    print("  ✓ PyInstaller instalado")

# 2. Verificar FFmpeg en bin/
print("\n[2/4] Verificando FFmpeg...")
bin_dir = RESOURCE_BIN_DIR
ffmpeg_exe = bin_dir / ("ffmpeg" if IS_MAC else "ffmpeg.exe")
ffprobe_exe = bin_dir / ("ffprobe" if IS_MAC else "ffprobe.exe")

if ffmpeg_exe.exists() and ffprobe_exe.exists():
    print(f"  ✓ FFmpeg encontrado en {bin_dir}")
else:
    print(f"  ! FFmpeg no encontrado en {bin_dir}")
    if IS_MAC:
        print("  Coloca ffmpeg y ffprobe dentro de mac/bin antes de compilar.")
        print("  También puedes instalarlos con Homebrew y copiarlos a esa carpeta.")
    else:
        print("  Descargando FFmpeg automáticamente...")
        try:
            setup_script = PROJECT_ROOT / "scripts" / "setup_ffmpeg.py"
            subprocess.check_call([sys.executable, str(setup_script)])
            if ffmpeg_exe.exists():
                print("  ✓ FFmpeg descargado correctamente")
            else:
                print("  ⚠ No se pudo descargar FFmpeg. El .exe funcionará")
                print("    pero necesitará FFmpeg instalado en el sistema.")
        except Exception as e:
            print(f"  ⚠ Error descargando FFmpeg: {e}")
            print("    El .exe funcionará pero necesitará FFmpeg en el sistema.")

# 3. Compilar con PyInstaller usando el spec existente
print("\n[3/4] Compilando ejecutable (esto puede tardar unos minutos)...")
spec_file = PROJECT_ROOT / "youtubedpl.spec"
if not spec_file.exists():
    print(f"  ✗ Error: No se encontró {spec_file}")
    sys.exit(1)

try:
    subprocess.check_call([
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        str(spec_file)
    ])
    print("  ✓ Compilación exitosa")
except subprocess.CalledProcessError as e:
    print(f"  ✗ Error en la compilación: {e}")
    sys.exit(1)

# 4. Crear README para distribución
print("\n[4/4] Creando archivos de distribución...")

dist_dir = PROJECT_ROOT / "dist"
dist_dir.mkdir(exist_ok=True)

lite_notice = """

    • Edición ligera sin IA
    • Incluye Video, Imagen y Convertir
""" if LITE_BUILD else ""

package_label = ARTIFACT_NAME

readme_content = f"""
╔═════════════════════════════════════════════════╗
║       UNIVERSE DOWNLOADER - INSTRUCCIONES       ║
╚═════════════════════════════════════════════════╝

📦 CONTENIDO DEL PAQUETE:
    • {package_label} - Aplicación principal
{lite_notice}

🚀 CÓMO USAR:

    1. Ejecuta "{package_label}"

   2. Se abrirá automáticamente tu navegador en:
      http://127.0.0.1:8000

   3. Pega la URL del video (YouTube, TikTok, Facebook, etc.)

   4. Selecciona el formato:
      • MP4 - Video en máxima calidad (hasta 4K)
      • MP3 - Audio en alta calidad (M4A/AAC)

   5. Haz clic en "Descargar"

   6. El archivo se guardará en la carpeta "downloads"

⚠️ NOTAS IMPORTANTES:

   • La primera vez puede tardar un poco en iniciar
   • Necesitas conexión a Internet
   • FFmpeg viene incluido para máxima calidad de video
   • La app se minimiza a la bandeja del sistema (system tray)

🔧 SOLUCIÓN DE PROBLEMAS:

   • Si no se abre el navegador automáticamente, abre:
     http://127.0.0.1:8000

   • Si aparece un error de firewall, permite el acceso

   • Para cerrar la aplicación, haz clic derecho en el
     icono de la bandeja del sistema y selecciona "Salir"

📝 PLATAFORMAS SOPORTADAS:

   • YouTube, TikTok, Facebook, Instagram, Twitter/X
   • Y muchas más (usa yt-dlp como motor de descarga)

═══════════════════════════════════════════════════════════

Desarrollado con Python, FastAPI y yt-dlp
"""

with open(dist_dir / "LEEME.txt", "w", encoding="utf-8") as f:
    f.write(readme_content)

artifact_path = dist_dir / ARTIFACT_NAME
artifact_size = ""
if artifact_path.exists():
    artifact_size = f" ({get_path_size(artifact_path) / (1024*1024):.1f} MB)"

print("  ✓ Archivos de distribución creados")

print("\n" + "=" * 60)
print("  ✅ BUILD COMPLETADO")
print("=" * 60)
print(f"\n  📁 Ubicación: {dist_dir}")
print(f"\n  📦 Archivos generados:")
print(f"     • {ARTIFACT_NAME}{artifact_size}")
print(f"     • LEEME.txt")
print(f"\n  🚀 Ejecuta 'create_release.py' para crear el ZIP distribuible")
print("=" * 60)
