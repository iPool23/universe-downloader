"""
Script para crear paquete de distribución completo
"""
import zipfile
import os
from pathlib import Path
import shutil

print("=" * 60)
print("CREANDO PAQUETE DE DISTRIBUCIÓN")
print("=" * 60)

# Verificar que existe el ejecutable
exe_path = Path("dist/YouTubeDownloader.exe")
if not exe_path.exists():
    print("✗ Error: No se encontró YouTubeDownloader.exe")
    print("  Ejecuta primero: python build.py")
    exit(1)

# Crear carpeta de release
release_folder = Path("release")
if release_folder.exists():
    shutil.rmtree(release_folder)
release_folder.mkdir()

print("\n[1/3] Copiando archivos...")
# Copiar ejecutable
shutil.copy("dist/YouTubeDownloader.exe", release_folder / "YouTubeDownloader.exe")
print("✓ YouTubeDownloader.exe")

# Copiar README
shutil.copy("dist/LEEME.txt", release_folder / "LEEME.txt")
print("✓ LEEME.txt")

# Crear carpeta downloads vacía
(release_folder / "downloads").mkdir()
print("✓ Carpeta downloads")

# Crear archivo de versión
version_info = """
YouTube Downloader v1.0
=======================

Características:
• Descarga videos de YouTube en MP4 (hasta 4K)
• Descarga audio en M4A de alta calidad
• Interfaz web moderna y fácil de usar
• No requiere instalación de Python
• Portable - funciona desde cualquier carpeta

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
print("✓ VERSION.txt")

print("\n[2/3] Creando archivo ZIP...")
zip_name = "YouTubeDownloader_v1.0_Windows.zip"
with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(release_folder):
        for file in files:
            file_path = Path(root) / file
            arcname = file_path.relative_to(release_folder)
            zipf.write(file_path, arcname)
            print(f"  + {arcname}")
    
    # Agregar carpeta downloads vacía
    zipf.write(release_folder / "downloads", "downloads/")

print(f"✓ {zip_name} creado")

# Obtener tamaño del archivo
zip_size = os.path.getsize(zip_name) / (1024 * 1024)  # MB
exe_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB

print("\n[3/3] Limpiando archivos temporales...")
shutil.rmtree(release_folder)
print("✓ Limpieza completada")

print("\n" + "=" * 60)
print("✅ PAQUETE DE DISTRIBUCIÓN CREADO")
print("=" * 60)
print(f"\n📦 Archivo: {zip_name}")
print(f"📊 Tamaño ZIP: {zip_size:.2f} MB")
print(f"📊 Tamaño EXE: {exe_size:.2f} MB")
print("\n📁 Contenido del paquete:")
print("   • YouTubeDownloader.exe - Aplicación principal")
print("   • LEEME.txt - Instrucciones de uso")
print("   • VERSION.txt - Información de versión")
print("   • downloads/ - Carpeta para descargas")
print("\n🚀 LISTO PARA DISTRIBUIR")
print("   Comparte el archivo ZIP con cualquier usuario")
print("   No necesitan Python ni librerías instaladas")
print("\n" + "=" * 60)
