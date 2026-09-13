# Imagen de servidor (Linux/ARM64 para el VPS) — no confundir con el empaquetado de escritorio
# (BUILD_MACOS.command / youtubedpl.spec), que es para el .app/.exe con bandeja del sistema.
FROM python:3.12-slim

# ffmpeg: para unir video+audio y convertir a H.264 (ver docs de la sesión: sin esto casi ningún
# video moderno de YouTube se puede descargar). nodejs: JS runtime que yt-dlp necesita para resolver
# el n-challenge de YouTube.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg \
      nodejs \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.docker.txt .
RUN pip install --no-cache-dir -r requirements.docker.txt

COPY src ./src
COPY public ./public

RUN mkdir -p /app/downloads

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
