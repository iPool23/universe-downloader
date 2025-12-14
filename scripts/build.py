"""
Script para crear ejecutable standalone del YouTube Downloader
"""
import subprocess
import sys
import os

print("=" * 60)
print("CREANDO EJECUTABLE STANDALONE")
print("=" * 60)

# Instalar PyInstaller si no está instalado
print("\n[1/4] Verificando PyInstaller...")
try:
    import PyInstaller
    print("✓ PyInstaller ya está instalado")
except ImportError:
    print("Instalando PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    print("✓ PyInstaller instalado")

# Crear el spec file personalizado
print("\n[2/4] Creando configuración de build...")
spec_content = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/youtubedpl.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'yt_dlp',
        'yt_dlp.extractor',
        'yt_dlp.postprocessor',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='YouTubeDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
"""

with open('youtubedpl.spec', 'w', encoding='utf-8') as f:
    f.write(spec_content)
print("✓ Configuración creada")

# Ejecutar PyInstaller
print("\n[3/4] Compilando ejecutable (esto puede tardar unos minutos)...")
try:
    subprocess.check_call([
        sys.executable, 
        "-m", 
        "PyInstaller", 
        "--clean",
        "youtubedpl.spec"
    ])
    print("✓ Compilación exitosa")
except subprocess.CalledProcessError as e:
    print(f"✗ Error en la compilación: {e}")
    sys.exit(1)

# Crear README para distribución
print("\n[4/4] Creando archivos de distribución...")
readme_content = """
╔══════════════════════════════════════════════════════════╗
║          YOUTUBE DOWNLOADER - INSTRUCCIONES              ║
╚══════════════════════════════════════════════════════════╝

📦 CONTENIDO DEL PAQUETE:
   • YouTubeDownloader.exe - Aplicación principal

🚀 CÓMO USAR:

   1. Ejecuta "YouTubeDownloader.exe"
   
   2. Se abrirá automáticamente tu navegador en:
      http://127.0.0.1:8000
      
   3. Pega la URL del video de YouTube
   
   4. Selecciona el formato:
      • MP4 - Video en máxima calidad (hasta 4K)
      • MP3 - Audio en alta calidad (M4A/AAC)
      
   5. Haz clic en "Descargar"
   
   6. El archivo se guardará en tu carpeta de Descargas

⚠️ NOTAS IMPORTANTES:

   • La primera vez puede tardar un poco en iniciar
   • Necesitas conexión a Internet
   • Para descargar MP4 en máxima calidad, se recomienda
     tener FFmpeg instalado (opcional)
   • Los archivos se descargan en la carpeta "downloads"
     junto al ejecutable

🔧 SOLUCIÓN DE PROBLEMAS:

   • Si no se abre el navegador automáticamente, abre:
     http://127.0.0.1:8000
     
   • Si aparece un error de firewall, permite el acceso
   
   • Para cerrar la aplicación, cierra la ventana de consola

📝 FORMATOS SOPORTADOS:

   • MP4: Video con audio (máxima calidad disponible)
   • M4A: Audio de alta calidad (AAC)

═══════════════════════════════════════════════════════════

Desarrollado con Python, FastAPI y yt-dlp
"""

with open('dist/LEEME.txt', 'w', encoding='utf-8') as f:
    f.write(readme_content)

print("✓ Archivos de distribución creados")

print("\n" + "=" * 60)
print("✅ BUILD COMPLETADO EXITOSAMENTE")
print("=" * 60)
print(f"\n📁 Ubicación: {os.path.abspath('dist')}")
print("\n📦 Archivos generados:")
print("   • YouTubeDownloader.exe")
print("   • LEEME.txt")
print("\n🚀 Puedes distribuir la carpeta 'dist' completa")
print("   El ejecutable funciona sin necesidad de Python instalado")
print("\n" + "=" * 60)
