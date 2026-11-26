/* JARVIS - pannello web */
'use strict';

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

function el(tag, props = {}, ...figli) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === 'class') n.className = v;
    else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null && v !== false) n.setAttribute(k, v === true ? '' : v);
  }
  for (const f of figli.flat()) {
    if (f === null || f === undefined || f === false) continue;
    n.append(f instanceof Node ? f : document.createTextNode(String(f)));
  }
  return n;
}

async function api(url, dati) {
  const opzioni = dati === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dati),
  };
  const r = await fetch(url, opzioni);
  if (r.status === 401) { location.href = '/accesso'; throw new Error('Accesso richiesto'); }
  let corpo = {};
  try { corpo = await r.json(); } catch { /* risposta vuota */ }
  if (!r.ok) throw new Error(corpo.errore || `Errore ${r.status}`);
  return corpo;
}

const dataOra = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const oggi = new Date().toDateString() === d.toDateString();
  return oggi ? d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleString('it-IT', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
};

// =========================================================================
// PREFERENZE (solo in questo dispositivo)
// =========================================================================
const PREF_BASE = {
  voce: '', tono: 0.35, velocita: 0.85, saggio: null, attiva: true, motore: 'server',
  tema: 'ciano', suoni: true, particelle: true, avvio: true,
};
let pref = { ...PREF_BASE };
try { pref = { ...PREF_BASE, ...JSON.parse(localStorage.getItem('jarvis_pref') || '{}') }; } catch { /* niente */ }
function salvaPref() { try { localStorage.setItem('jarvis_pref', JSON.stringify(pref)); } catch { /* niente */ } }

let profilo = { nome: 'Riccardo', stile_saggio: true, manuali: [] };
const saggio = () => (pref.saggio === null ? profilo.stile_saggio : pref.saggio);
// Insulto solo se attivo in config.py (INSULTI_ATTIVI) e solo per errori dell'utente.
const rimprovero = (conInsulto, senza) => (profilo.insulti === false ? senza : conInsulto);

const parametri = new URLSearchParams(location.search);
if (parametri.get('modo') === 'r1' || parametri.get('compatto') === '1') document.body.classList.add('compatto');

// =========================================================================
// FRASI (parlata normale / da saggio maestro). Serie, senza complimenti.
// =========================================================================
const F = {
  saluto: (n) => (saggio() ? `${n}. Attivo, Jarvis è.` : `${n}. Jarvis attivo.`),
  segreteria: (k) => (k === 0
    ? (saggio() ? 'Messaggi in segreteria, nessuno.' : 'Nessun messaggio in segreteria.')
    : (saggio() ? `In segreteria, ${k} messaggi tu hai.` : `${k} messaggi in segreteria.`)),
  detto: (chi, t) => (saggio() ? `Da ${chi}: ${t}` : `${chi}: ${t}`),
  chiamato: (chi) => (saggio() ? `Chiamato ti ha, ${chi}.` : `${chi} ti ha chiamato su WhatsApp.`),
  vocale: () => (saggio() ? 'un vocale lasciato ha' : 'un messaggio vocale'),
  nonLetti: (k) => (k === 0
    ? (saggio() ? 'Nuovi messaggi WhatsApp, nessuno.' : 'Nessun nuovo messaggio WhatsApp.')
    : (saggio() ? `Messaggi non letti, in ${k} chat ci sono.` : `Messaggi non letti in ${k} chat.`)),
  chat: (nome, k) => (saggio() ? `In ${nome}, ${k} nuovi.` : `${nome}: ${k} nuovi.`),
  email: (k) => (saggio() ? `Email non lette, ${k} tu hai.` : `${k} email non lette.`),
  teams: (k) => (k === 0 ? 'Nessun nuovo messaggio dei professori su Teams.'
    : (saggio() ? `Dai professori, ${k} messaggi su Teams arrivati sono.` : `${k} messaggi dei professori su Teams.`)),
  agenda: (k) => (k === 0 ? 'Nessun impegno oggi.' : (saggio() ? `Oggi, ${k} impegni tu hai.` : `${k} impegni oggi.`)),
  inviato: () => (saggio() ? 'Inviato, il messaggio è.' : 'Messaggio inviato.'),
  inoltrato: (k) => (saggio() ? `Inoltrato a ${k} chat, è.` : `Inoltrato a ${k} chat.`),
  votato: () => (saggio() ? 'Votato, hai.' : 'Voto inviato.'),
  manuale: () => (saggio() ? 'Il manuale, questo dice.' : 'Dal manuale:'),
  prova: () => (saggio() ? 'Pronto, io sono. Parla, tu devi.' : 'Pronto.'),
  errore: (e) => (saggio() ? `Un problema c'è: ${e}` : `Errore: ${e}`),
};

// =========================================================================
// SUONI (generati, nessun file audio)
// =========================================================================
let audioCtx = null;
function suono(tipo = 'clic') {
  if (!pref.suoni) return;
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const o = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    const t = audioCtx.currentTime;
    const note = { clic: [1400, 0.04], notifica: [880, 0.18], errore: [180, 0.35], avvio: [440, 0.6] }[tipo] || [1000, 0.05];
    o.type = tipo === 'errore' ? 'sawtooth' : 'sine';
    o.frequency.setValueAtTime(note[0], t);
    if (tipo === 'avvio') o.frequency.exponentialRampToValueAtTime(1320, t + note[1]);
    if (tipo === 'notifica') o.frequency.setValueAtTime(1320, t + 0.09);
    g.gain.setValueAtTime(0.06, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + note[1]);
    o.connect(g).connect(audioCtx.destination);
    o.start(t); o.stop(t + note[1]);
  } catch { /* audio non disponibile */ }
}
document.addEventListener('click', (e) => { if (e.target.closest('button')) suono('clic'); });

// =========================================================================
// VOCE
// =========================================================================
const sintesi = window.speechSynthesis;
let voci = [];
const coda = [];
let parlaOra = false;

function caricaVoci() {
  if (!sintesi) return;
  voci = sintesi.getVoices().filter((v) => v.lang && v.lang.toLowerCase().startsWith('it'));
  const sel = $('#sel-voce');
  sel.replaceChildren(...voci.map((v) => el('option', { value: v.name }, `${v.name} (${v.lang})`)));
  if (!pref.voce && voci.length) {
    const nonNatural = voci.find((v) => !/natural|online/i.test(v.name));
    pref.voce = (nonNatural || voci[0]).name;
  }
  sel.value = pref.voce;
  aggiornaStatoVoce();
}

function aggiornaStatoVoce() {
  const p = $('#stato-voce');
  const server = profilo.voce_server && pref.motore !== 'browser';
  if (!server && (!sintesi || !voci.length)) { p.textContent = 'Voce n.d.'; p.className = 'pillola ko'; return; }
  p.textContent = pref.attiva ? (server ? 'Voce Jarvis' : 'Voce browser') : 'Voce off';
  p.className = 'pillola ' + (pref.attiva ? 'ok' : '');
}

function mostraParlato(testo, errore) {
  const p = $('#parlato');
  p.textContent = testo;
  p.classList.toggle('errore', Boolean(errore));
  $('#nucleo').classList.toggle('errore', Boolean(errore));
  if (errore) setTimeout(() => $('#nucleo').classList.remove('errore'), 2500);
}

// Testo adatto alla voce: niente elenchi di estratti, niente prefissi tecnici, lunghezza limitata.
function perLaVoce(testo) {
  let t = String(testo);
  if (t.startsWith('(Ollama')) {
    const m = t.match(/\[1\][^\n]*\n([\s\S]*?)(\n\[2\]|$)/);
    t = 'Ecco cosa dicono le mie fonti. ' + (m ? m[1] : '');
  }
  t = t.replace(/\[\d+\]/g, '').replace(/\s+/g, ' ').trim();
  return t.length > 700 ? t.slice(0, 700).replace(/[^.!?]*$/, '') || t.slice(0, 700) : t;
}

// Voce: risposta vocale (domande vocali, rapporto, annunci, pulsanti "Leggi").
function parla(testo, errore = false, voce = true) {
  if (!testo) return;
  mostraParlato(testo, errore);
  if (!voce || !pref.attiva) return;
  const usaServer = profilo.voce_server && pref.motore !== 'browser';
  if (!usaServer && !sintesi) return;
  coda.push(perLaVoce(testo));
  if (!parlaOra) prossimo();
}

