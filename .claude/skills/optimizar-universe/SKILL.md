---
name: optimizar-universe
description: Mide y optimiza Universe Downloader (app de escritorio Windows con FastAPI, pywebview, yt-dlp y FFmpeg, empaquetada con PyInstaller e Inno Setup) con scripts propios para el arranque, el peso del instalador, la descarga, la entrega de archivos y la interfaz, una línea base con números reales y un catálogo de lo ya aplicado y lo ya descartado. Úsala siempre que pidan optimizar, acelerar o aligerar la app, o cuando digan que algo «se demora», «tarda en abrir», «va lento», «pesa mucho», «consume mucha memoria» o que el instalador o las actualizaciones son muy grandes, y también antes de afirmar que un cambio «mejora el rendimiento», aunque no usen la palabra optimizar.
---

# Optimizar Universe Downloader

En esta app la intuición falla seguido. En el primer análisis (20/11/2026) dos sospechas razonables
resultaron falsas al medirlas: el archivo de íconos de 348 KB «tenía que» pesar en la carga (la
página está lista en 17 ms) y el recorte sin recodificar «tenía que» ser mucho más rápido (19 %, a
cambio de archivos cinco veces más grandes). Lo que sí costaba no se veía leyendo el código: el
instalador llevaba FFmpeg dos veces y guardar un video de 1 GB lo pasaba entero por la memoria.

Por eso el método es siempre el mismo: **medir, cambiar una cosa, volver a medir, anotar.** Un
cambio sin número de antes y de después no es una optimización, es una apuesta.

## Antes de proponer nada

1. Lee `references/catalogo.md`: qué se aplicó ya, qué se midió y se descartó (con sus números, para
   no repetir el experimento) y qué ideas quedaron sin probar.
2. Lee `references/linea-base.md`: los últimos números de cada medición. Son tu «antes».
3. Vuelve a medir lo que vayas a tocar. La línea base envejece: cambia yt-dlp, cambia FFmpeg, cambia
   la máquina. Si tu «antes» no coincide con el anotado, averigua por qué antes de seguir.

## Las cinco mediciones

Todas están en `scripts/`, se ejecutan desde la raíz del repo y arrancan su propio motor o su propia
ventana: no usan ni cierran la app que el dueño tenga abierta. Cada una explica sus opciones con
`--help` o en su cabecera.

| Qué duele | Script | Qué te dice |
| --- | --- | --- |
| «Tarda en abrir» | `python scripts/medir_arranque.py` (añade `--exe RUTA` para la compilada, `--imports` para el desglose) | Segundos acumulados en cada fase, desde que se lanza hasta que la interfaz carga |
| «El instalador pesa», «la actualización tarda» | `python scripts/medir_tamano.py --lzma` | Cuánto ocupa cada parte en disco y cuánto aporta al instalador ya comprimida |
| «Guardar el archivo tarda», «se come la memoria» | `python scripts/medir_entrega.py --mb 500` | Coste de las tres formas de llevar un archivo terminado a su destino |
| «La descarga se demora» | `python scripts/medir_descarga.py URL --fin 00:20` | Escaneo, espera hasta el primer avance, duración de cada estado y total |
| «La interfaz va lenta» | `node scripts/medir_ui.mjs PUERTO` | Carga de la página, peso de cada archivo, íconos y cambio de vista en la ventana real |

Las rutas son relativas a esta carpeta (`.claude/skills/optimizar-universe/`).

Detalles que cambian el resultado:

- **Compilada frente a código.** El dueño usa la app instalada, así que el número que cuenta es el de
  la compilada. `build.ps1 -NoSetup` compila y comprueba en menos de un minuto, sin los diez de
  comprimir el instalador. Úsalo en cada vuelta y deja el instalador completo para el final.
- **Primera pasada.** El arranque en frío (archivos sin caché) es más lento que la mediana. El script
  muestra cada pasada: anota las dos cifras, porque el dueño vive la primera al encender la PC.
- **YouTube desde esta red.** Suele responder «inicia sesión» por la IP. Es un bloqueo, no lentitud:
  mide con `https://archive.org/details/BigBuckBunny_124` y di expresamente que lo específico de
  YouTube quedó sin medir. No lo rodees con cookies: la app no las usa por decisión del dueño.
- **Tramos cortos.** Para medir la descarga usa `--fin 00:20`. Un tramo lo baja FFmpeg sin informar
  porcentaje, así que verás un solo estado largo; es normal.

## Cómo decidir qué optimizar

Ordena por lo que el dueño nota, no por lo elegante:

1. Lo que escala con el tamaño del archivo o con cada uso (entregar un video grande, cada descarga).
2. Lo que se paga en cada apertura (arranque).
3. Lo que se paga en cada instalación o actualización (peso del instalador).
4. Lo que solo se ve en un caso raro.

Y descarta sin pena lo que mida poco. Una mejora del 5 % que complica el código o cambia lo que el
usuario recibe (calidad, tamaño del archivo, un paso más) casi nunca compensa. Anótala en el catálogo
como descartada, con su número, para que nadie la vuelva a intentar.

## Al aplicar un cambio

- **Una cosa por vez.** Si mezclas dos cambios y el número mejora, no sabes cuál fue; si empeora,
  tampoco.
- **Que siga funcionando igual.** Después de cada cambio: `python src/main.py --selftest`, y prueba el
  flujo que tocaste en la ventana real (`UNIVERSE_UI_DEBUG_PORT` + `scripts/cdp.mjs`). El cuadro
  «Guardar como» es nativo y no se puede pulsar por CDP: prueba esa parte por las rutas del motor.
- **Marcas de arranque.** `src/main.py` anota fases con `_mark("nombre")` cuando `UNIVERSE_TIMING=1`.
  Si reordenas el arranque, conserva las marcas existentes y añade las nuevas: sin ellas
  `medir_arranque.py` deja de poder comparar con la línea base.
- **Dependencias pesadas.** Lo que solo usa una función se importa dentro de esa función. Lo que solo
  usa la edición completa (IA) va en `excluded_modules` de `youtubedpl.spec`.
- **Sin publicar.** Los cambios quedan como commits en `desktop`. `release.ps1` solo si el dueño lo
  pide. Para que los use: `build.ps1 -Fast -Install`, con la app cerrada.
- **La app del dueño no se toca.** Si está abierta, no la cierres: `UNIVERSE_ALLOW_MULTIPLE=1` permite
  abrir otra instancia para medir.

## Al terminar

Actualiza los dos archivos de `references/` en el mismo commit que el cambio:

- En `linea-base.md`, una fila nueva con fecha por cada medición que hayas repetido. No borres las
  filas anteriores: la serie muestra si algo empeoró sin que nadie lo notara.
- En `catalogo.md`, mueve la entrada a «Aplicado» o «Descartado» con el antes, el después y cómo se
  midió.

Informa al dueño con una tabla de antes y después, en sus unidades (segundos, MB), y di qué no
pudiste medir. Si algo no mejoró, dilo igual: saber que un camino no sirve también es un resultado.
