# Línea base

Números reales, con fecha. Añade filas; no borres las anteriores. Máquina de referencia: la PC del
dueño (Windows 11, SSD, red de oficina a ~3,6 MB/s contra archive.org).

## Arranque (`medir_arranque.py`)

Segundos acumulados desde que se lanza la app. «Compilada» es `build_out\UniverseDownloader`.

| Fecha | Versión | Modo | Ventana visible | Interfaz cargada | Primera pasada | Nota |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-20 | 3.1.1 | código | 1,33 | 1,61 | 1,61 | Línea base |
| 2026-11-20 | 3.1.1 | compilada | 1,13 | 1,42 | 1,83 | Línea base |
| 2026-11-20 | 3.1.1+ | código | 0,60 | 1,09 | — | Ventana y motor a la vez; API en segundo plano (funciones listas a 1,37 s) |
| 2026-11-20 | 3.1.1+ | compilada | 0,69 | 1,10 | 1,32 | Ídem (funciones listas a 1,18 s) |
| 2026-11-20 | 3.2.0 | compilada | 0,65 | 1,05 | — | Repetición, mediana de 5 (funciones listas a 1,13 s) |
| 2026-11-20 | 3.2.0 | compilada, `noarchive` | 0,65 | 1,06 | — | Prueba descartada: igual en caliente; recién instalada abre en 4,3–4,6 s frente a 2,0–3,2 |

Desglose de la línea base compilada: Python en marcha 0,21 · motor importado 0,67 · motor escuchando
0,72 · ventana creada 0,72 · ventana visible 1,13 · interfaz cargada 1,42. La ventana no empezaba a
crearse hasta que el motor terminaba: dos esperas en fila (0,44 s de importar + 0,41 s de WebView2).

Importar el motor desde el código: 0,84 s. Los que más pesan: fastapi 96 ms, código propio 67 ms,
pydantic 64 ms, yt_dlp 55 ms, charset_normalizer 47 ms, pikepdf 28 ms, Cryptodome 27 ms.

## Peso (`medir_tamano.py --lzma`)

| Fecha | Versión | Carpeta compilada | Instalador | Nota |
| --- | --- | --- | --- | --- |
| 2026-11-20 | 3.1.1 | 591 MB | 157,2 MB | Línea base |
| 2026-11-20 | 3.2.0 | 365 MB | 114,6 MB | FFmpeg compartido y sin numpy (estimación comprimida: 162 → 123 MB; el instalador real salió mejor) |
| 2026-11-20 | 3.2.0, `noarchive` | 402 MB | 106,0 MB | Prueba descartada: 4370 archivos en vez de 815; instalar 9,8–13,5 s frente a 7,1–10,8 |

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

Desglose tras el cambio (sin comprimir → comprimido estimado): `bin/avcodec-63.dll` 117,3 → 31,5 ·
`bin/deno.exe` 93,5 → 29,1 · `bin/avfilter-12.dll` 36,4 → 12,0 · `bin/avformat-63.dll` 22,2 → 8,0 ·
`UniverseDownloader.exe` 21,6 → 21,2 · `PIL` 12,7 → 3,4. Lo que más pesa ahora es deno (24 %) y el
ejecutable que no se comprime (17 %): ver «Ideas sin medir» en el catálogo.

## Entrega de archivos (`medir_entrega.py --mb 500`)

| Fecha | Forma | Segundos | Memoria extra | Nota |
| --- | --- | --- | --- | --- |
| 2026-11-20 | blob (la que usaba la descarga de video) | 2,04 | 500 MB | Línea base |
| 2026-11-20 | enlace (conversiones, audio, PDF) | 2,01 | ~1 MB | |
| 2026-11-20 | mover | 0,00 | ninguna | Mismo disco |
| 2026-11-20 | mover, por `POST /api/save` (300 MB) | 0,02 | ninguna | Es lo que usa la app desde hoy |

Medido con `urllib`; dentro de WebView2 el blob cuesta además la copia a disco que hace el navegador.

## Descarga (`medir_descarga.py`)

| Fecha | Caso | Escaneo | Hasta el primer avance | Total | Nota |
| --- | --- | --- | --- | --- | --- |
| 2026-11-20 | archive.org, tramo 0–20 s, 360p | 1,05 s (repetido: 1 ms) | 4,69 s | 4,69 s | Línea base. La descarga volvía a analizar el video (~1 s) |
| 2026-11-20 | archive.org, tramo 0–20 s, 360p | 0,87 s | 3,47 s | 3,47 s | La descarga reutiliza el análisis del escaneo (mediana de 3) |
| 2026-11-20 | YouTube | 3,53 s → «inicia sesión» | — | — | Bloqueo por IP, no medible desde esta red |
| 2026-11-26 | YouTube «Me at the zoo», tramo 0–10 s | 2,55 s | 1,79 s | 4,3 s | yt-dlp 2026.11.23; la red ya no estaba bloqueada |
| 2026-11-26 | YouTube Rick Astley (4K), tramo 0–10 s | 2,31 s | — | 17,1 s | 12,8 MB; Despacito 2,8 + 9,0 s; un Short 2,3 + 1,3 s |
| 2026-11-26 | archive.org, tramo 0–20 s, 360p | 1,01 s | — | 4,36 s | Descarga 3,35 s: igual que antes de los cambios de YouTube |

## Editor de imagen (`medir_vista_previa.py`)

Foto real de 9,2 MP (`C:\Windows\Web\Wallpaper\Windows\img0.jpg`, 3840×2400), calidad 85,
`--rafaga 3` (tres ajustes con 300 ms entre uno y otro) y lote de 8 copias.

| Fecha | Formato | Una vista previa | Última de 3 | Motor sin responder | Lote de 8 | Nota |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-20 | WebP | 0,90 s | 1,90 s | 0,78 s | 6,37 s | Línea base: se convertía en el hilo del motor |
| 2026-11-20 | JPG | 0,08 s | 0,10 s | 0,08 s | 0,80 s | Ídem |
| 2026-11-20 | PNG | 6,10 s | 17,71 s | 4,11 s | 32,13 s | Ídem |
| 2026-11-20 | WebP | 0,80 s | 0,87 s | 0,02 s | 1,93 s | Conversión en hilos aparte; el lote, 4 a la vez |
| 2026-11-20 | JPG | 0,10 s | 0,10 s | 0,02 s | 0,37 s | Ídem |
| 2026-11-20 | PNG | 3,63 s | 4,23 s | 0,03 s | 9,16 s | Ídem |

Reparto de una vista previa con fotos generadas (peor caso para el compresor), a WebP: 2 MP 0,41 s
(codificar 86 %), 12 MP 2,26 s (93 %), 24 MP 4,65 s (95 %). Abrir la foto y enviarla suman entre 60
y 240 ms: lo que cuesta es codificar.

## Interfaz (`medir_ui.mjs`)

| Fecha | Página interactiva | Cambio de vista | `createIcons()` | Nota |
| --- | --- | --- | --- | --- |
| 2026-11-20 | 17 ms | 10 ms (un cuadro) | 0,82 ms | 560 elementos; usa 29 de 1737 íconos; `lucide.min.js` 348 KB, `app.js` 97 KB |