// Solo testo: risposta a domande scritte e a pulsanti (niente voce).
function scrivi(testo, errore = false) {
  if (!testo) return;
  mostraParlato(testo, errore);
  if (!$('#centrale').classList.contains('visibile')) notifica(testo.length > 300 ? testo.slice(0, 300) + '…' : testo, errore);
}

// Voce del server (Piper): stessa voce su PC, telefono e Rabbit R1.
let audioCorrente = null;
async function prossimoServer(testo) {
  try {
    const r = await fetch('/api/voce', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ testo }) });
    if (!r.ok) throw new Error('voce server non disponibile');
    const url = URL.createObjectURL(await r.blob());
    audioCorrente = new Audio(url);
    audioCorrente.onplay = () => { $('#sblocca').hidden = true; attivaOnde(true); };
    audioCorrente.onended = audioCorrente.onerror = () => { URL.revokeObjectURL(url); coda.shift(); prossimo(); };
    await audioCorrente.play();
  } catch (e) {
    if (e && e.name === 'NotAllowedError') { $('#sblocca').hidden = false; attivaOnde(false); return; } // serve un tocco
    pref.motore = 'browser'; // ripiego sulla voce del browser
    prossimo();
  }
}

function attivaOnde(si) {
  $('#nucleo').classList.toggle('parla', si);
  $('#onde').classList.toggle('attive', si);
}

function prossimo() {
  const testo = coda[0];
  if (testo === undefined) { parlaOra = false; attivaOnde(false); return; }
  parlaOra = true;
  if (profilo.voce_server && pref.motore !== 'browser') { prossimoServer(testo); return; }
  if (!sintesi) { coda.length = 0; parlaOra = false; return; }
  const u = new SpeechSynthesisUtterance(testo);
  const v = voci.find((x) => x.name === pref.voce);
  if (v) u.voice = v;
  u.lang = v ? v.lang : 'it-IT';
  u.pitch = Number(pref.tono);
  u.rate = Number(pref.velocita);
  let partito = false;
  u.onstart = () => { partito = true; $('#sblocca').hidden = true; attivaOnde(true); };
  u.onend = u.onerror = () => { if (!partito) return; coda.shift(); prossimo(); };
  sintesi.speak(u);
  setTimeout(() => { if (!partito) { sintesi.cancel(); $('#sblocca').hidden = false; attivaOnde(false); } }, 2500);
}

$('#sblocca').addEventListener('click', () => {
  $('#sblocca').hidden = true;
  if (audioCorrente) audioCorrente.play().catch(() => { $('#sblocca').hidden = false; }); else prossimo();
});
$('#btn-zitto').addEventListener('click', () => {
  if (audioCorrente) { audioCorrente.pause(); audioCorrente = null; }
  coda.length = 0; if (sintesi) sintesi.cancel(); parlaOra = false; attivaOnde(false);
});

// Barre audio attorno al nucleo
(function creaOnde() {
  const box = $('#onde');
  for (let i = 0; i < 48; i++) {
    const s = document.createElement('span');
    s.style.transform = `rotate(${i * 7.5}deg) translateY(var(--r-onde))`;
    s.style.animationDelay = `${(i % 6) * 0.08}s`;
    box.append(s);
  }
}());

// =========================================================================
// NOTIFICHE A COMPARSA
// =========================================================================
function notifica(testo, errore = false) {
  const n = el('div', { class: 'notifica' + (errore ? ' errore' : '') }, testo);
  $('#notifiche').append(n);
  suono(errore ? 'errore' : 'notifica');
  setTimeout(() => n.remove(), 7000);
}

// =========================================================================
// PARTICELLE DI SFONDO
// =========================================================================
(function particelle() {
  const c = $('#particelle');
  const ctx = c.getContext('2d');
  let punti = [];
  function dimensiona() {
    c.width = innerWidth; c.height = innerHeight;
    const n = Math.min(70, Math.floor((innerWidth * innerHeight) / 22000));
    punti = Array.from({ length: n }, () => ({
      x: Math.random() * c.width, y: Math.random() * c.height, vx: (Math.random() - 0.5) * 0.3, vy: (Math.random() - 0.5) * 0.3,
    }));
  }
  dimensiona();
  addEventListener('resize', dimensiona);
  const ridotto = matchMedia('(prefers-reduced-motion: reduce)').matches;
  function disegna() {
    ctx.clearRect(0, 0, c.width, c.height);
    if (pref.particelle && !ridotto) {
      const col = getComputedStyle(document.documentElement).getPropertyValue('--acc-rgb').trim() || '0,224,255';
      for (const p of punti) {
        p.x = (p.x + p.vx + c.width) % c.width; p.y = (p.y + p.vy + c.height) % c.height;
        ctx.fillStyle = `rgba(${col},0.5)`; ctx.fillRect(p.x, p.y, 1.6, 1.6);
      }
      for (let i = 0; i < punti.length; i++) {
        for (let j = i + 1; j < punti.length; j++) {
          const d = Math.hypot(punti[i].x - punti[j].x, punti[i].y - punti[j].y);
          if (d < 110) {
            ctx.strokeStyle = `rgba(${col},${0.12 * (1 - d / 110)})`;
            ctx.beginPath(); ctx.moveTo(punti[i].x, punti[i].y); ctx.lineTo(punti[j].x, punti[j].y); ctx.stroke();
          }
        }
      }
    }
    requestAnimationFrame(disegna);
  }
  disegna();
}());

// =========================================================================
// SEQUENZA DI AVVIO
// =========================================================================
async function sequenzaAvvio() {
  if (!pref.avvio) return;
  const box = $('#avvio');
  const righe = $('#avvio-righe');
  const barra = $('#avvio-progresso');
  const passi = ['Inizializzazione nucleo', 'Collegamento WhatsApp', 'Collegamento Google', 'Collegamento Teams',
    'Ricerca PC Msi', 'Caricamento manuale di meccanica', 'Sintesi vocale'];
  box.hidden = false;
  suono('avvio');
  righe.textContent = '';
  for (let i = 0; i < passi.length; i++) {
    righe.textContent += `> ${passi[i]} ... OK\n`;
    barra.style.width = `${((i + 1) / passi.length) * 100}%`;
    await new Promise((r) => setTimeout(r, 260));
  }
  await new Promise((r) => setTimeout(r, 300));
  box.hidden = true;
}
$('#avvio').addEventListener('click', () => { $('#avvio').hidden = true; });

// =========================================================================
// NAVIGAZIONE, OROLOGIO, SCHERMO INTERO, TEMA
// =========================================================================
$('#menu').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-sezione]');
  if (b) mostraSezione(b.dataset.sezione);
});

function mostraSezione(nome) {
  $$('#menu button').forEach((x) => x.classList.toggle('attivo', x.dataset.sezione === nome));
  $$('.sezione').forEach((s) => s.classList.toggle('visibile', s.id === nome));
  if (nome === 'whatsapp') caricaChat();
  if (nome === 'impostazioni') { caricaImpostazioni(); caricaRegistro(); caricaTelefono(); }
  if (nome === 'gmail') caricaSpazio();
  if (nome === 'msi') aggiornaSistema();
  if (nome === 'memoria') caricaMemoria();
  if (nome === 'media') caricaMedia();
}

setInterval(() => { $('#orologio').textContent = new Date().toLocaleTimeString('it-IT'); }, 1000);
$('#btn-schermo').addEventListener('click', () => {
  if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen().catch(() => {});
});

function applicaTema() {
  document.documentElement.dataset.tema = pref.tema;
  $$('.tema').forEach((b) => b.classList.toggle('attivo', b.dataset.tema === pref.tema));
}
$('#temi').addEventListener('click', (e) => {
  const b = e.target.closest('.tema');
  if (!b) return;
  pref.tema = b.dataset.tema; salvaPref(); applicaTema();
});

// =========================================================================
// BARRA COMANDI (testo o voce)
// =========================================================================
// voce = true se la domanda e' arrivata a voce: rispondo a voce. Scritta: rispondo per iscritto.
function gestisciRisposta(r, voce = false) {
  const errore = r.esito === 'errore_utente' || r.esito === 'errore';
  if (voce) parla(r.testo, errore, true); else scrivi(r.testo, errore);
  if (r.esito === 'errore_utente') suono('errore');
  if (r.immagine) { $('#msi-schermo').src = r.immagine; $('#msi-schermo').hidden = false; mostraSezione('msi'); }
  if (r.azione_pannello === 'rapporto') rapporto(false);
  if (r.azione_pannello === 'pulizia') { mostraSezione('gmail'); analizzaPosta(); }
  if (r.azione_pannello === 'media') { mostraSezione('media'); evidenziaMedia(r.media || []); }
  if (r.fonti && r.fonti.length) mostraParlato(r.testo + '\nFonti: ' + r.fonti.map((f) => `${f.manuale} (${f.sezione})`).join(', '));
}

