# Catálogo de optimizaciones

Tres listas: lo aplicado, lo medido y descartado, y las ideas sin probar. Antes de proponer algo,
búscalo aquí. Cada entrada dice qué se midió y con qué script, para poder repetirlo.

## Aplicado

### Entregar el archivo moviéndolo, no pasándolo por la página (20/11/2026)
- **Problema medido:** la descarga de video hacía `fetch → response.blob() → a.click()`. El archivo
  entero pasaba por la memoria de la ventana: 500 MB de memoria y 2,0 s por cada 500 MB
  (`medir_entrega.py`), más la copia a disco del navegador.
- **Cambio:** la ventana pregunta la ruta con el cuadro nativo (`Api.elegir_destino` en `main.py`) y
  el motor mueve el archivo (`POST /api/save`). Lo usan la descarga, la conversión a H.264, extraer
  audio y el PDF; los lotes preguntan una sola vez por la carpeta (`Api.elegir_carpeta`). Si el
  usuario cierra el cuadro, la tarjeta ofrece reintentar y la X descarta (`POST /api/discard`). El
  cuadro no ocupa turno en la cola de tareas. En modo navegador todo baja por enlace.
- **Resultado:** guardar 300 MB pasó de ~1,2 s y 300 MB de memoria a 18 ms y nada de memoria.
  Comprobado en la ventana real con una descarga de verdad (archivo de 15 s en su destino).
- **Sin comprobar:** el cuadro nativo en sí no se puede pulsar por CDP; en la prueba se sustituyó
  solo la elección de la ruta. Entre discos distintos el motor copia (no hay otra forma).

### No analizar el video dos veces (20/11/2026)
- **Problema medido:** `/api/scan` tardaba 1,05 s y la descarga volvía a llamar a `extract_info`
  desde cero (`medir_descarga.py`: 4,69 s en un tramo de 20 s).
- **Cambio:** el escaneo guarda el análisis de yt-dlp (`_remember_info`, 5 minutos, 20 entradas) y
  la descarga lo retoma con `process_ie_result` en su primer intento. Si ese análisis ya no sirve
  (enlaces caducados), se descarta, se limpian los restos y se analiza de nuevo.
- **Resultado:** 4,69 s → 3,47 s (mediana de 3 pasadas), un 26 % menos. Con el análisis estropeado a
  propósito la descarga se recupera sola (5,1 s) y no deja errores guardados.
- **Ojo:** la clave de la caché es la URL tal como la limpia el escaneo. Si se cambia cómo se limpia
  una URL en `get_video_info`, hay que hacer lo mismo en `download`.

### Ventana y motor a la vez, y la interfaz antes que las funciones pesadas (20/11/2026)
- **Problema medido:** la ventana no empezaba a crearse hasta que el motor escuchaba (0,72 s en la
  compilada) y WebView2 tardaba 0,41 s más en mostrarse (`medir_arranque.py`).
- **Primer intento, insuficiente:** crear la ventana con una pantalla de inicio y arrancar el motor
  en el hilo de `webview.start(func)`. La ventana apareció a los 0,61 s (antes 1,33, desde el
  código), pero la interfaz quedó lista casi igual (1,58 frente a 1,61): importar el motor y crear
  la ventana compiten por el intérprete en vez de sumarse.
- **Lo que sí funcionó:** además, `app.py` carga las rutas de la API (yt-dlp, pikepdf, curl_cffi…)
  en un hilo aparte. El motor sirve la página en cuanto FastAPI está listo y las funciones quedan
  disponibles poco después; una petición a `/api/` que llegue antes espera (`WaitForApi`), no falla.
- **Resultado, app compilada (mediana de 5):** ventana visible 1,13 → 0,69 s; interfaz cargada
  1,42 → 1,10 s; funciones listas a 1,18 s; primera apertura 1,83 → 1,32 s. Desde el código:
  ventana 1,33 → 0,60 s e interfaz 1,61 → 1,09 s.
- **Arreglo de paso:** el tema elegido se guardaba en `localStorage`, ligado al puerto, que cambia
  en cada apertura, así que no se conservaba. Ahora vive en `preferencias.json` (`src/prefs.py`),
  va inyectado en la página y da el color de fondo de la ventana desde el primer instante.
