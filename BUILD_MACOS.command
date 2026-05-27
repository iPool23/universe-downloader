#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "============================================================"
echo "  UNIVERSE DOWNLOADER - BUILD MACOS"
echo "============================================================"
echo
echo "Este flujo crea la edición ligera para Mac."
echo "Antes de compilar, coloca FFmpeg en mac/bin y el icono en mac/icon.icns."
echo

python3 scripts/build.py --lite
python3 scripts/create_release.py --lite

echo
echo "============================================================"
echo "✅ BUILD MACOS COMPLETADO"
echo "============================================================"