async function eseguiComando(testo, voce = false) {
  try {
    const r = await api('/api/comando', { testo });
    gestisciRisposta(r, voce);
    aggiornaPromemoria();
  } catch (e) { (voce ? parla : scrivi)(F.errore(e.message), true); }
}

$('#form-comando').addEventListener('submit', (e) => {
  e.preventDefault();
  const t = $('#testo-comando').value;
  $('#testo-comando').value = '';
  eseguiComando(t);
});

const Riconoscitore = window.SpeechRecognition || window.webkitSpeechRecognition;
function dettatura(bottone, alRisultato) {
  if (!Riconoscitore) { bottone.hidden = true; return; }
  bottone.addEventListener('click', () => {
    const r = new Riconoscitore();
    r.lang = 'it-IT';
    r.onstart = () => bottone.classList.add('ascolta');
    r.onend = () => bottone.classList.remove('ascolta');
    r.onerror = () => bottone.classList.remove('ascolta');
    r.onresult = (ev) => alRisultato(ev.results[0][0].transcript);
    r.start();
  });
}
// Domanda a voce dal microfono del pannello -> risposta a voce.
dettatura($('#btn-mic-comando'), (t) => { $('#testo-comando').value = t; eseguiComando(t, true); });

// =========================================================================
// ANNUNCI DAL SERVER (comandi vocali dati al PC server)
// =========================================================================
let ultimoAnnuncio = null;
async function controllaAnnunci() {
  try {
    const r = await api('/api/annunci?dopo=' + (ultimoAnnuncio ?? 0));
    if (ultimoAnnuncio === null) { ultimoAnnuncio = r.ultimo; return; } // ignora quelli vecchi
    // Annunci = risposte a comandi vocali dati al PC server, promemoria, riepilogo: a voce.
    r.annunci.forEach((a) => { notifica(a.testo); gestisciRisposta({ ...a, esito: 'ok' }, true); });
    if (r.annunci.length) aggiornaPromemoria();
    ultimoAnnuncio = r.ultimo;
  } catch { /* server non raggiungibile */ }
}

// =========================================================================
// WIDGET
// =========================================================================
function misura(nome, valore) {
  const v = Math.max(0, Math.min(100, Number(valore) || 0));
  return el('div', { class: 'misura' },
    el('div', { class: 'etichetta-m' }, el('span', {}, nome), el('span', {}, `${Math.round(v)}%`)),
    el('div', { class: 'traccia' }, el('div', { class: 'riempi' + (v > 85 ? ' alto' : ''), style: `width:${v}%` })));
}

async function aggiornaMeteo() {
  try {
    const m = await api('/api/meteo');
    $('#w-meteo').replaceChildren(el('div', { class: 'w-grande' }, `${m.temperatura}°`),
      el('div', {}, `${m.citta} · ${m.descrizione}`),
      el('div', { class: 'sotto nota' }, `min ${m.minima}° · max ${m.massima}° · vento ${m.vento} km/h`));
  } catch (e) { $('#w-meteo').replaceChildren(el('span', { class: 'nota' }, e.message)); }
}

let statoMsi = { online: false };
async function aggiornaSistema() {
  try {
    const s = await api('/api/sistema');
    $('#w-server').replaceChildren(misura('CPU', s.cpu), misura('RAM', s.ram), misura('Disco', s.disco),
      el('div', { class: 'nota' }, `Acceso da ${s.uptime_ore} h`));
    statoMsi = s.msi || { online: false };
    const pill = $('#stato-msi');
    pill.textContent = statoMsi.online ? 'Msi on' : 'Msi off';
    pill.className = 'pillola ' + (statoMsi.online ? 'ok' : 'ko');
    const corpoMsi = statoMsi.online
      ? [el('div', { class: 'w-grande' }, 'ONLINE'), misura('CPU', statoMsi.cpu), misura('RAM', statoMsi.ram)]
      : [el('div', { class: 'w-grande' }, 'OFFLINE'), el('div', { class: 'nota' }, 'Spento, fuori casa o agente non avviato.')];
    $('#w-msi').replaceChildren(...corpoMsi);
    $('#msi-stato').textContent = statoMsi.online
      ? `Collegato: ${statoMsi.host || 'Msi'} · ${statoMsi.sistema || ''}` : 'Msi non collegato.';
  } catch { /* niente */ }
}

async function aggiornaAgenda() {
  try {
    const ev = await api('/api/calendario/oggi');
    $('#w-agenda').replaceChildren(...(ev.length ? ev.map((e) => el('div', {},
      el('strong', {}, e.inizio && e.inizio.includes('T') ? dataOra(e.inizio) + ' ' : 'Giornata · '), e.titolo))
      : [el('span', { class: 'nota' }, 'Nessun impegno oggi.')]));
    return ev;
  } catch (e) { $('#w-agenda').replaceChildren(el('span', { class: 'nota' }, e.message.slice(0, 120))); return null; }
}

async function aggiornaPromemoria() {
  try {
    const r = await api('/api/promemoria');
    const righe = [
      ...r.promemoria.map((p) => el('div', {}, el('strong', {}, dataOra(p.quando) + ' '), p.testo)),
      ...r.note.map((n) => el('div', { class: 'sotto' }, '• ' + n.testo)),
    ];
    $('#w-promemoria').replaceChildren(...(righe.length ? righe
      : [el('span', { class: 'nota' }, "Niente. Prova: 'ricordami tra 20 minuti di studiare' o 'annota comprare olio motore'.")]));
  } catch { /* niente */ }
}

async function caricaRegistro() {
  try {
    const righe = await api('/api/registro');
    $('#lista-registro').replaceChildren(...(righe.length ? righe.map((r) => el('div', { class: 'voce' + (r.dettaglio.includes('ERRATA') ? ' sicura' : '') },
      el('div', { class: 'titolo' }, el('span', {}, r.tipo), el('span', { class: 'sotto' }, dataOra(r.ora))),
      el('div', { class: 'sotto' }, r.dettaglio + (r.ip ? ` · ${r.ip}` : ''))))
      : [el('p', { class: 'nota' }, 'Registro vuoto.')]));
  } catch (e) { $('#lista-registro').replaceChildren(el('p', { class: 'errore' }, e.message)); }
}
$('#btn-registro').addEventListener('click', caricaRegistro);

// =========================================================================
// SEGRETERIA
// =========================================================================
const giaAnnunciati = new Set();

function testoRegistrazione(r) {
  const parti = r.contenuti.map((c) => (c.vocale ? F.vocale() : c.testo));
  if ((r.origine || '').includes('chiamata')) {
    return F.chiamato(r.contatto) + (parti.length ? ' ' + F.detto(r.contatto, parti.join('. ')) : '');
  }
  return F.detto(r.contatto, parti.join('. ') || '...');
}

function disegnaSegreteria(lista) {
  const box = $('#lista-segreteria');
  if (!lista.length) { box.replaceChildren(el('p', { class: 'nota' }, 'Nessun messaggio registrato.')); return; }
  box.replaceChildren(...lista.slice().reverse().map((r) => {
    let stato = '';
    if (r.stato !== 'completato') stato = 'sta ancora scrivendo';
    else if (r.chiuso_con === 'inattività') stato = 'non ha premuto 1';
    return el('div', { class: 'voce' + (r.nuovo ? ' nuova' : '') },
      el('div', { class: 'titolo' }, el('span', {}, r.contatto), el('span', { class: 'sotto' }, dataOra(r.inizio))),
      r.origine !== 'messaggio' ? el('div', { class: 'etichetta' }, r.origine) : null,
      stato ? el('div', { class: 'etichetta' }, stato) : null,
      ...r.contenuti.map((c) => (c.vocale ? el('audio', { controls: true, preload: 'none', src: c.vocale })
        : el('div', {}, c.testo))),
      el('div', { class: 'azioni' }, el('button', { class: 'btn piccolo sec', onclick: () => parla(testoRegistrazione(r)) }, 'Leggi')));
  }));
}

