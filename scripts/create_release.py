"""
Script para crear paquete de distribución completo de Universe Downloader.
"""
import zipfile
import os
from pathlib import Path
import shutil

# Asegurar que estamos en el directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

APP_NAME = "UniverseDownloader"
VERSION = "2.2.0"

print("=" * 60)
print("  UNIVERSE DOWNLOADER - PAQUETE DE DISTRIBUCIÓN")
print("=" * 60)

# Verificar que existe el ejecutable
exe_path = Path(f"dist/{APP_NAME}.exe")
if not exe_path.exists():
    print(f"  ✗ Error: No se encontró {exe_path}")
    print("    Ejecuta primero: python scripts/build.py")
    exit(1)

# Crear carpeta de release
release_folder = Path("release")
if release_folder.exists():
    shutil.rmtree(release_folder)
release_folder.mkdir()

print("\n[1/3] Copiando archivos...")

# Copiar ejecutable
shutil.copy(exe_path, release_folder / f"{APP_NAME}.exe")
print(f"  ✓ {APP_NAME}.exe")

# Copiar README
leeme_path = Path("dist/LEEME.txt")
if leeme_path.exists():
    shutil.copy(leeme_path, release_folder / "LEEME.txt")
    print("  ✓ LEEME.txt")

# Crear carpeta downloads vacía
(release_folder / "downloads").mkdir()
print("  ✓ Carpeta downloads")

# Crear archivo de versión
version_info = f"""
Universe Downloader v{VERSION}
=======================

Características:
• Descarga videos de YouTube, TikTok, Facebook, Instagram, Twitter/X
• Descarga audio en M4A de alta calidad
• Interfaz web moderna y fácil de usar
• No requiere instalación de Python
• Portable - funciona desde cualquier carpeta
• FFmpeg incluido para máxima calidad
• Se minimiza a la bandeja del sistema

Requisitos:
• Windows 10/11
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
zip_name = f"{APP_NAME}_v{VERSION}_Windows.zip"
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
exe_size = os.path.getsize(exe_path) / (1024 * 1024)

print("\n[3/3] Limpiando archivos temporales...")
shutil.rmtree(release_folder)
print("  ✓ Limpieza completada")

print("\n" + "=" * 60)
print("  ✅ PAQUETE DE DISTRIBUCIÓN CREADO")
print("=" * 60)
print(f"\n  📦 Archivo: {zip_name}")
print(f"  📊 Tamaño ZIP: {zip_size:.1f} MB")
print(f"  📊 Tamaño EXE: {exe_size:.1f} MB")
print(f"\n  📁 Contenido del paquete:")
print(f"     • {APP_NAME}.exe - Aplicación principal")
print(f"     • LEEME.txt - Instrucciones de uso")
print(f"     • VERSION.txt - Información de versión")
print(f"     • downloads/ - Carpeta para descargas")
print(f"\n  🚀 LISTO PARA DISTRIBUIR")
print("=" * 60)