- **Ojo:** `window.events.loaded` salta dos veces (pantalla de inicio e interfaz). Y cualquier código
  que use `src.api.routes` justo después de importar `src.app` debe esperar a `app.api_ready`.

### FFmpeg una sola vez y sin numpy en la edición ligera (20/11/2026)
- **Problema medido:** `ffmpeg.exe` y `ffprobe.exe` estáticos sumaban 386 MB y 87 MB del
  instalador (54 %), con las mismas bibliotecas dentro de cada uno. `numpy` ocupaba 26 MB sin que
  nada de la edición ligera lo usara (`medir_tamano.py --lzma`).
- **Cambio:** `scripts/setup_ffmpeg.py` baja la compilación «shared» de BtbN (ejecutables de menos
  de 1 MB y las bibliotecas una vez, sin `ffplay.exe`) y aparta la estática en `bin/estatico/`.
  `youtubedpl.spec` empaqueta `bin/*.dll` y añade `numpy` a `excluded_modules` en la ligera.
- **Trampa que costó dos compilaciones:** PyInstaller analiza de qué depende `ffmpeg.exe` y copia
  esas DLL otra vez en la raíz de `_internal`, también si se declaran como datos. La carpeta pasó a
  551 MB con FFmpeg duplicado. El spec quita esas copias de `a.binaries` después del análisis. Si
  cambia la versión de FFmpeg, vuelve a medir: que no haya `av*.dll` sueltas en la raíz.
- **Resultado:** carpeta compilada 591 → 365 MB; comprimida (estimación) 162 → 123 MB. FFmpeg
  ahorró 33 MB de instalador, no los 44 previstos: la biblioteca compartida se comprime peor.
- **Comprobado:** mismos 7 codificadores que antes (libx264, libx265, libmp3lame, aac, libwebp…).
  Con el FFmpeg del sistema fuera del PATH, la app compilada usó el empaquetado para convertir a
  H.264, extraer un MP3 y descargar un tramo de 12 s exactos.

### Convertir imágenes fuera del hilo del motor (20/11/2026)
- **Problema medido:** `/api/convert-image` y `/api/convert-images-batch` convertían dentro del hilo
  que atiende todas las peticiones. Con una foto real de 9 MP (`medir_vista_previa.py --rafaga 3`):
  al mover un control tres veces seguidas, la última vista previa tardaba 1,9 s en WebP y 17,7 s en
  PNG, porque esperaba a las dos anteriores, que ya nadie iba a ver; mientras tanto el motor no
  respondía a nada (0,8 s en WebP, 4,1 s en PNG: el avance de una descarga se quedaba quieto); y un
  lote de 8 fotos tardaba 6,4 s en WebP y 32 s en PNG, de una en una.
- **Cambio:** las dos rutas convierten con `asyncio.to_thread`. El lote convierte hasta 4 fotos a la
  vez y arma el zip al final, en el mismo orden en que llegaron.
- **Resultado:** última de tres vistas previas 1,9 → 0,9 s (WebP) y 17,7 → 4,2 s (PNG); motor sin
  responder 0,8–4,1 s → 20 ms; lote de 8 fotos 6,4 → 1,9 s (WebP) y 32 → 9,2 s (PNG).
- **Comprobado:** el zip del lote sale igual que antes (nombres repetidos con `_1`, `errores.txt`
  con las que fallan, sin restos en la carpeta de trabajo, 400 si ninguna sirve).
- **Ojo:** el tope de 4 a la vez es por memoria (cada foto de 24 MP ocupa unos 70 MB abierta), no
  por procesador. Pillow suelta el intérprete mientras codifica: por eso los hilos sí suman aquí.