async function aggiornaSegreteria(annuncia) {
  try {
    const lista = await api('/api/segreteria');
    disegnaSegreteria(lista);
    const nuove = lista.filter((r) => r.nuovo && r.stato === 'completato' && !giaAnnunciati.has(r.id));
    if (annuncia && nuove.length) {
      nuove.forEach((r) => { giaAnnunciati.add(r.id); notifica('Segreteria: ' + r.contatto); parla(testoRegistrazione(r)); });
      await api('/api/segreteria/letti', { ids: nuove.map((r) => r.id) });
    }
  } catch (e) {
    $('#lista-segreteria').replaceChildren(el('p', { class: 'errore' }, e.message));
  }
}

function testoParlato(m) {
  if (m.sondaggio) return `un sondaggio: ${m.sondaggio.domanda}. Opzioni: ${m.sondaggio.opzioni.join(', ')}.`;
  if (m.vocale || m.tipo === 'ptt') return F.vocale();
  return m.testo;
}

// =========================================================================
// RAPPORTO: segreteria, WhatsApp, Teams, agenda, email
// =========================================================================
let rapportoInCorso = false;
async function rapporto(conSaluto = true) {
  if (rapportoInCorso) return;
  rapportoInCorso = true;
  try {
    if (conSaluto) parla(F.saluto(profilo.nome));
    const lista = await api('/api/segreteria?solo_nuovi=1').catch(() => []);
    const complete = lista.filter((r) => r.stato === 'completato');
    parla(F.segreteria(complete.length));
    complete.forEach((r) => { giaAnnunciati.add(r.id); parla(testoRegistrazione(r)); });
    if (complete.length) await api('/api/segreteria/letti', { ids: complete.map((r) => r.id) }).catch(() => {});
    aggiornaSegreteria(false);

    try {
      const chat = (await api('/api/wa/chat')).filter((c) => c.non_letti > 0);
      parla(F.nonLetti(chat.length));
      for (const c of chat.slice(0, 5)) {
        parla(F.chat(c.nome, c.non_letti));
        const msgs = await api(`/api/wa/messaggi?chat=${encodeURIComponent(c.id)}&n=${Math.min(c.non_letti, 5)}`);
        msgs.filter((m) => !m.da_me).forEach((m) => parla(F.detto(m.autore || c.nome, testoParlato(m))));
      }
    } catch { /* WhatsApp non collegato */ }

    try {
      const t = await api('/api/teams/nuovi');
      if (t.configurato) {
        parla(F.teams(t.messaggi.length));
        t.messaggi.slice(0, 8).forEach((m) => parla(`${m.da}, ${m.dove}: ${m.testo}`));
        disegnaTeams(t);
        if (t.messaggi.length) await api('/api/teams/visti', { ids: t.messaggi.map((m) => m.id) });
      }
    } catch { /* Teams non disponibile */ }

    try {
      const pr = await api('/api/promemoria');
      const oggi = new Date().toDateString();
      const diOggi = pr.promemoria.filter((p) => new Date(p.quando).toDateString() === oggi);
      if (diOggi.length) parla('Promemoria di oggi: ' + diOggi.map((p) => `${dataOra(p.quando)} ${p.testo}`).join('; '));
    } catch { /* niente */ }

    const ev = await aggiornaAgenda();
    if (ev) {
      parla(F.agenda(ev.length));
      ev.forEach((e) => parla(`${e.inizio && e.inizio.includes('T') ? dataOra(e.inizio) : 'Tutto il giorno'}, ${e.titolo}.`));
    }
    try {
      const email = await api('/api/gmail/lista?q=is:unread');
      parla(F.email(email.length));
    } catch { /* Gmail non configurato */ }
  } finally {
    rapportoInCorso = false;
  }
}
$('#btn-rapporto').addEventListener('click', () => rapporto(true));

// =========================================================================
// WHATSAPP
// =========================================================================
let chatCache = [];
let chatAperta = null;
let citazione = null;
let impWa = { escluse: [], risposta_automatica: 'scelte', chat_risposta_auto: [] };

async function statoWa() {
  const p = $('#stato-wa');
  try {
    const s = await api('/api/wa/stato');
    p.textContent = s.pronto ? 'WhatsApp on' : (s.qr ? 'WhatsApp QR' : 'WhatsApp...');
    p.className = 'pillola ' + (s.pronto ? 'ok' : 'ko');
    return s;
  } catch {
    p.textContent = 'WhatsApp off'; p.className = 'pillola ko';
    return null;
  }
}

async function caricaChat() {
  try {
    [chatCache, impWa] = await Promise.all([api('/api/wa/chat'), api('/api/wa/impostazioni')]);
    disegnaChat();
  } catch (e) {
    $('#lista-chat').replaceChildren(el('p', { class: 'errore' }, e.message));
  }
}

function disegnaChat() {
  const filtro = $('#cerca-chat').value.toLowerCase();
  const lista = chatCache.filter((c) => c.nome.toLowerCase().includes(filtro));
  $('#lista-chat').replaceChildren(...lista.map((c) => el('div', {
    class: 'voce' + (c.non_letti ? ' nuova' : '') + (chatAperta && chatAperta.id === c.id ? ' selezionata' : ''),
    onclick: () => apriChat(c),
  },
  el('div', { class: 'titolo' }, el('span', {}, (c.gruppo ? '# ' : '') + c.nome),
    c.non_letti ? el('span', { class: 'contatore' }, c.non_letti) : el('span', { class: 'sotto' }, dataOra(c.ora))),
  el('div', { class: 'sotto' }, (c.ultimo || '').slice(0, 80)),
  c.risposta_auto ? el('div', { class: 'etichetta' }, 'risposta automatica') : null)));
}
$('#cerca-chat').addEventListener('input', disegnaChat);

async function apriChat(c) {
  chatAperta = c;
  citazione = null;
  $('#citazione').hidden = true;
  $('#titolo-chat').textContent = c.nome;
  $('#interruttori-chat').hidden = false;
  $('#form-invio').hidden = false;
  const chk = $('#chk-auto');
  chk.checked = c.risposta_auto;
  chk.disabled = c.gruppo || impWa.risposta_automatica === 'tutti';
  chk.parentElement.title = c.gruppo ? 'Non disponibile per i gruppi'
    : (impWa.risposta_automatica === 'tutti' ? 'Modalità attuale: tutte le chat (cambia in Impostazioni)' : '');
  disegnaChat();
  await caricaMessaggi();
}

async function caricaMessaggi() {
  if (!chatAperta) return;
  const box = $('#messaggi');
  box.replaceChildren(el('p', { class: 'nota' }, 'Carico...'));
  try {
    const msgs = await api(`/api/wa/messaggi?chat=${encodeURIComponent(chatAperta.id)}&n=40`);
    box.replaceChildren(...msgs.map(disegnaMessaggio));
    box.scrollTop = box.scrollHeight;
  } catch (e) {
    box.replaceChildren(el('p', { class: 'errore' }, e.message));
  }
}

function disegnaMessaggio(m) {
  let blocco = null;
  if (m.sondaggio) {
    const tipo = m.sondaggio.multipla ? 'checkbox' : 'radio';
    const nomeGruppo = 'p' + m.id.replace(/\W/g, '');
    const opzioni = m.sondaggio.opzioni.map((o) => el('label', { class: 'interruttore' },
      el('input', { type: tipo, name: nomeGruppo, value: o }), el('span', {}, o)));
    blocco = el('div', { class: 'sondaggio' }, el('strong', {}, m.sondaggio.domanda), ...opzioni,
      el('div', {}, el('button', {
        class: 'btn piccolo',
        onclick: async () => {
          const scelte = opzioni.map((l) => l.querySelector('input')).filter((i) => i.checked).map((i) => i.value);
          if (!scelte.length) { scrivi(rimprovero('Non hai scelto nessuna opzione, genio.', 'Nessuna opzione scelta.'), true); return; }
          try { await api('/api/wa/vota', { messaggio: m.id, opzioni: scelte }); scrivi(F.votato()); } catch (e) { scrivi(F.errore(e.message), true); }
        },
      }, 'Vota')));
  }
  return el('div', { class: 'msg' + (m.da_me ? ' mio' : '') },
    m.autore && !m.da_me ? el('div', { class: 'autore' }, m.autore) : null,
    m.sondaggio ? null : el('div', {}, m.testo),
    m.vocale ? el('audio', { controls: true, preload: 'none', src: '/vocali/' + m.vocale }) : null,
    blocco,
    el('div', { class: 'ora' }, dataOra(m.ora)),
    el('div', { class: 'azioni-msg' },
      el('button', { class: 'btn piccolo sec', onclick: () => impostaCitazione(m) }, 'Rispondi'),
      el('button', { class: 'btn piccolo sec', onclick: () => apriInoltro(m) }, 'Inoltra'),
      el('button', { class: 'btn piccolo sec', onclick: () => parla(F.detto(m.autore || chatAperta.nome, testoParlato(m))) }, 'Leggi')));
}

