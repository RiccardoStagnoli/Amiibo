/*
 * JARVIS - Servizio Alexa (libreria open source alexa-remote2, NON ufficiale).
 *
 * Manda ad Alexa comandi testuali, come se li dicessi tu a voce:
 *   "accendi la luce del salotto", "imposta il termostato a 21 gradi",
 *   "riproduci musica rilassante su Amazon Music", "che tempo fa".
 * Cosi' Jarvis controlla tutti i dispositivi collegati alla tua Alexa.
 *
 * Primo accesso: avvia il servizio, poi dal PC server apri http://127.0.0.1:3456
 * e accedi con il tuo account Amazon. L'accesso viene salvato in dati/alexa_cookie.json.
 *
 * API locale (solo 127.0.0.1:3011): GET /stato, GET /dispositivi, POST /comando {testo, dispositivo}, POST /parla {testo, dispositivo}
 */

const fs = require('fs');
const http = require('http');
const path = require('path');
const Alexa = require('alexa-remote2');

const PORTA = 3011;
const PORTA_ACCESSO = 3456;
const FILE_COOKIE = path.join(__dirname, '..', 'dati', 'alexa_cookie.json');
const DISPOSITIVO_PREDEFINITO = process.env.ALEXA_DISPOSITIVO || ''; // nome di un Echo, es. "Echo Dot di Riccardo"
fs.mkdirSync(path.dirname(FILE_COOKIE), { recursive: true });

const log = (t) => console.log(`[${new Date().toLocaleString('it-IT')}] ${t}`);
let pronto = false;
let errore = null;
const alexa = new Alexa();

let cookieSalvato;
try { cookieSalvato = JSON.parse(fs.readFileSync(FILE_COOKIE, 'utf8')); } catch { cookieSalvato = undefined; }

alexa.on('cookie', () => {
  try {
    fs.writeFileSync(FILE_COOKIE, JSON.stringify(alexa.cookieData), 'utf8');
    log('Accesso ad Amazon salvato.');
  } catch (e) { log('Impossibile salvare l\'accesso: ' + e.message); }
});

alexa.init({
  cookie: cookieSalvato,
  proxyOnly: true,
  proxyOwnIp: '127.0.0.1',
  proxyPort: PORTA_ACCESSO,
  proxyLogLevel: 'warn',
  amazonPage: 'amazon.it',
  acceptLanguage: 'it-IT',
  alexaServiceHost: 'alexa.amazon.it',
  useWsMqtt: false,
  bluetooth: false,
  cookieRefreshInterval: 4 * 24 * 60 * 60 * 1000,
  logger: (t) => { if (/error|errore|proxy/i.test(String(t))) log(String(t).slice(0, 300)); },
}, (err) => {
  if (err) {
    errore = String(err.message || err);
    log(`Accesso richiesto: apri http://127.0.0.1:${PORTA_ACCESSO} dal PC server e accedi ad Amazon. (${errore.slice(0, 120)})`);
    return;
  }
  pronto = true;
  errore = null;
  log(`Alexa collegata: ${Object.keys(alexa.serialNumbers).length} dispositivi Echo.`);
});

function echo(nome) {
  const lista = Object.values(alexa.serialNumbers || {}).filter((d) => d.capabilities && d.capabilities.includes('TTS'));
  if (!lista.length) throw new Error('Nessun dispositivo Echo trovato sull\'account.');
  const cercato = (nome || DISPOSITIVO_PREDEFINITO || '').toLowerCase();
  if (!cercato) return lista[0];
  const d = lista.find((x) => (x.accountName || '').toLowerCase() === cercato)
    || lista.find((x) => (x.accountName || '').toLowerCase().includes(cercato));
  if (!d) throw new Error(`Echo "${nome}" non trovato. Disponibili: ${lista.map((x) => x.accountName).join(', ')}`);
  return d;
}

const promessa = (f) => new Promise((ok, ko) => f((e, r) => (e ? ko(e) : ok(r))));

const rotte = {
  'GET /stato': async () => ({ pronto, errore, accesso: pronto ? null : `http://127.0.0.1:${PORTA_ACCESSO}` }),
  'GET /dispositivi': async () => {
    const eco = Object.values(alexa.serialNumbers || {}).map((d) => ({ nome: d.accountName, tipo: d.deviceFamily, online: d.online }));
    let casa = [];
    try {
      const r = await promessa((cb) => alexa.getSmarthomeDevicesV2(cb));
      casa = (Array.isArray(r) ? r : Object.values(r || {})).map((x) => x.friendlyName || x.displayName || x.name).filter(Boolean);
    } catch { /* elenco dispositivi casa non disponibile */ }
    return { echo: eco, casa };
  },
  'POST /comando': async (b) => {
    if (!b.testo) throw new Error('Testo del comando mancante');
    const d = echo(b.dispositivo);
    await promessa((cb) => alexa.sendSequenceCommand(d.serialNumber, 'textCommand', String(b.testo), cb));
    return { ok: true, echo: d.accountName };
  },
  'POST /parla': async (b) => {
    const d = echo(b.dispositivo);
    await promessa((cb) => alexa.sendSequenceCommand(d.serialNumber, 'speak', String(b.testo || ''), cb));
    return { ok: true, echo: d.accountName };
  },
};

http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');
  const rotta = rotte[`${req.method} ${url.pathname}`];
  const rispondi = (c, d) => { res.writeHead(c, { 'Content-Type': 'application/json; charset=utf-8' }); res.end(JSON.stringify(d)); };
  if (!rotta) return rispondi(404, { errore: 'Funzione inesistente' });
  if (url.pathname !== '/stato' && !pronto) return rispondi(503, { errore: `Alexa non collegata: dal PC server apri http://127.0.0.1:${PORTA_ACCESSO} e accedi ad Amazon.` });
  let corpo = '';
  req.on('data', (c) => { corpo += c; if (corpo.length > 1e5) req.destroy(); });
  req.on('end', async () => {
    try { rispondi(200, await rotta(corpo ? JSON.parse(corpo) : {})); } catch (e) { rispondi(400, { errore: String(e.message || e) }); }
  });
}).listen(PORTA, '127.0.0.1', () => log(`API Alexa su http://127.0.0.1:${PORTA}`));