### YouTube: yt-dlp al día, reintentos que sirven y actualización automática (26/11/2026)
- **Problema:** yt-dlp 2026.10.26 fallaba con los reproductores nuevos de YouTube («n challenge
  solving failed: a.addOnDisposeCallback is not a function», issue yt-dlp #18123), arreglado en
  2026.11.23. Los reintentos con `android` e `ios` ya no servían: piden PO token y yt-dlp descarta
  sus formatos. Y cada arreglo de YouTube obligaba a publicar la app entera.
- **Cambio:** yt-dlp 2026.11.23; reintentos con los clientes de serie y luego `ios_producer`; el
  bloqueo por IP («not a bot») corta los reintentos en el acto; mensaje que dice qué hacer;
  `src/ytdlp_updater.py` baja de PyPI las versiones nuevas (SHA-256 verificado) y las usa en la
  siguiente apertura.
- **Resultado (desde la red de la oficina, `medir_descarga.py --fin 00:10`):** «Me at the zoo» 5,6
  s en total; Rick Astley (4K) escaneo 2,3 s y descarga 14,8 s; Despacito 2,8 + 9,0 s; un Short
  2,3 + 1,3 s; MP3 entero 2,1 + 0,7 s. archive.org sin cambios (360p, 20 s: 3,35 s).
- **Ojo:** ese día la red ya no estaba bloqueada. yt-dlp 2026.10.26 con el código anterior también
  bajó Rick Astley, pero con el error del resolvedor de desafíos, que en otros videos deja sin
  formatos. El bloqueo de la semana anterior fue temporal.
- **Actualización automática, comprobada en una compilación con yt-dlp 2026.10.26 dentro:** bajó y
  dejó lista la 2026.11.23 a los 6,7 s de abrir; en la apertura siguiente `--selftest` dijo
  «2026.11.23 (actualizado; la app trae 2026.10.26)». Con una copia estropeada volvió a la suya y la
  marcó como mala. Coste en el arranque: funciones listas 1,24 → 1,32 s.

## Pendiente (medido, con ganancia clara)

_(nada pendiente al 20/11/2026: todo lo medido con ganancia clara está aplicado)_

## Descartado (medido, no compensa)

### Recorte rápido sin recodificar
- **Idea:** quitar `force_keyframes_at_cuts` para que FFmpeg copie el tramo en vez de recodificarlo.
- **Medido (20/11/2026, tramo de 5 min a 720p, archive.org):** exacto 45,6 s y 27,8 MB; rápido
  36,9 s y 132,8 MB. Solo 19 % más rápido, con un archivo 4,8 veces mayor y cortes menos precisos.
- **Por qué no:** el tiempo lo pone la red al bajar el tramo, no la recodificación. Repetir solo si
  la red deja de ser el límite (por ejemplo, fibra rápida y tramos de más de media hora).

### Recortar el archivo de íconos (lucide)
- **Idea:** dejar solo los 29 íconos que usa la página, de los 1737 del archivo (348 KB).
- **Medido:** la página está interactiva en 17 ms y `createIcons()` cuesta 0,82 ms (`medir_ui.mjs`).
- **Por qué no:** no hay tiempo que ganar y obliga a regenerar el archivo cada vez que se use un
  ícono nuevo. Los 348 KB son el 0,06 % de la carpeta instalada.

### Recordar la foto en el motor entre un ajuste y otro del editor
- **Idea:** no volver a enviar ni a abrir la imagen cada vez que se mueve un control.
- **Medido (20/11/2026, `medir_vista_previa.py`):** enviar y abrir la foto cuesta 60 ms a 2 MP y
  240 ms a 24 MP, frente a 0,4–4,6 s de la petición entera en WebP y PNG (4–15 %). Solo en JPG es
  una parte grande (40–70 %), pero de un total de 60–350 ms.
- **Por qué no:** el tiempo lo pone el codificador, no el envío. Obligaría a guardar estado en el
  motor (qué foto, cuándo soltarla) para ganar una décima.

### Codificar más rápido (menos esfuerzo en WebP, PNG sin `optimize`)
- **Medido (20/11/2026, `medir_vista_previa.py --ajustes`, tres fotos reales de 9 MP):** WebP
  `method=2` en vez de 4 tarda un 62–70 % menos (0,7 → 0,24 s) y pesa un 4–8 % más; `method=3` no
  cambia nada; `method=6` tarda un 15–27 % más por un 2–4 % menos. PNG con `compress_level=6` en
  vez de `optimize=True` tarda un 62–89 % menos (0,6–4,2 → 0,2–0,5 s) y pesa un 5–11 % más.
- **Por qué no (por ahora):** no es ganancia limpia, cambia el archivo que recibe el usuario, y el
  editor existe para que pese menos. Es una decisión del dueño, no técnica. Si se quiere rapidez al
  arrastrar sin perder peso, la vía es una vista previa rápida y la conversión con todo el esfuerzo
  solo al guardar, avisando de que el peso mostrado es aproximado.

### Módulos sueltos en vez de dentro del ejecutable (`noarchive=True`)
- **Idea:** el ejecutable de 22 MB lleva los módulos de Python ya comprimidos con zlib y el
  instalador no les saca nada. Sueltos, como `.pyc`, sí se comprimen.
- **Medido (20/11/2026, las dos compilaciones del mismo código, instalador real de Inno Setup):**
  instalador 114,6 → 106,0 MB (9 MB menos, 7,5 %). A cambio: 815 → 4370 archivos y 367 → 402 MB en
  disco; instalar 7,1–10,8 → 9,8–13,5 s; primera apertura recién instalada 2,0–3,2 → 4,3–4,6 s (el
  antivirus revisa cada archivo la primera vez). El arranque normal, ya en caché, no cambia (1,05 s).
- **Por qué no:** en una red de 3,6 MB/s los 9 MB son 2,5 s menos de descarga, y se pierden entre 4
  y 5 s entre instalar y abrir, en cada actualización. Solo compensaría con conexiones muy lentas.
- **Para repetirlo:** `noarchive=True` en `youtubedpl.spec`, compilar con `--distpath` a otra
  carpeta, y cronometrar la instalación con un `.iss` de prueba con otro `AppId` y
  `Uninstallable=no`, para no tocar la instalación real.

### Importaciones perezosas del motor
- **Idea:** retrasar yt_dlp, pikepdf, pybalt y bs4, unos 200 ms al importar.
- **Medido (20/11/2026, `medir_arranque.py --exe`, mediana de 5):** desde que la API se carga en un
  hilo aparte, la interfaz está cargada a 1,05 s y las funciones listas a 1,13 s.
- **Por qué no:** esas importaciones ya no están en el camino de la ventana. Lo máximo que se
  ganaría son 80 ms que ocurren después de que la interfaz ya se ve.

### Saltarse el bloqueo de YouTube por IP sin cookies
Investigado el 26/11/2026; no hay una forma fiable. Los mantenedores de yt-dlp dicen que, sin
cookies, la única salida es otra IP (issues #12475 y #15865).
- **PO tokens (bgutil-ytdlp-pot-provider, GPL-3.0):** sirven para los 403 en los formatos, no para
  el bloqueo. Su propio README: «a PO Token does not bypass IP-based login restrictions».
- **cobalt / pybalt para YouTube:** la instancia principal (api.cobalt.tools, v11.7.1) ya no
  ofrece YouTube («no podemos saltar sus límites a nuestra escala», issue cobalt #1356). Las
  comunitarias piden Turnstile, y pybalt 2025.7.1 no filtra por YouTube.
- **Tor:** YouTube marca las salidas de Tor todavía más. Además es lento, y el proyecto Tor pide no
  usarlo para descargas grandes.
- **Proxies residenciales:** es lo que hacen las webs de pago. Cuestan dinero por GB y van contra la
  idea de una app gratuita sin cuentas.

### Optimizar el cambio de vista o el DOM
- **Medido:** 10 ms por cambio, que es un cuadro de pantalla. 560 elementos.
- **Por qué no:** ya está en el mínimo que se puede percibir.

## Ideas sin medir

- **deno (29 MB del instalador, 18 %).** Alternativas: bajarlo la primera vez que se use YouTube, o
  QuickJS (≈1 MB), que yt-dlp admite pero resuelve los desafíos mucho más lento. No se puede validar
  desde esta red porque YouTube está bloqueado por IP: probar desde otra conexión antes de decidir.
- **Descargas en paralelo dentro de un mismo video** (`concurrent_fragment_downloads`, o aria2c como
  descargador externo). Solo ayuda en formatos por fragmentos; hace falta un sitio que los use y no
  esté bloqueado para medirlo.
- **Actualizaciones diferenciales.** Hoy cada actualización baja el instalador entero (114,6 MB).
  FFmpeg y deno, que casi nunca cambian, son más de la mitad: un parche por diferencias, o bajarlos
  aparte solo cuando cambien, sería el siguiente paso. Es un desarrollo, no un ajuste.