function impostaCitazione(m) {
  citazione = m;
  const c = $('#citazione');
  c.textContent = 'Risposta a: ' + m.testo.slice(0, 120) + '  (tocca per annullare)';
  c.hidden = false;
  $('#testo-invio').focus();
}
$('#citazione').addEventListener('click', () => { citazione = null; $('#citazione').hidden = true; });

$('#form-invio').addEventListener('submit', async (e) => {
  e.preventDefault();
  const testo = $('#testo-invio').value.trim();
  if (!chatAperta) return;
  if (!testo) { scrivi(rimprovero('Messaggio vuoto. Scrivi qualcosa, coglione.', 'Messaggio vuoto.'), true); suono('errore'); return; }
  try {
    await api('/api/wa/invia', { chat: chatAperta.id, testo, cita: citazione ? citazione.id : undefined });
    $('#testo-invio').value = '';
    citazione = null; $('#citazione').hidden = true;
    scrivi(F.inviato());
    setTimeout(caricaMessaggi, 800);
  } catch (err) { scrivi(F.errore(err.message), true); }
});
dettatura($('#btn-detta'), (t) => { $('#testo-invio').value = t; });

$('#chk-auto').addEventListener('change', async (e) => {
  if (!chatAperta) return;
  const lista = new Set(impWa.chat_risposta_auto);
  if (e.target.checked) lista.add(chatAperta.id); else lista.delete(chatAperta.id);
  const modo = impWa.risposta_automatica === 'nessuno' && e.target.checked ? 'scelte' : impWa.risposta_automatica;
  impWa = await api('/api/wa/impostazioni', { chat_risposta_auto: [...lista], risposta_automatica: modo });
  caricaChat();
});

$('#btn-escludi').addEventListener('click', async () => {
  if (!chatAperta || !confirm(`Escludere "${chatAperta.nome}"? Jarvis non leggerà più questa chat.`)) return;
  impWa = await api('/api/wa/impostazioni', {
    escluse: [...new Set([...impWa.escluse, chatAperta.id])],
    chat_risposta_auto: impWa.chat_risposta_auto.filter((x) => x !== chatAperta.id),
  });
  chatAperta = null;
  $('#titolo-chat').textContent = 'Seleziona una chat';
  $('#interruttori-chat').hidden = true;
  $('#form-invio').hidden = true;
  $('#messaggi').replaceChildren();
  caricaChat();
});

let daInoltrare = null;
function apriInoltro(m) {
  daInoltrare = m;
  $('#cerca-inoltra').value = '';
  $('#lista-inoltra').replaceChildren();
  disegnaInoltro();
  $('#dlg-inoltra').showModal();
}
function disegnaInoltro() {
  const f = $('#cerca-inoltra').value.toLowerCase();
  const selezionate = new Set($$('#lista-inoltra input:checked').map((i) => i.value));
  $('#lista-inoltra').replaceChildren(...chatCache.filter((c) => c.nome.toLowerCase().includes(f)).map((c) =>
    el('label', { class: 'interruttore' },
      el('input', { type: 'checkbox', value: c.id, checked: selezionate.has(c.id) }), el('span', {}, c.nome))));
}
$('#cerca-inoltra').addEventListener('input', disegnaInoltro);
$('#dlg-inoltra').addEventListener('close', async () => {
  if ($('#dlg-inoltra').returnValue !== 'ok' || !daInoltrare) return;
  const dest = $$('#lista-inoltra input:checked').map((i) => i.value);
  if (!dest.length) { scrivi(rimprovero('Non hai scelto nessun destinatario. Sveglia.', 'Nessun destinatario scelto.'), true); return; }
  try {
    const r = await api('/api/wa/inoltra', { messaggio: daInoltrare.id, destinazioni: dest });
    scrivi(F.inoltrato(r.inoltrati));
  } catch (e) { scrivi(F.errore(e.message), true); }
});

// =========================================================================
// GOOGLE: Gmail, spazio, pulizia
// =========================================================================
async function caricaSpazio() {
  try {
    const q = await api('/api/google/spazio');
    const gb = (b) => `${(b / 1073741824).toFixed(1)} GB`;
    const perc = q.limit ? (q.usage * 100) / q.limit : 0;
    $('#spazio').replaceChildren(misura(`Usato ${gb(q.usage || 0)}${q.limit ? ' su ' + gb(q.limit) : ''}`, perc),
      el('div', { class: 'nota' }, `Gmail ${gb(q.usageInGmail || 0)} · Drive ${gb(q.usageInDrive || 0)} · Cestino Drive ${gb(q.usageInDriveTrash || 0)}`));
  } catch (e) { $('#spazio').replaceChildren(el('span', { class: 'nota' }, e.message)); }
}

async function caricaGmail(q, tutta) {
  const box = $('#lista-gmail');
  $('#email-aperta').hidden = true;
  box.replaceChildren(el('p', { class: 'nota' }, 'Controllo la posta...'));
  try {
    const lista = await api(`/api/gmail/lista?q=${encodeURIComponent(q)}${tutta ? '&tutta=1' : ''}`);
    if (!lista.length) { box.replaceChildren(el('p', { class: 'nota' }, 'Nessuna email.')); return; }
    box.replaceChildren(...lista.map((m) => el('div', { class: 'voce' + (m.non_letta ? ' nuova' : ''), onclick: () => apriEmail(m.id) },
      el('div', { class: 'titolo' }, el('span', {}, m.oggetto)),
      el('div', { class: 'sotto' }, m.mittente + ' · ' + m.data),
      el('div', { class: 'sotto' }, m.anteprima))));
  } catch (e) { box.replaceChildren(el('p', { class: 'errore' }, e.message)); }
}
async function apriEmail(id) {
  const a = $('#email-aperta');
  a.hidden = false;
  a.replaceChildren(el('p', { class: 'nota' }, 'Apro...'));
  try {
    const m = await api('/api/gmail/email/' + encodeURIComponent(id));
    a.replaceChildren(el('h3', {}, m.oggetto), el('div', { class: 'sotto' }, `Da: ${m.mittente}\nData: ${m.data}`),
      el('div', { class: 'azioni' }, el('button', { class: 'btn piccolo', onclick: () => parla(`${m.oggetto}. ${m.corpo.slice(0, 1500)}`) }, 'Leggi ad alta voce')),
      el('div', {}, m.corpo));
    a.scrollIntoView({ behavior: 'smooth' });
  } catch (e) { a.replaceChildren(el('p', { class: 'errore' }, e.message)); }
}
$$('[data-gmail]').forEach((b) => b.addEventListener('click', () => caricaGmail(b.dataset.gmail, false)));
$('#btn-cerca-gmail').addEventListener('click', () => caricaGmail($('#cerca-gmail').value, true));

function disegnaPulizia(lista, pesanti) {
  const box = $('#lista-pulizia');
  if (!lista.length) { box.replaceChildren(el('p', { class: 'nota' }, 'Niente da pulire.')); $('#azioni-pulizia').hidden = true; return; }
  box.replaceChildren(...lista.map((m) => el('label', { class: 'voce' + (m.sicura ? ' sicura' : '') },
    el('div', { class: 'titolo' },
      el('span', {}, el('input', { type: 'checkbox', value: m.id, checked: pesanti ? false : m.sicura }), ' ', m.oggetto),
      el('span', { class: 'sotto' }, pesanti ? `${m.dimensione_mb} MB` : `${Math.round(m.punteggio * 100)}%`)),
    el('div', { class: 'sotto' }, `${m.mittente} · ${m.data}`),
    m.motivi ? el('div', { class: 'etichetta' }, m.motivi.join(' · ')) : null)));
  $('#azioni-pulizia').hidden = false;
}

