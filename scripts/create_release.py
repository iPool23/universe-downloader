"""
Script para crear paquete de distribución completo de Universe Downloader.
"""
import argparse
import zipfile
import os
import sys
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description="Create Universe Downloader release package")
parser.add_argument("--lite", action="store_true", help="Mark the release as the lite build without AI features")
args = parser.parse_args()
LITE_BUILD = args.lite
IS_MAC = sys.platform == 'darwin'

# Asegurar que estamos en el directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

APP_NAME = "UniverseDownloader"
VERSION = "2.2.0"
ARTIFACT_NAME = f"{APP_NAME}.app" if IS_MAC else f"{APP_NAME}.exe"

print("=" * 60)
print("  UNIVERSE DOWNLOADER - PAQUETE DE DISTRIBUCIÓN")
print("=" * 60)

# Verificar que existe el ejecutable
artifact_path = Path(f"dist/{ARTIFACT_NAME}")
if not artifact_path.exists():
    print(f"  ✗ Error: No se encontró {artifact_path}")
    print("    Ejecuta primero: python scripts/build.py")
    exit(1)

# Crear carpeta de release
release_folder = Path("release")
if release_folder.exists():
    shutil.rmtree(release_folder)
release_folder.mkdir()

print("\n[1/3] Copiando archivos...")

# Copiar ejecutable
release_artifact_path = release_folder / ARTIFACT_NAME
if artifact_path.is_dir():
    shutil.copytree(artifact_path, release_artifact_path)
else:
    shutil.copy(artifact_path, release_artifact_path)
print(f"  ✓ {ARTIFACT_NAME}")

# Copiar README
leeme_path = Path("dist/LEEME.txt")
if leeme_path.exists():
    shutil.copy(leeme_path, release_folder / "LEEME.txt")
    print("  ✓ LEEME.txt")

# Crear carpeta downloads vacía
(release_folder / "downloads").mkdir()
print("  ✓ Carpeta downloads")

# Crear archivo de versión
lite_feature_note = """• Edición ligera sin IA
• Incluye Video, Imagen y Convertir
""" if LITE_BUILD else ""
platform_note = "• Compatible con macOS" if IS_MAC else ""
platform_requirement = "• macOS 12+" if IS_MAC else "• Windows 10/11"

version_info = f"""
Universe Downloader v{VERSION}
=======================

Características:
{lite_feature_note}• Descarga videos de YouTube, TikTok, Facebook, Instagram, Twitter/X
• Descarga audio en M4A de alta calidad
• Interfaz web moderna y fácil de usar
• No requiere instalación de Python
• Portable - funciona desde cualquier carpeta
• FFmpeg incluido para máxima calidad
• Se minimiza a la bandeja del sistema
{platform_note}

Requisitos:
{platform_requirement}
• Conexión a Internet

Desarrollado con:
• Python 3.11
• FastAPI
• yt-dlp
• PyInstaller
"""

with open(release_folder / "VERSION.txt", "w", encoding="utf-8") as f:
    f.write(version_info)
print("  ✓ VERSION.txt")

print("\n[2/3] Creando archivo ZIP...")
zip_name = f"{APP_NAME}_v{VERSION}_{'macOS' if IS_MAC else 'Windows'}.zip"
with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(release_folder):
        for file in files:
            file_path = Path(root) / file
            arcname = file_path.relative_to(release_folder)
            zipf.write(file_path, arcname)
            print(f"    + {arcname}")

    # Agregar carpeta downloads vacía
    zipf.write(release_folder / "downloads", "downloads/")

print(f"  ✓ {zip_name} creado")

# Obtener tamaños
zip_size = os.path.getsize(zip_name) / (1024 * 1024)
def get_path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total

artifact_size = get_path_size(artifact_path) / (1024 * 1024)

print("\n[3/3] Limpiando archivos temporales...")
shutil.rmtree(release_folder)
print("  ✓ Limpieza completada")

print("\n" + "=" * 60)
print("  ✅ PAQUETE DE DISTRIBUCIÓN CREADO")
print("=" * 60)
print(f"\n  📦 Archivo: {zip_name}")
print(f"  📊 Tamaño ZIP: {zip_size:.1f} MB")
print(f"  📊 Tamaño {ARTIFACT_NAME}: {artifact_size:.1f} MB")
print(f"\n  📁 Contenido del paquete:")
print(f"     • {ARTIFACT_NAME} - Aplicación principal")
print(f"     • LEEME.txt - Instrucciones de uso")
print(f"     • VERSION.txt - Información de versión")
print(f"     • downloads/ - Carpeta para descargas")
print(f"\n  🚀 LISTO PARA DISTRIBUIR")
print("=" * 60)
