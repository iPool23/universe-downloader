// Mide la carga y la respuesta de la interfaz dentro de la ventana real (WebView2).
//
//   1. Lanza la app con el puerto de depuración (PowerShell):
//        $env:UNIVERSE_UI_DEBUG_PORT = "9340"; $env:UNIVERSE_ALLOW_MULTIPLE = "1"; python src/main.py
//   2. node medir_ui.mjs 9340
//
// Recarga la página varias veces y saca la mediana de: cuánto tarda en estar lista, cuánto pesa y
// tarda cada archivo, cuánto cuesta dibujar los íconos y cuánto tarda en cambiar de vista.
// No modifica nada: solo lee tiempos del navegador.
import { conectar } from './cdp.mjs';

const port = process.argv[2];
if (!port) { console.error('uso: node medir_ui.mjs <puerto>'); process.exit(1); }
const REPETICIONES = 5;
const mediana = (xs) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];

const pagina = await conectar(port);
const cargas = [];
for (let i = 0; i < REPETICIONES; i++) {
  await pagina.send('Page.reload', { ignoreCache: false });
  await new Promise((r) => setTimeout(r, 1200));
  cargas.push(await pagina.evaluar(`(() => {
    const nav = performance.getEntriesByType('navigation')[0];
    const res = performance.getEntriesByType('resource').map(r => ({
      nombre: r.name.split('/').pop().split('?')[0], ms: Math.round(r.duration),
      kb: Math.round((r.decodedBodySize || r.transferSize || 0) / 1024) }));
    return { dom: Math.round(nav.domContentLoadedEventEnd), carga: Math.round(nav.loadEventEnd),
             html_kb: Math.round(nav.decodedBodySize / 1024), res, nodos: document.querySelectorAll('*').length,
             iconos: document.querySelectorAll('svg.lucide').length };
  })()`));
}
const ultima = cargas.at(-1);
console.log(`== Carga de la interfaz (${pagina.url}), mediana de ${REPETICIONES} recargas`);
console.log(`  página interactiva: ${mediana(cargas.map(c => c.dom))} ms   carga completa: ${mediana(cargas.map(c => c.carga))} ms`);
console.log(`  HTML ${ultima.html_kb} KB · ${ultima.nodos} elementos · ${ultima.iconos} íconos dibujados`);
console.log('  archivo                          KB     ms');
for (const r of ultima.res.sort((a, b) => b.kb - a.kb)) {
  const ms = mediana(cargas.map(c => c.res.find(x => x.nombre === r.nombre)?.ms ?? 0));
  console.log(`  ${r.nombre.padEnd(30)} ${String(r.kb).padStart(5)}  ${String(ms).padStart(5)}`);
}

const iconos = await pagina.evaluar(`(() => {
  const usados = new Set([...document.querySelectorAll('[data-lucide]')].map(e => e.dataset.lucide));
  document.querySelectorAll('svg.lucide').forEach(s => usados.add(s.getAttribute('data-lucide')));
  const disponibles = window.lucide?.icons ? Object.keys(window.lucide.icons).length : null;
  const t = performance.now();
  for (let i = 0; i < 20; i++) lucide.createIcons();
  return { usados: usados.size, disponibles, crear_ms: (performance.now() - t) / 20 };
})()`);
console.log(`\n  íconos: la página usa ${iconos.usados} de los ${iconos.disponibles ?? '?'} que trae el archivo de íconos`);
console.log(`  lucide.createIcons() sin nada nuevo que dibujar: ${iconos.crear_ms.toFixed(2)} ms por llamada`);

const vista = await pagina.evaluar(`(async () => {
  const items = [...document.querySelectorAll('.nav-item')];
  const tiempos = [];
  for (let vuelta = 0; vuelta < 3; vuelta++) {
    for (const item of items) {
      const t = performance.now();
      item.click();
      await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      tiempos.push(performance.now() - t);
    }
  }
  items[0].click();
  tiempos.sort((a, b) => a - b);
  return { mediana: tiempos[Math.floor(tiempos.length / 2)], peor: tiempos.at(-1) };
})()`);
console.log(`  cambiar de vista: ${vista.mediana.toFixed(1)} ms de mediana, ${vista.peor.toFixed(1)} ms el peor (incluye dos cuadros de pantalla)`);
pagina.cerrar();
