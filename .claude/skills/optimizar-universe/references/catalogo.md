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

## Pendiente (medido, con ganancia clara)

Ordenado por lo que más nota el dueño.

### 4. FFmpeg una sola vez
- **Problema medido:** `ffmpeg.exe` y `ffprobe.exe` estáticos suman 386 MB y 87 MB del instalador
  (54 %), con el mismo código dentro de cada uno (`medir_tamano.py --lzma`).
- **Cambio:** usar la compilación «shared» del mismo proveedor (BtbN gpl-shared): dos ejecutables
  pequeños y las bibliotecas una sola vez. Mismos códecs.
- **Se espera:** ~44 MB menos de instalador y ~190 MB menos en disco.

### 5. Sacar numpy de la edición ligera
- **Problema medido:** 25,9 MB en disco, 5,1 MB del instalador. Lo arrastra una importación opcional
  de Pillow (`PIL/_typing.py`, protegida con try/except); solo lo usan los servicios de IA.
- **Cambio:** añadir `numpy` a `excluded_modules` cuando `UNIVERSE_LITE_BUILD=1`.
- **Se espera:** ~5 MB menos de instalador. Comprobar conversión de imágenes y PDF después.

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

### Optimizar el cambio de vista o el DOM
- **Medido:** 10 ms por cambio, que es un cuadro de pantalla. 560 elementos.
- **Por qué no:** ya está en el mínimo que se puede percibir.

## Ideas sin medir

- **deno (29 MB del instalador, 18 %).** Alternativas: bajarlo la primera vez que se use YouTube, o
  QuickJS (≈1 MB), que yt-dlp admite pero resuelve los desafíos mucho más lento. No se puede validar
  desde esta red porque YouTube está bloqueado por IP: probar desde otra conexión antes de decidir.
- **El ejecutable de 23 MB que no se comprime.** PyInstaller guarda los módulos con zlib y el
  instalador ya no les saca nada. `noarchive=True` los dejaría como miles de `.pyc` sueltos, que sí
  se comprimen, pero puede alargar la instalación y el arranque. Medir las dos cosas antes.
- **Importaciones perezosas del motor.** yt_dlp, pikepdf, pybalt y bs4 suman unos 200 ms de 840 al
  importar desde el código. Con la ventana ya creándose en paralelo (entrada 3) puede que dejen de
  estar en el camino crítico: medir después de aplicarla.
- **Descargas en paralelo dentro de un mismo video** (`concurrent_fragment_downloads`, o aria2c como
  descargador externo). Solo ayuda en formatos por fragmentos; hace falta un sitio que los use y no
  esté bloqueado para medirlo.
- **Actualizaciones diferenciales.** Hoy cada actualización baja el instalador entero. Reducir el
  instalador (entradas 4 y 5) es el primer paso; un parche por diferencias sería el siguiente.