async function analizzaPosta() {
  $('#lista-pulizia').replaceChildren(el('p', { class: 'nota' }, 'Analizzo la posta in arrivo (può richiedere un minuto)...'));
  try {
    const r = await api('/api/gmail/pulizia');
    disegnaPulizia(r, false);
    scrivi(`${r.filter((x) => x.sicura).length} email sopra la soglia del 90 per cento, ${r.filter((x) => !x.sicura).length} dubbie.`);
  } catch (e) { $('#lista-pulizia').replaceChildren(el('p', { class: 'errore' }, e.message)); }
}
$('#btn-analizza').addEventListener('click', analizzaPosta);
$('#btn-pesanti').addEventListener('click', async () => {
  $('#lista-pulizia').replaceChildren(el('p', { class: 'nota' }, 'Cerco le email pesanti...'));
  try { disegnaPulizia(await api('/api/gmail/pesanti'), true); } catch (e) { $('#lista-pulizia').replaceChildren(el('p', { class: 'errore' }, e.message)); }
});
$$('#azioni-pulizia [data-azione]').forEach((b) => b.addEventListener('click', async () => {
  const ids = $$('#lista-pulizia input:checked').map((i) => i.value);
  if (!ids.length) { scrivi(rimprovero('Non hai selezionato niente, testa vuota.', 'Nessuna email selezionata.'), true); suono('errore'); return; }
  if (b.dataset.azione === 'cestina' && !confirm(`Spostare ${ids.length} email nel cestino?`)) return;
  try {
    const r = await api('/api/gmail/azione', { azione: b.dataset.azione, ids });
    scrivi(`Fatto su ${r.fatte} email.`);
    $$('#lista-pulizia input:checked').forEach((i) => i.closest('.voce').remove());
    caricaSpazio();
  } catch (e) { scrivi(F.errore(e.message), true); }
}));
$('#btn-svuota').addEventListener('click', async () => {
  if (!confirm('Eliminare DEFINITIVAMENTE tutte le email nel cestino di Gmail? Non si può annullare.')) return;
  try {
    const r = await api('/api/gmail/azione', { azione: 'svuota_cestino', conferma: true });
    scrivi(`Eliminate definitivamente ${r.eliminate} email.`);
    caricaSpazio();
  } catch (e) { scrivi(F.errore(e.message), true); }
});

// =========================================================================
// TEAMS
// =========================================================================
let teamsUltimi = [];
function disegnaTeams(t) {
  const box = $('#lista-teams');
  if (!t.configurato) { box.replaceChildren(el('p', { class: 'nota' }, 'Teams non configurato (GUIDA, Fase 12).')); return; }
  teamsUltimi = t.messaggi;
  const righe = t.messaggi.map((m) => el('div', { class: 'voce nuova' },
    el('div', { class: 'titolo' }, el('span', {}, m.da), el('span', { class: 'sotto' }, dataOra(m.ora))),
    el('div', { class: 'etichetta' }, m.dove), el('div', {}, m.testo)));
  box.replaceChildren(...(righe.length ? righe : [el('p', { class: 'nota' }, 'Nessun nuovo messaggio.')]),
    ...(t.avvisi || []).map((a) => el('p', { class: 'nota' }, a)));
}
$('#btn-teams').addEventListener('click', async () => {
  $('#lista-teams').replaceChildren(el('p', { class: 'nota' }, 'Controllo Teams...'));
  try {
    const t = await api('/api/teams/nuovi');
    disegnaTeams(t);
    if (t.configurato) {
      scrivi(F.teams(t.messaggi.length));
      t.messaggi.slice(0, 8).forEach((m) => scrivi(`${m.da}, ${m.dove}: ${m.testo}`));
    }
  } catch (e) { $('#lista-teams').replaceChildren(el('p', { class: 'errore' }, e.message)); }
});
$('#btn-teams-letti').addEventListener('click', async () => {
  if (!teamsUltimi.length) return;
  await api('/api/teams/visti', { ids: teamsUltimi.map((m) => m.id) });
  disegnaTeams({ configurato: true, messaggi: [] });
});

// =========================================================================
// MSI
// =========================================================================
$$('[data-msi]').forEach((b) => b.addEventListener('click', () => {
  if (b.dataset.conferma && !confirm(b.dataset.conferma)) return;
  eseguiComando(b.dataset.msi);
}));

// =========================================================================
// MECCANICA
// =========================================================================
$('#form-meccanica').addEventListener('submit', async (e) => {
  e.preventDefault();
  const domanda = $('#domanda').value.trim();
  const box = $('#risposta-meccanica');
  if (!domanda) { scrivi(rimprovero('Domanda vuota. Complimenti.', 'Domanda vuota.'), true); return; }
  box.replaceChildren(el('p', { class: 'nota' }, 'Consulto il manuale...'));
  try {
    const r = await api('/api/comando', { testo: 'meccanica: ' + domanda });
    box.replaceChildren(el('div', {}, r.testo),
      r.fonti && r.fonti.length ? el('h3', {}, 'Fonti') : null,
      ...(r.fonti || []).map((f, i) => el('div', { class: 'sotto' }, `[${i + 1}] ${f.manuale} — ${f.sezione}`)));
    const senzaAI = r.testo.startsWith('(Ollama');
    scrivi(r.fonti && r.fonti.length ? F.manuale() + ' ' + (senzaAI ? r.testo.split('\n').slice(2, 6).join(' ').slice(0, 600) : r.testo) : r.testo);
  } catch (err) { box.replaceChildren(el('p', { class: 'errore' }, err.message)); }
});

// =========================================================================
// MEMORIA: fatti, documenti, comandi insegnati, non capiti
// =========================================================================
async function eliminaMemoria(tipo, id) {
  try { await api('/api/memoria/elimina', { tipo, id }); caricaMemoria(); } catch (e) { scrivi(F.errore(e.message), true); }
}

function rigaMemoria(titolo, sotto, tipo, id, extraBtn) {
  return el('div', { class: 'voce' },
    el('div', { class: 'titolo' }, el('span', {}, titolo),
      el('span', { class: 'azioni', style: 'margin:0' }, extraBtn || null,
        el('button', { class: 'btn piccolo sec', onclick: () => eliminaMemoria(tipo, id) }, 'Elimina'))),
    sotto ? el('div', { class: 'sotto' }, sotto) : null);
}

async function caricaMemoria() {
  try {
    const m = await api('/api/memoria');
    const vuoto = (t) => [el('p', { class: 'nota' }, t)];
    $('#lista-fatti').replaceChildren(...(m.fatti.length ? m.fatti.slice().reverse().map((f) =>
      rigaMemoria(f.testo, dataOra(f.ora), 'fatto', f.id)) : vuoto('Nessun fatto memorizzato.')));
    $('#lista-documenti').replaceChildren(...(m.documenti.length ? m.documenti.map((d) =>
      rigaMemoria(d.nome, `${d.kb || "<1"} KB di testo · ${dataOra(d.ora)}`, 'documento', d.nome)) : vuoto('Nessun documento.')));
    $('#lista-alias').replaceChildren(...(m.comandi.length ? m.comandi.map((a) =>
      rigaMemoria(`"${a.frase}"`, `→ ${a.comando}`, 'comando', a.id)) : vuoto('Nessun comando insegnato.')));
    $('#lista-non-capiti').replaceChildren(...(m.non_capiti.length ? m.non_capiti.slice().reverse().map((x) =>
      rigaMemoria(x.frase, `${x.volte} volte · ultima ${dataOra(x.ora)}`, 'non_capito', x.id,
        el('button', {
          class: 'btn piccolo',
          onclick: () => { $('#alias-frase').value = x.frase; $('#alias-comando').focus(); $('#alias-comando').scrollIntoView({ behavior: 'smooth' }); },
        }, 'Insegna'))) : vuoto('Niente: ho capito tutto.')));
  } catch (e) { $('#lista-fatti').replaceChildren(el('p', { class: 'errore' }, e.message)); }
}

$('#form-fatto').addEventListener('submit', async (e) => {
  e.preventDefault();
  const testo = $('#testo-fatto').value.trim();
  try {
    const r = await api('/api/memoria/fatto', { testo });
    $('#testo-fatto').value = '';
    scrivi(r.nuovo ? 'Memorizzato.' : 'Lo sapevo già.');
    caricaMemoria();
  } catch (err) { scrivi(err.message, true); suono('errore'); }
});

