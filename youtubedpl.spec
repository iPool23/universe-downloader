
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path


block_cipher = None

IS_MAC = sys.platform == 'darwin'

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
ffmpeg_binary_name = 'ffmpeg' if IS_MAC else 'ffmpeg.exe'
ffprobe_binary_name = 'ffprobe' if IS_MAC else 'ffprobe.exe'
exe_icon = None if IS_MAC else (str(Path('public/imgs/favicon.ico')) if Path('public/imgs/favicon.ico').exists() else None)

binaries = []
for binary_name in (ffmpeg_binary_name, ffprobe_binary_name):
    binary_path = resource_bin_dir / binary_name
    if binary_path.exists():
        binaries.append((str(binary_path), 'bin'))

icon_path = Path('mac') / 'icon.icns' if IS_MAC else Path('public/imgs/favicon.ico')
icon_file = str(icon_path) if icon_path.exists() else None

datas = [
    ('src/views', 'src/views'),
    ('src/static', 'src/static'),
    ('public/imgs', 'public/imgs'),
]

if IS_MAC and icon_path.exists():
    datas.append((str(icon_path), 'mac'))

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
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
        'curl_cffi',
        'curl_cffi.requests',
        'pystray',
        'pystray._darwin' if IS_MAC else 'pystray._win32',
        'PIL',
        'PIL.Image',
        'pybalt',
    ],
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
    upx=not IS_MAC,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=IS_MAC,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=exe_icon,
)

if IS_MAC:
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
