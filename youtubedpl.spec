
# -*- mode: python ; coding: utf-8 -*-
# PyInstaller. En Windows lo llama build.ps1; en macOS, scripts/build.py (GitHub Actions).
#
# Windows: carpeta (onedir) -> build_out\UniverseDownloader\UniverseDownloader.exe + _internal\.
#          Así arranca al instante (no se descomprime en cada inicio) y el instalador de Inno Setup
#          reemplaza los archivos en cada actualización.
# macOS:   un solo ejecutable dentro de UniverseDownloader.app, como hasta ahora.

import os
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
    ]

resource_bin_dir = Path('mac') / 'bin' if IS_MAC else Path('bin')
exe_suffix = '' if IS_MAC else '.exe'
exe_icon = None if IS_MAC else (str(Path('public/imgs/favicon.ico')) if Path('public/imgs/favicon.ico').exists() else None)

# FFmpeg y, si está, deno: el motor de JavaScript que yt-dlp necesita para YouTube en las PCs
# que no tienen Node instalado (scripts/setup_deno.py lo deja en bin/).
binaries = []
for binary_name in ('ffmpeg', 'ffprobe', 'deno'):
    binary_path = resource_bin_dir / f'{binary_name}{exe_suffix}'
    if binary_path.exists():
        binaries.append((str(binary_path), 'bin'))

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

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if IS_MAC:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='UniverseDownloader',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=True,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=exe_icon,
    )

    bundle_kwargs = {
        'name': 'UniverseDownloader.app',
        'bundle_identifier': 'com.universe.downloader',
    }
    if icon_file:
        bundle_kwargs['icon'] = icon_file

    app = BUNDLE(
        exe,
        **bundle_kwargs,
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