$('#form-alias').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    await api('/api/memoria/comando', { frase: $('#alias-frase').value, comando: $('#alias-comando').value });
    scrivi(`Imparato: quando dici "${$('#alias-frase').value.trim()}" eseguo "${$('#alias-comando').value.trim()}".`);
    $('#alias-frase').value = ''; $('#alias-comando').value = '';
    caricaMemoria();
  } catch (err) { scrivi(err.message, true); suono('errore'); }
});

$('#form-documento').addEventListener('submit', async (e) => {
  e.preventDefault();
  const file = $('#file-documento').files[0];
  if (!file) { scrivi(rimprovero('Non hai scelto nessun file, genio.', 'Nessun file scelto.'), true); suono('errore'); return; }
  const dati = new FormData();
  dati.append('file', file);
  scrivi('Leggo il documento...');
  try {
    const r = await fetch('/api/memoria/documento', { method: 'POST', body: dati });
    const corpo = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(corpo.errore || `Errore ${r.status}`);
    scrivi(`Documento ${corpo.nome} imparato: ${corpo.caratteri} caratteri di testo.`);
    $('#file-documento').value = '';
    caricaMemoria();
  } catch (err) { scrivi(err.message, true); suono('errore'); }
});

// =========================================================================
// FOTO E VIDEO
// =========================================================================
let mediaCache = [];
let daEvidenziare = new Set();

function caricaFileMedia(file, nome) {
  const descrizione = $('#descr-media').value.trim();
  const stato = $('#stato-media');
  if (!file) return;
  if (descrizione.split(/\s+/).filter(Boolean).length < 2) {
    scrivi(rimprovero('Prima scrivi una descrizione di almeno due parole, o non la ritroverai mai.', 'Serve una descrizione di almeno due parole.'), true);
    suono('errore');
    return;
  }
  const dati = new FormData();
  dati.append('file', file, nome || file.name);
  dati.append('descrizione', descrizione);
  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/media');
  xhr.upload.onprogress = (e) => { if (e.lengthComputable) stato.textContent = `Caricamento ${Math.round((e.loaded / e.total) * 100)}%...`; };
  xhr.onload = () => {
    let r = {};
    try { r = JSON.parse(xhr.responseText); } catch { /* niente */ }
    if (xhr.status === 401) { location.href = '/accesso'; return; }
    if (xhr.status >= 400) { stato.textContent = ''; scrivi(r.errore || `Errore ${xhr.status}`, true); suono('errore'); return; }
    stato.textContent = '';
    $('#descr-media').value = '';
    scrivi(`${r.tipo === 'video' ? 'Video' : 'Foto'} salvato: ${r.descrizione}.`);
    caricaMedia();
  };
  xhr.onerror = () => { stato.textContent = ''; scrivi('Caricamento non riuscito: server non raggiungibile.', true); };
  xhr.send(dati);
}
['#file-media', '#foto-ora', '#video-ora'].forEach((id) => $(id).addEventListener('change', (e) => {
  caricaFileMedia(e.target.files[0]);
  e.target.value = '';
}));

function evidenziaMedia(ids) { daEvidenziare = new Set(ids); disegnaGalleria(); }

async function caricaMedia() {
  try { mediaCache = await api('/api/media'); disegnaGalleria(); } catch (e) { $('#galleria').replaceChildren(el('p', { class: 'errore' }, e.message)); }
}

function disegnaGalleria() {
  const f = ($('#cerca-media').value || '').toLowerCase();
  const lista = mediaCache.filter((m) => m.descrizione.toLowerCase().includes(f));
  if (!lista.length) { $('#galleria').replaceChildren(el('p', { class: 'nota' }, mediaCache.length ? 'Nessun risultato.' : 'Galleria vuota.')); return; }
  $('#galleria').replaceChildren(...lista.map((m) => el('div', { class: 'scheda-media' + (daEvidenziare.has(m.id) ? ' evidenziata' : '') },
    m.tipo === 'video' ? el('video', { src: '/media/' + m.file, controls: true, preload: 'metadata', playsinline: true })
      : el('a', { href: '/media/' + m.file, target: '_blank', rel: 'noopener' }, el('img', { src: '/media/' + m.file, alt: m.descrizione, loading: 'lazy' })),
    el('div', { class: 'info' },
      el('strong', {}, m.descrizione),
      el('span', { class: 'sotto' }, `${m.tipo} · ${m.kb > 1024 ? (m.kb / 1024).toFixed(1) + ' MB' : m.kb + ' KB'} · ${dataOra(m.ora)}`),
      el('div', { class: 'azioni', style: 'margin:0' },
        el('button', { class: 'btn piccolo', onclick: () => apriInvioMedia(m) }, 'WhatsApp'),
        el('a', { class: 'btn piccolo sec', href: '/media/' + m.file, download: m.descrizione.replace(/[^\w\s-]/g, '') + m.file.slice(m.file.lastIndexOf('.')) }, 'Scarica'),
        el('button', {
          class: 'btn piccolo sec',
          onclick: async () => {
            if (!confirm('Eliminare questo file?')) return;
            await api('/api/media/elimina', { id: m.id }).catch(() => {});
            caricaMedia();
          },
        }, 'Elimina'))))));
}
$('#cerca-media').addEventListener('input', disegnaGalleria);

let mediaDaInviare = null;
async function apriInvioMedia(m) {
  mediaDaInviare = m;
  if (!chatCache.length) { try { chatCache = await api('/api/wa/chat'); } catch (e) { scrivi(e.message, true); return; } }
  $('#cerca-dest-media').value = '';
  $('#didascalia-media').value = m.descrizione;
  disegnaDestMedia();
  $('#dlg-media').showModal();
}
function disegnaDestMedia() {
  const f = $('#cerca-dest-media').value.toLowerCase();
  $('#lista-dest-media').replaceChildren(...chatCache.filter((c) => c.nome.toLowerCase().includes(f)).slice(0, 60).map((c) =>
    el('label', { class: 'interruttore' }, el('input', { type: 'radio', name: 'dest-media', value: c.id }), el('span', {}, c.nome))));
}
$('#cerca-dest-media').addEventListener('input', disegnaDestMedia);
$('#dlg-media').addEventListener('close', async () => {
  if ($('#dlg-media').returnValue !== 'ok' || !mediaDaInviare) return;
  const scelta = document.querySelector('input[name=dest-media]:checked');
  if (!scelta) { scrivi(rimprovero('Non hai scelto a chi mandarlo. Sveglia.', 'Nessuna chat scelta.'), true); return; }
  try {
    const r = await api('/api/media/invia', { id: mediaDaInviare.id, chat: scelta.value, didascalia: $('#didascalia-media').value });
    scrivi('Inviato su WhatsApp' + (r.come_documento ? ' come documento (file grande).' : '.'));
  } catch (e) { scrivi(F.errore(e.message), true); }
});

// Fotocamera / webcam (serve https o localhost)
let flusso = null;
let registratore = null;
let fotocamera = 'environment';
async function apriWebcam() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    scrivi("Fotocamera non disponibile da questo indirizzo: serve https o localhost. Sul telefono usa 'Scatta foto' / 'Registra video'.", true);
    return;
  }
  try {
    if (flusso) flusso.getTracks().forEach((t) => t.stop());
    flusso = await navigator.mediaDevices.getUserMedia({ video: { facingMode: fotocamera }, audio: true })
      .catch(() => navigator.mediaDevices.getUserMedia({ video: { facingMode: fotocamera } }));
    $('#webcam-video').srcObject = flusso;
    $('#webcam-zona').hidden = false;
  } catch (e) { scrivi('Accesso alla fotocamera negato o non disponibile: ' + e.message, true); }
}
function chiudiWebcam() {
  if (registratore && registratore.state === 'recording') registratore.stop();
  if (flusso) flusso.getTracks().forEach((t) => t.stop());
  flusso = null;
  $('#webcam-zona').hidden = true;
}
$('#btn-webcam').addEventListener('click', apriWebcam);
$('#btn-chiudi-webcam').addEventListener('click', chiudiWebcam);
$('#btn-gira').addEventListener('click', () => { fotocamera = fotocamera === 'environment' ? 'user' : 'environment'; apriWebcam(); });
$('#btn-scatta').addEventListener('click', () => {
  const v = $('#webcam-video');
  if (!v.videoWidth) return;
  const c = document.createElement('canvas');
  c.width = v.videoWidth; c.height = v.videoHeight;
  c.getContext('2d').drawImage(v, 0, 0);
  c.toBlob((b) => caricaFileMedia(b, `foto_${Date.now()}.jpg`), 'image/jpeg', 0.9);
  suono('notifica');
});
$('#btn-registra').addEventListener('click', () => {
  const b = $('#btn-registra');
  if (registratore && registratore.state === 'recording') { registratore.stop(); return; }
  if (!flusso || !window.MediaRecorder) { scrivi('Registrazione video non supportata da questo browser.', true); return; }
  const pezzi = [];
  const tipo = MediaRecorder.isTypeSupported('video/mp4') ? 'video/mp4' : 'video/webm';
  registratore = new MediaRecorder(flusso, { mimeType: tipo });
  registratore.ondataavailable = (e) => { if (e.data.size) pezzi.push(e.data); };
  registratore.onstop = () => {
    b.textContent = 'Registra video'; b.classList.remove('ascolta');
    caricaFileMedia(new Blob(pezzi, { type: tipo }), `video_${Date.now()}.${tipo === 'video/mp4' ? 'mp4' : 'webm'}`);
  };
  registratore.start();
  b.textContent = 'Stop'; b.classList.add('ascolta');
});

