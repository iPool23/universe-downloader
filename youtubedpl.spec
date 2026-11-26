
# -*- mode: python ; coding: utf-8 -*-
# PyInstaller. En Windows lo llama build.ps1; en macOS, .github/workflows/mac.yml (GitHub Actions).
#
# Windows: carpeta (onedir) -> build_out\UniverseDownloader\UniverseDownloader.exe + _internal\.
#          Así arranca al instante (no se descomprime en cada inicio) y el instalador de Inno Setup
#          reemplaza los archivos en cada actualización.
# macOS:   carpeta dentro de «Universe Downloader.app» (Apple Silicon).

import os
import runpy
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


block_cipher = None

IS_MAC = sys.platform == 'darwin'
IS_WIN = sys.platform == 'win32'

LITE_BUILD = os.environ.get('UNIVERSE_LITE_BUILD', '0') == '1'
excluded_modules = []

if LITE_BUILD:
    excluded_modules = [
        'rembg',
        'torch',
        'torchvision',
        'torchaudio',
        'diffusers',
        'onnx',
        'onnxruntime',
        'accelerate',
        'huggingface_hub',
        'transformers',
        'safetensors',
        'src.services.outpainting_service',
        'src.services.rembg_service',
        # Solo lo usan los servicios de IA. Entraba arrastrado por una importación opcional de
        # Pillow (PIL/_typing.py, protegida con try/except): 26 MB en disco sin que nada lo use.
        'numpy',
    ]

resource_bin_dir = Path('mac') / 'bin' if IS_MAC else Path('bin')
exe_suffix = '' if IS_MAC else '.exe'
exe_icon = None if IS_MAC else (str(Path('public/imgs/favicon.ico')) if Path('public/imgs/favicon.ico').exists() else None)

# FFmpeg y, si está, deno: el motor de JavaScript que yt-dlp necesita para YouTube en las PCs
# que no tienen Node instalado (scripts/setup_deno.py lo deja en bin/).
binaries = []
bundled_tools = []
for binary_name in ('ffmpeg', 'ffprobe', 'deno'):
    binary_path = resource_bin_dir / f'{binary_name}{exe_suffix}'
    if binary_path.exists():
        bundled_tools.append((str(binary_path), 'bin'))
# FFmpeg «shared» (scripts/setup_ffmpeg.py): los dos ejecutables comparten estas bibliotecas, que por
# eso van una sola vez. Solo las de bin/ mismo: bin/estatico/ guarda la compilación anterior.
if IS_WIN:
    for dll in sorted(resource_bin_dir.glob('*.dll')):
        bundled_tools.append((str(dll), 'bin'))

binaries = bundled_tools
# Nombres de las DLL de FFmpeg que van en bin/. PyInstaller analiza de qué depende ffmpeg.exe y copia
# esas mismas DLL OTRA VEZ en la raíz de _internal (también si se declaran como datos: las
# reclasifica). Medido: la carpeta pasaba de 370 a 551 MB. Las copias de la raíz se quitan después
# del análisis, más abajo; ffmpeg.exe usa las que tiene al lado, en bin/.
ffmpeg_dll_names = {dll.name.lower() for dll in resource_bin_dir.glob('*.dll')} if IS_WIN else set()

icon_path = Path('mac') / 'icon.icns' if IS_MAC else Path('public/imgs/favicon.ico')
icon_file = str(icon_path) if icon_path.exists() else None

datas = [
    ('src/views', 'src/views'),
    ('src/static', 'src/static'),
    ('public/imgs', 'public/imgs'),
]
# scripts con los que yt-dlp resuelve los desafíos de YouTube (paquete yt-dlp-ejs)
datas += collect_data_files('yt_dlp_ejs')

if IS_MAC and icon_path.exists():
    datas.append((str(icon_path), 'mac'))

hiddenimports = [
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
    'yt_dlp_ejs',
    'curl_cffi',
    'curl_cffi.requests',
    'pystray',
    'pystray._darwin' if IS_MAC else 'pystray._win32',
    'PIL',
    'PIL.Image',
    'pybalt',
    'pikepdf',
]
if IS_WIN:
    # ventana de escritorio: pywebview sobre Edge WebView2 (pythonnet); sus DLL las junta el hook de webview
    hiddenimports += ['webview', 'webview.platforms.winforms', 'webview.platforms.edgechromium', 'clr']
if IS_MAC:
    hiddenimports += ['webview', 'webview.platforms.cocoa', 'AppKit', 'Foundation', 'WebKit', 'Quartz',
                      'Security', 'UniformTypeIdentifiers']

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Fuera las copias de las DLL de FFmpeg que el análisis dejó en la raíz (ver arriba). Cada entrada es
# (ruta de destino, origen, tipo): las de la raíz no llevan carpeta; las de bin/ se conservan.
if ffmpeg_dll_names:
    a.binaries = [entry for entry in a.binaries if entry[0].lower() not in ffmpeg_dll_names]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if IS_MAC:
    version = runpy.run_path('src/version.py')
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='UniverseDownloader',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch='arm64',
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_file,
    )
    coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name='UniverseDownloader', upx=False)
    app = BUNDLE(
        coll,
        name='Universe Downloader.app',
        icon=icon_file,
        bundle_identifier=version['APP_ID'],
        version=version['APP_VERSION'],
        info_plist={
            'CFBundleName': version['APP_NAME'],
            'CFBundleDisplayName': version['APP_NAME'],
            'CFBundleShortVersionString': version['APP_VERSION'],
            'CFBundleVersion': version['APP_VERSION'],
            'LSMinimumSystemVersion': '13.0',
            'LSApplicationCategoryType': 'public.app-category.utilities',
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='UniverseDownloader',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,   # el instalador ya comprime; UPX solo alarga el arranque y dispara antivirus
        console=False,
        disable_windowed_traceback=False,
        icon=exe_icon,
    )
    coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name='UniverseDownloader', upx=False)
