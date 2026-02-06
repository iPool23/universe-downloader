"""
Script para crear ejecutable standalone de Universe Downloader.
Usa el spec file existente (youtubedpl.spec) y opcionalmente descarga FFmpeg.
"""
import subprocess
import sys
import os
from pathlib import Path

# Asegurar que estamos en el directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

APP_NAME = "UniverseDownloader"

print("=" * 60)
print("  UNIVERSE DOWNLOADER - BUILD")
print("=" * 60)

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
bin_dir = PROJECT_ROOT / "bin"
ffmpeg_exe = bin_dir / "ffmpeg.exe"
ffprobe_exe = bin_dir / "ffprobe.exe"

if ffmpeg_exe.exists() and ffprobe_exe.exists():
    print(f"  ✓ FFmpeg encontrado en {bin_dir}")
else:
    print("  ! FFmpeg no encontrado en bin/")
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

readme_content = f"""
╔═════════════════════════════════════════════════╗
║       UNIVERSE DOWNLOADER - INSTRUCCIONES       ║
╚═════════════════════════════════════════════════╝

📦 CONTENIDO DEL PAQUETE:
   • {APP_NAME}.exe - Aplicación principal

🚀 CÓMO USAR:

   1. Ejecuta "{APP_NAME}.exe"

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

exe_path = dist_dir / f"{APP_NAME}.exe"
exe_size = ""
if exe_path.exists():
    exe_size = f" ({exe_path.stat().st_size / (1024*1024):.1f} MB)"

print("  ✓ Archivos de distribución creados")

print("\n" + "=" * 60)
print("  ✅ BUILD COMPLETADO")
print("=" * 60)
print(f"\n  📁 Ubicación: {dist_dir}")
print(f"\n  📦 Archivos generados:")
print(f"     • {APP_NAME}.exe{exe_size}")
print(f"     • LEEME.txt")
print(f"\n  🚀 Ejecuta 'create_release.py' para crear el ZIP distribuible")
print("=" * 60)
