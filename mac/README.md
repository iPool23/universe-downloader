# Recursos de la compilación de Mac

- `icon.icns`: el ícono de la app (la carpeta sobre un cuadrado redondeado, como pide macOS).
- `bin/`: `ffmpeg`, `ffprobe` y `deno` para Apple Silicon. No se suben al repositorio: los dejan
  `python scripts/setup_ffmpeg.py` y `python scripts/setup_deno.py` (en una Mac), cada uno
  verificado con su suma SHA-256.

La compilación la hace `.github/workflows/mac.yml`. La de Windows usa `bin/` en la raíz.
