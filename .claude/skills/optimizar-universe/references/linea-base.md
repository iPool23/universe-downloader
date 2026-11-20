# Línea base

Números reales, con fecha. Añade filas; no borres las anteriores. Máquina de referencia: la PC del
dueño (Windows 11, SSD, red de oficina a ~3,6 MB/s contra archive.org).

## Arranque (`medir_arranque.py`)

Segundos acumulados desde que se lanza la app. «Compilada» es `build_out\UniverseDownloader`.

| Fecha | Versión | Modo | Ventana visible | Interfaz cargada | Primera pasada | Nota |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-20 | 3.1.1 | código | 1,33 | 1,61 | 1,61 | Línea base |
| 2026-11-20 | 3.1.1 | compilada | 1,13 | 1,42 | 1,83 | Línea base |

Desglose de la línea base compilada: Python en marcha 0,21 · motor importado 0,67 · motor escuchando
0,72 · ventana creada 0,72 · ventana visible 1,13 · interfaz cargada 1,42. La ventana no empezaba a
crearse hasta que el motor terminaba: dos esperas en fila (0,44 s de importar + 0,41 s de WebView2).

Importar el motor desde el código: 0,84 s. Los que más pesan: fastapi 96 ms, código propio 67 ms,
pydantic 64 ms, yt_dlp 55 ms, charset_normalizer 47 ms, pikepdf 28 ms, Cryptodome 27 ms.

## Peso (`medir_tamano.py --lzma`)

| Fecha | Versión | Carpeta compilada | Instalador | Nota |
| --- | --- | --- | --- | --- |
| 2026-11-20 | 3.1.1 | 591 MB | 157,2 MB | Línea base |

Desglose de la línea base (sin comprimir → comprimido, % del instalador):

| Parte | MB | Comprimido | % |
| --- | --- | --- | --- |
| `bin/ffmpeg.exe` | 193,2 | 43,7 | 27 % |
| `bin/ffprobe.exe` | 193,0 | 43,6 | 27 % |
| `bin/deno.exe` | 93,5 | 29,1 | 18 % |
| `UniverseDownloader.exe` | 23,1 | 22,7 | 14 % |
| `numpy` + `numpy.libs` | 25,9 | 5,1 | 3 % |
| `PIL` | 12,7 | 3,4 | 2 % |
| resto | 49,5 | 14,8 | 9 % |

`ffmpeg.exe` y `ffprobe.exe` son compilaciones estáticas: cada una lleva dentro las mismas
bibliotecas. El ejecutable de la app casi no se comprime porque PyInstaller ya guarda los módulos
comprimidos con zlib. `numpy` entra arrastrado por una importación opcional de Pillow; nada de la
edición ligera lo usa.

## Entrega de archivos (`medir_entrega.py --mb 500`)

| Fecha | Forma | Segundos | Memoria extra | Nota |
| --- | --- | --- | --- | --- |
| 2026-11-20 | blob (la que usaba la descarga de video) | 2,04 | 500 MB | Línea base |
| 2026-11-20 | enlace (conversiones, audio, PDF) | 2,01 | ~1 MB | |
| 2026-11-20 | mover | 0,00 | ninguna | Mismo disco |

Medido con `urllib`; dentro de WebView2 el blob cuesta además la copia a disco que hace el navegador.

## Descarga (`medir_descarga.py`)

| Fecha | Caso | Escaneo | Hasta el primer avance | Total | Nota |
| --- | --- | --- | --- | --- | --- |
| 2026-11-20 | archive.org, tramo 0–20 s, 360p | 1,05 s (repetido: 1 ms) | 4,69 s | 4,69 s | Línea base. La descarga volvía a analizar el video (~1 s) |
| 2026-11-20 | YouTube | 3,53 s → «inicia sesión» | — | — | Bloqueo por IP, no medible desde esta red |

## Interfaz (`medir_ui.mjs`)

| Fecha | Página interactiva | Cambio de vista | `createIcons()` | Nota |
| --- | --- | --- | --- | --- |
| 2026-11-20 | 17 ms | 10 ms (un cuadro) | 0,82 ms | 560 elementos; usa 29 de 1737 íconos; `lucide.min.js` 348 KB, `app.js` 97 KB |