// =========================================================================
// APP PER TELEFONO (installazione)
// =========================================================================
let richiestaInstallazione = null;
addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); richiestaInstallazione = e; $('#btn-installa').hidden = false; });
$('#btn-installa').addEventListener('click', async () => {
  if (!richiestaInstallazione) return;
  richiestaInstallazione.prompt();
  await richiestaInstallazione.userChoice;
  richiestaInstallazione = null;
  $('#btn-installa').hidden = true;
});
if ('serviceWorker' in navigator && window.isSecureContext) navigator.serviceWorker.register('/sw.js').catch(() => {});

async function caricaTelefono() {
  const zona = $('#telefono-zona');
  try {
    const t = await api('/api/telefono');
    const parti = [];
    if (t.qr) parti.push(el('img', { class: 'qr-telefono', src: t.qr, alt: 'Codice QR per aprire Jarvis sul telefono' }));
    if (t.indirizzi.length) parti.push(el('p', {}, 'Inquadra il codice con la fotocamera del telefono oppure apri: ', el('strong', {}, t.indirizzi.join('  oppure  '))));
    if (t.solo_locale) parti.push(el('p', {}, 'Ora Jarvis è visibile solo da questo PC. Per il telefono: GUIDA, Fase 19 (HOST_PANNELLO e password, oppure Tailscale).'));
    parti.push(el('p', {}, 'Sul telefono, dopo averlo aperto: Android/Chrome → menu ⋮ → "Installa app" (o "Aggiungi a schermata Home"); iPhone/Safari → Condividi → "Aggiungi alla schermata Home".'));
    zona.replaceChildren(...parti);
  } catch (e) { zona.replaceChildren(e.message); }
}

// =========================================================================
// IMPOSTAZIONI
// =========================================================================
async function caricaImpostazioni() {
  const s = await statoWa();
  const zona = $('#qr-zona');
  if (!s) zona.replaceChildren('Servizio WhatsApp spento. Avvialo con avvia_server_jarvis.bat.');
  else if (s.pronto) zona.replaceChildren('WhatsApp collegato.');
  else if (s.qr) {
    zona.replaceChildren(el('p', {}, 'Sul telefono: WhatsApp → Dispositivi collegati → Collega un dispositivo, poi inquadra:'),
      el('img', { class: 'qr', src: s.qr, alt: 'Codice QR di collegamento WhatsApp' }));
  } else zona.replaceChildren('Avvio di WhatsApp in corso... riapri questa sezione tra qualche secondo.');

  if (!s || !s.pronto) return;
  try {
    const [imp, tutte] = await Promise.all([api('/api/wa/impostazioni'), api('/api/wa/chat?escluse=1&n=300')]);
    impWa = imp;
    const nomi = Object.fromEntries(tutte.map((c) => [c.id, c.nome]));
    $$('input[name=modo]').forEach((r) => { r.checked = r.value === imp.risposta_automatica; });
    const riga = (id, campo) => el('div', { class: 'voce' },
      el('div', { class: 'titolo' }, el('span', {}, nomi[id] || id),
        el('button', {
          class: 'btn piccolo sec',
          onclick: async () => {
            impWa = await api('/api/wa/impostazioni', { [campo]: impWa[campo].filter((x) => x !== id) });
            caricaImpostazioni();
          },
        }, 'Rimuovi')));
    $('#lista-auto').replaceChildren(...(imp.chat_risposta_auto.length ? imp.chat_risposta_auto.map((id) => riga(id, 'chat_risposta_auto'))
      : [el('p', { class: 'nota' }, 'Nessuna. Attivala dalla chat, sezione WhatsApp.')]));
    $('#lista-escluse').replaceChildren(...(imp.escluse.length ? imp.escluse.map((id) => riga(id, 'escluse'))
      : [el('p', { class: 'nota' }, 'Nessuna.')]));
  } catch (e) { $('#lista-escluse').replaceChildren(el('p', { class: 'errore' }, e.message)); }
}

$$('input[name=modo]').forEach((r) => r.addEventListener('change', async () => {
  try { impWa = await api('/api/wa/impostazioni', { risposta_automatica: r.value }); } catch (e) { scrivi(F.errore(e.message), true); }
}));

function preparaControlli() {
  $('#tono').value = pref.tono;
  $('#velocita').value = pref.velocita;
  $('#chk-saggio').checked = saggio();
  $('#chk-voce').checked = pref.attiva;
  $('#chk-suoni').checked = pref.suoni;
  $('#chk-particelle').checked = pref.particelle;
  $('#chk-avvio').checked = pref.avvio;
  $('#sel-voce').addEventListener('change', (e) => { pref.voce = e.target.value; salvaPref(); });
  $('#sel-motore').value = pref.motore === 'browser' ? 'browser' : 'server';
  $('#sel-motore').addEventListener('change', (e) => { pref.motore = e.target.value; salvaPref(); aggiornaStatoVoce(); });
  $('#tono').addEventListener('input', (e) => { pref.tono = e.target.value; salvaPref(); });
  $('#velocita').addEventListener('input', (e) => { pref.velocita = e.target.value; salvaPref(); });
  $('#chk-saggio').addEventListener('change', (e) => { pref.saggio = e.target.checked; salvaPref(); });
  $('#chk-voce').addEventListener('change', (e) => { pref.attiva = e.target.checked; salvaPref(); aggiornaStatoVoce(); });
  $('#chk-suoni').addEventListener('change', (e) => { pref.suoni = e.target.checked; salvaPref(); });
  $('#chk-particelle').addEventListener('change', (e) => { pref.particelle = e.target.checked; salvaPref(); });
  $('#chk-avvio').addEventListener('change', (e) => { pref.avvio = e.target.checked; salvaPref(); });
  $('#btn-prova-voce').addEventListener('click', () => parla(F.prova()));
}

// =========================================================================
// AVVIO
// =========================================================================
(async function avvio() {
  applicaTema();
  preparaControlli();
  try { profilo = await api('/api/profilo'); } catch { /* valori predefiniti */ }
  aggiornaStatoVoce();
  $('#nota-manuale').textContent = 'Fonte: ' + (profilo.manuali || []).join(', ') + ' (manuale del 1907). Risponde solo se il manuale copre almeno il 90% dei termini.';
  $('#chk-saggio').checked = saggio();
  if (sintesi) { caricaVoci(); sintesi.addEventListener('voiceschanged', caricaVoci); }
  const attivazione = parametri.get('attivazione') === '1';
  if (attivazione) {
    history.replaceState(null, '', location.pathname + (document.body.classList.contains('compatto') ? '?modo=r1' : ''));
    await sequenzaAvvio();
  }
  statoWa(); aggiornaMeteo(); aggiornaSistema(); aggiornaAgenda(); aggiornaPromemoria(); controllaAnnunci();
  if (attivazione) await rapporto(true); else aggiornaSegreteria(false);
  setInterval(() => { aggiornaSegreteria(true); statoWa(); aggiornaSistema(); }, 20000);
  setInterval(controllaAnnunci, 3000);
  setInterval(aggiornaMeteo, 15 * 60 * 1000);
}());
