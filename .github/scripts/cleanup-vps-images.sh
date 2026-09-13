#!/usr/bin/env bash
# Limpieza de imagenes Docker y cache de build sin uso en el VPS compartido (mismo servidor que
# Pagos, Mesa Digital, yabrio, etc.). `docker image prune -a` solo borra imagenes que ningun
# contenedor (activo o detenido) referencia -- esa es la unica proteccion que hace falta, ya que
# este paso corre despues de `docker compose up -d`, cuando el contenedor nuevo ya existe y
# referencia su imagen. Es a nivel de host, no solo de esta app, igual que en el resto de sitios
# de este VPS -- correrlo desde cualquiera de los despliegues tiene el mismo efecto.
set -euo pipefail

disk_before=$(df -P / | awk 'NR==2 { print $5 }')
images_out=$(docker image prune -af 2>&1) || true
builder_out=$(docker builder prune -af 2>&1) || true
disk_after=$(df -P / | awk 'NR==2 { print $5 }')

images_freed=$(grep -oE 'Total reclaimed space: .*' <<<"$images_out" | sed 's/Total reclaimed space: //' || echo "0B")
builder_freed=$(grep -oE 'Total:\s*[0-9.]+[A-Za-z]+' <<<"$builder_out" | sed 's/Total:\s*//' || echo "0B")

echo "IMAGES_FREED=${images_freed:-0B}"
echo "BUILDER_FREED=${builder_freed:-0B}"
echo "DISK_BEFORE=$disk_before"
echo "DISK_AFTER=$disk_after"
