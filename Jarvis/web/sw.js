/* JARVIS - service worker dell'app per telefono.
   Tiene in memoria la grafica, cosi' l'app si apre subito; i dati arrivano sempre dal server. */
const CACHE = 'jarvis-v2';
const RISORSE = ['/web/style.css', '/web/app.js', '/web/manifest.json', '/web/icona-192.png', '/web/icona-512.png', '/web/icona.svg'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(RISORSE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((k) => Promise.all(k.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
    .then(() => self.clients.claim()));
});

const NON_RAGGIUNGIBILE = `<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Jarvis</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#03080f;color:#d8f6ff;
font-family:system-ui,sans-serif;text-align:center;padding:16px}h1{color:#00e0ff;letter-spacing:.2em}
button{background:transparent;color:#00e0ff;border:1px solid #00e0ff;border-radius:6px;padding:10px 18px;font-size:1rem}</style>
</head><body><div><h1>J.A.R.V.I.S.</h1><p>Server non raggiungibile.</p>
<p>Il PC server deve essere acceso e il telefono collegato alla stessa rete (o a Tailscale).</p>
<button onclick="location.reload()">Riprova</button></div></body></html>`;

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).catch(() => new Response(NON_RAGGIUNGIBILE, { headers: { 'Content-Type': 'text/html; charset=utf-8' } })));
    return;
  }
  if (url.origin === location.origin && url.pathname.startsWith('/web/')) {
    // prima la rete (versione aggiornata), se manca la copia salvata
    e.respondWith(fetch(req).then((r) => {
      const copia = r.clone();
      caches.open(CACHE).then((c) => c.put(req, copia));
      return r;
    }).catch(() => caches.match(req)));
  }
});
