// Maneja la ventana real de la app por el puerto de depuración de WebView2 (protocolo CDP).
// Necesita Node 22 o más nuevo (trae WebSocket y fetch) y la app lanzada con UNIVERSE_UI_DEBUG_PORT.
//
//   node cdp.mjs <puerto> info                    dirección de la página
//   node cdp.mjs <puerto> eval "<expresión JS>"    evalúa en la página (espera promesas)
//   node cdp.mjs <puerto> shot <archivo.png>       captura de la ventana
//
// También se importa desde otros scripts: `import { conectar } from './cdp.mjs'`.
import { writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

export async function conectar(port) {
  let page;
  for (let i = 0; i < 60 && !page; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
      page = list.find((t) => t.type === 'page' && t.url.startsWith('http://127.0.0.1'));
    } catch { /* la ventana todavía no abre el puerto */ }
    if (!page) await new Promise((r) => setTimeout(r, 500));
  }
  if (!page) throw new Error(`no hay página de la app en el puerto ${port} (¿se lanzó con UNIVERSE_UI_DEBUG_PORT?)`);

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let seq = 0;
  const pending = new Map();
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  };
  const send = (method, params = {}) => new Promise((res) => {
    const id = ++seq;
    pending.set(id, res);
    ws.send(JSON.stringify({ id, method, params }));
  });
  const evaluar = async (expression) => {
    const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (r.result.exceptionDetails) {
      throw new Error(r.result.exceptionDetails.exception?.description || JSON.stringify(r.result.exceptionDetails));
    }
    return r.result.result.value;
  };
  return { url: page.url, send, evaluar, cerrar: () => ws.close() };
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [port, cmd, ...args] = process.argv.slice(2);
  const pagina = await conectar(port);
  if (cmd === 'shot') {
    const r = await pagina.send('Page.captureScreenshot', { format: 'png' });
    writeFileSync(args[0], Buffer.from(r.result.data, 'base64'));
    console.log('captura:', args[0]);
  } else if (cmd === 'eval') {
    const v = await pagina.evaluar(args[0]);
    console.log(typeof v === 'string' ? v : JSON.stringify(v));
  } else {
    console.log('url:', pagina.url);
  }
  pagina.cerrar();
}
