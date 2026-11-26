/* JARVIS - pannello web */
'use strict';

const $ = (s) => document.querySelector(s);

// replaceChildren del browser scrive "null" per gli elementi vuoti: li togliamo noi, ovunque.
const _replaceChildrenOriginale = Element.prototype.replaceChildren;
Element.prototype.replaceChildren = function replaceChildrenSicuro(...figli) {
  return _replaceChildrenOriginale.apply(this, figli.flat().filter((f) => f !== null && f !== undefined && f !== false));
};
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
  tema: 'ciano', suoni: true, particelle: true, avvio: true, ascoltoSempre: false,
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
  if (nome === 'github') caricaGitHub();
  if (nome === 'compiti') { caricaCompiti(); statoClasseViva(); }
  if (nome === 'casa') caricaCasa();
  if (nome === 'perte') caricaPerTe();
  if (nome === 'scrittura') { preparaLavagna(); statoScrittura(); }
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
  if (r.azione_pannello === 'scrittura') mostraSezione('scrittura');
  if (r.azione_pannello === 'compiti') mostraSezione('compiti');
  if (r.azione_pannello === 'perte') mostraSezione('perte');
  if (r.azione_pannello === 'guida' && r.guida) apriGuida(r.guida);
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
// ASCOLTO SEMPRE ATTIVO NEL PANNELLO ("Jarvis attivazione", come Alexa)
// Usa il riconoscimento vocale del browser (Chrome/Edge: l'audio viene elaborato dai server
// di Google/Microsoft). Funziona solo con il pannello aperto e in primo piano.
// =========================================================================
const RX_ATTIVAZIONE = /\b(jarvis|giarvis|jervis|jarvi|giarvi|gervis|travis)\b[\s,.]*(attivazione|attiva|attivati|attivo)\b/i;
let ascoltoAttivo = false;
let riconoscitoreContinuo = null;
let attesaComando = false;
let timerComando = null;
let ultimoErroreAscolto = 0;

function aggiornaPillolaAscolto(stato) {
  const p = $('#stato-ascolto');
  if (!p) return;
  p.hidden = !ascoltoAttivo && stato !== 'errore';
  p.textContent = stato === 'comando' ? 'Ti ascolto…' : stato === 'errore' ? 'Ascolto: errore' : 'In ascolto';
  p.className = 'pillola ' + (stato === 'comando' ? 'ok ascolta-pillola' : stato === 'errore' ? 'ko' : 'ok');
}

function terminaAttesaComando() {
  attesaComando = false;
  clearTimeout(timerComando);
  aggiornaPillolaAscolto('attivo');
}

function gestisciFraseSentita(frase) {
  const testo = frase.trim();
  if (!testo) return;
  if (attesaComando) {
    terminaAttesaComando();
    if (/^(basta|grazie|niente|stop|annulla)\b/i.test(testo)) { suono('clic'); return; }
    $('#testo-comando').value = testo;
    eseguiComando(testo, true); // domanda a voce -> risposta a voce
    return;
  }
  const m = testo.match(RX_ATTIVAZIONE);
  if (!m) return;
  const resto = testo.slice(m.index + m[0].length).replace(/^[\s,.]+/, '');
  suono('notifica');
  if (resto.length > 2) { // "Jarvis attivazione che ore sono" tutto insieme
    $('#testo-comando').value = resto;
    eseguiComando(resto, true);
    return;
  }
  attesaComando = true;
  aggiornaPillolaAscolto('comando');
  parla('Sì?', false, true);
  timerComando = setTimeout(() => { if (attesaComando) { terminaAttesaComando(); suono('clic'); } }, 8000);
}

function avviaAscoltoContinuo() {
  if (!Riconoscitore) { scrivi('Questo browser non ha il riconoscimento vocale: usa Chrome o Edge.', true); return false; }
  if (riconoscitoreContinuo) return true;
  const r = new Riconoscitore();
  r.lang = 'it-IT';
  r.continuous = true;
  r.interimResults = false;
  r.onresult = (ev) => {
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      // mentre Jarvis parla ignora quello che sente (non deve rispondere a se stesso)
      if (ev.results[i].isFinal && !parlaOra) gestisciFraseSentita(ev.results[i][0].transcript);
    }
  };
  r.onerror = (ev) => {
    if (ev.error === 'not-allowed' || ev.error === 'service-not-allowed') {
      ascoltoAttivo = false; pref.ascoltoSempre = false; salvaPref();
      $('#chk-ascolto').checked = false;
      scrivi('Microfono non permesso: consenti il microfono a questa pagina nelle impostazioni del browser.', true);
      aggiornaPillolaAscolto('errore');
    }
    ultimoErroreAscolto = Date.now();
  };
  r.onend = () => {
    riconoscitoreContinuo = null;
    // il browser chiude l'ascolto dopo un po': si riavvia da solo finche' l'interruttore e' acceso
    if (ascoltoAttivo) setTimeout(avviaAscoltoContinuo, Date.now() - ultimoErroreAscolto < 3000 ? 2500 : 300);
  };
  try { r.start(); riconoscitoreContinuo = r; aggiornaPillolaAscolto('attivo'); return true; } catch { return false; }
}

function impostaAscoltoSempre(attivo) {
  ascoltoAttivo = attivo;
  pref.ascoltoSempre = attivo; salvaPref();
  if (attivo) avviaAscoltoContinuo();
  else if (riconoscitoreContinuo) { const r = riconoscitoreContinuo; riconoscitoreContinuo = null; r.abort(); }
  aggiornaPillolaAscolto('attivo');
}
$('#chk-ascolto').addEventListener('change', (e) => impostaAscoltoSempre(e.target.checked));
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && ascoltoAttivo) avviaAscoltoContinuo();
});

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
    const r = await api('/api/agenda');
    const nuovi = new Set((await api('/api/agenda/nuovi?segna=0')).map((x) => x.id));
    const lista = [...r.impegni.filter((x) => nuovi.has(x.id)), ...r.impegni.filter((x) => !nuovi.has(x.id))].slice(0, 8);
    $('#w-agenda').replaceChildren(...(lista.length ? lista.map((x) => el('div', { class: nuovi.has(x.id) ? 'nuovo-agenda' : '' },
      nuovi.has(x.id) ? el('span', { class: 'badge-nuovo' }, 'NUOVO') : null,
      el('strong', {}, dataOra(x.quando) + ' '), x.titolo,
      x.dettaglio ? el('div', { class: 'sotto nota' }, x.dettaglio.slice(0, 90)) : null))
      : [el('span', { class: 'nota' }, 'Nessun impegno nei prossimi 7 giorni.' + (r.avvisi.length ? ' ' + r.avvisi.join(' ') : ''))]));
  } catch (e) { $('#w-agenda').replaceChildren(el('span', { class: 'nota' }, e.message.slice(0, 120))); }
  try {
    return await api('/api/calendario/oggi'); // impegni di oggi, letti nel rapporto
  } catch { return null; }
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
    try {
      const nuoviAgenda = await api('/api/agenda/nuovi');
      if (nuoviAgenda.length) parla('Nuovo in agenda: ' + nuoviAgenda.map((x) => x.frase).join('; ') + '.');
    } catch { /* agenda non disponibile */ }
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

    try {
      const g = await api('/api/github');
      if (g.configurato) {
        const n = (g.notifiche || []).filter((x) => x.non_letta);
        parla(n.length ? `GitHub: ${n.length} notifiche. ` + n.slice(0, 4).map((x) => `${x.repo.split('/')[1]}: ${x.titolo}`).join('; ') : 'GitHub: nessuna notifica.');
      }
    } catch { /* GitHub non collegato */ }

    try {
      const c = (await api('/api/compiti')).filter((b) => b.stato === 'da_rivedere');
      if (c.length) parla(`Compiti: ${c.length} richieste di esercizi con la bozza pronta. ` + c.slice(0, 3).map((b) => `${b.da}: ${b.esercizi.length} esercizi ${b.tipo === 'foglio' ? 'su foglio' : 'da inviare'}`).join('; '));
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
// PER TE: ritratto, gusti, scoperte, oggetti seguiti, guide
// =========================================================================
async function caricaPerTe() {
  try {
    const d = await api('/api/pertete');
    $('#ritratto-testo').textContent = d.ritratto;
    const p = d.profilo;
    $('#interessi').replaceChildren(...(p.interessi.length ? p.interessi.map((i) => el('span', { class: 'chip', title: `${i.categoria} · peso ${i.peso}` },
      i.termine, el('button', { class: 'chip-x', title: 'Dimentica', onclick: () => azionePerTe('dimentica', i.termine) }, '×')))
      : [el('span', { class: 'nota' }, 'Ancora niente: dimmi cosa ti piace o usami di più.')]));
    $('#non-piace').textContent = p.non_piace.length ? 'Non ti interessano: ' + p.non_piace.join(', ') : '';
    $('#oggetti-seguiti').replaceChildren(...(d.oggetti.length ? d.oggetti.map((o) => el('span', { class: 'chip' }, o.nome,
      el('button', { class: 'chip-x', title: 'Smetti di seguire', onclick: () => azionePerTe('smetti', o.nome) }, '×')))
      : [el('span', { class: 'nota' }, 'Nessun oggetto seguito.')]));
    $('#abitudini').replaceChildren(...(d.abitudini.length ? d.abitudini.slice(0, 8).map((a) =>
      el('li', {}, `${a.quando} verso le ${a.ora}: "${a.comando}" (${a.volte} giorni)`)) : [el('li', { class: 'nota' }, 'Nessuna abitudine riconosciuta finora.')]));
    $('#lista-guide').replaceChildren(...(d.guide.length ? d.guide.map((g) => el('div', { class: 'voce', onclick: () => apriGuida(g.id) },
      el('div', { class: 'titolo' }, el('span', {}, g.titolo), el('span', { class: 'sotto' }, `${g.passi} passi · ${g.creata}`))))
      : [el('p', { class: 'nota' }, 'Nessuna guida. Chiedi: "come si costruisce un aquilone".')]));
  } catch (e) { $('#ritratto-testo').textContent = e.message; }
}

async function azionePerTe(azione, testo) {
  try { await api('/api/pertete/' + azione, { testo }); caricaPerTe(); } catch (e) { scrivi(e.message, true); }
}

async function caricaScoperte() {
  const box = $('#lista-scoperte');
  box.replaceChildren(el('p', { class: 'nota' }, 'Cerco novità sui tuoi interessi...'));
  try {
    const r = await api('/api/pertete/scoperte');
    const voci = r.scoperte.map((x) => el('div', { class: 'voce' },
      el('div', { class: 'titolo' }, el('a', { href: x.link, target: '_blank', rel: 'noopener' }, x.titolo)),
      el('div', { class: 'sotto' }, `${x.fonte} · ${dataOra(new Date(x.quando * 1000).toISOString())} · perché: ${x.perche}`),
      el('div', { class: 'azioni', style: 'margin:4px 0 0' },
        el('button', { class: 'btn piccolo sec', title: 'Mi interessa', onclick: async (ev) => { await api('/api/pertete/feedback', { link: x.link, titolo: x.titolo, voto: 1 }); ev.target.textContent = '👍 ok'; } }, '👍'),
        el('button', { class: 'btn piccolo sec', title: 'Non mi interessa', onclick: async (ev) => { await api('/api/pertete/feedback', { link: x.link, titolo: x.titolo, voto: -1 }); ev.target.closest('.voce').remove(); } }, '👎'))));
    const negozi = Object.entries(r.negozi).map(([nome, link]) => el('div', { class: 'voce' },
      el('strong', {}, `Cerca "${nome}": `), ...Object.entries(link).map(([n, u]) => el('a', { class: 'btn piccolo sec', href: u, target: '_blank', rel: 'noopener' }, n))));
    box.replaceChildren(...(voci.length ? voci : [el('p', { class: 'nota' }, 'Nessuna novità trovata.' + (r.avvisi[0] ? ' ' + r.avvisi[0] : ''))]),
      negozi.length ? el('h3', {}, 'Oggetti che segui: dove cercarli') : null, ...negozi);
  } catch (e) { box.replaceChildren(el('p', { class: 'errore' }, e.message)); }
}

let guidaAperta = null;
function disegnaGuida(g) {
  guidaAperta = g;
  const zona = $('#guida-zona');
  zona.hidden = false;
  zona.replaceChildren(
    el('h3', {}, g.titolo + (g.difficolta ? ` · ${g.difficolta}` : '') + (g.tempo ? ` · ${g.tempo}` : '')),
    g.senza_ai ? el('p', { class: 'nota' }, 'Ollama non è attivo: ecco le fonti trovate invece di una guida scritta passo per passo (GUIDA, Fase 6).') : null,
    g.sicurezza && g.sicurezza.length ? el('div', { class: 'avviso-sicurezza' }, '⚠ ', g.sicurezza.join(' ')) : null,
    g.materiali && g.materiali.length ? el('p', {}, el('strong', {}, 'Materiali: '), g.materiali.join(', ')) : null,
    g.attrezzi && g.attrezzi.length ? el('p', {}, el('strong', {}, 'Attrezzi: '), g.attrezzi.join(', ')) : null,
    el('ol', { class: 'passi-guida' }, ...g.passi.map((p, i) => el('li', { class: i === g.passo ? 'passo-attuale' : (i < g.passo ? 'passo-fatto' : '') },
      el('strong', {}, p.titolo), el('div', {}, p.dettaglio)))),
    g.consigli && g.consigli.length ? el('p', { class: 'nota' }, 'Consigli: ' + g.consigli.join(' ')) : null,
    el('div', { class: 'azioni' },
      el('button', { class: 'btn sec', onclick: () => muoviGuida('indietro') }, '◀ Passo precedente'),
      el('button', { class: 'btn', onclick: () => muoviGuida('avanti') }, 'Passo successivo ▶'),
      el('button', { class: 'btn sec', onclick: () => parla(`Passo ${g.passo + 1}: ${g.passi[g.passo].titolo}. ${g.passi[g.passo].dettaglio}`) }, 'Leggimelo')),
    g.fonti && g.fonti.length ? el('p', { class: 'sotto' }, 'Fonti: ', ...g.fonti.map((f) => (f.url ? el('a', { href: f.url, target: '_blank', rel: 'noopener' }, f.fonte + ' ') : f.fonte + ' '))) : null);
}
async function apriGuida(id) { try { disegnaGuida(await api('/api/guide/' + id)); mostraSezione('perte'); } catch (e) { scrivi(e.message, true); } }
async function muoviGuida(direzione) {
  try { const r = await api('/api/guide/muovi', { direzione }); disegnaGuida(r.guida); scrivi(r.testo); } catch (e) { scrivi(e.message, true); }
}

$('#form-piace').addEventListener('submit', (e) => { e.preventDefault(); const t = $('#piace-testo').value.trim(); $('#piace-testo').value = ''; azionePerTe('piace', t); });
$('#btn-non-piace').addEventListener('click', () => { const t = $('#piace-testo').value.trim(); $('#piace-testo').value = ''; azionePerTe('non_piace', t); });
$('#form-segui').addEventListener('submit', (e) => { e.preventDefault(); const t = $('#segui-testo').value.trim(); $('#segui-testo').value = ''; azionePerTe('segui', t); });
$('#btn-scoperte').addEventListener('click', caricaScoperte);
$('#btn-leggi-ritratto').addEventListener('click', () => parla($('#ritratto-testo').textContent));
$('#form-guida').addEventListener('submit', async (e) => {
  e.preventDefault();
  const t = $('#guida-testo').value.trim();
  if (!t) { scrivi(rimprovero('Costruire cosa? Il nulla?', 'Scrivi cosa vuoi costruire.'), true); return; }
  scrivi('Preparo la guida (con Ollama può richiedere qualche minuto)...');
  try {
    const r = await api('/api/comando', { testo: 'come si costruisce ' + t });
    if (r.guida) { apriGuida(r.guida); caricaPerTe(); }
    scrivi(r.testo, r.esito !== 'ok');
  } catch (err) { scrivi(err.message, true); }
});
$('#btn-cancella-profilo').addEventListener('click', async () => {
  if (!confirm('Cancellare TUTTO quello che Jarvis ha imparato sui tuoi gusti? Non si può annullare.')) return;
  await api('/api/pertete/cancella_tutto', { conferma: true }); caricaPerTe();
});

// =========================================================================
// CASA: Alexa, Spotify, Discord
// =========================================================================
async function caricaCasa() {
  // Alexa
  try {
    const s = await api('/api/alexa/stato');
    if (s.pronto) {
      const d = await api('/api/alexa/dispositivi');
      $('#alexa-stato').replaceChildren(el('span', { class: 'esito-ok' }, 'Alexa collegata. '),
        el('span', {}, 'Echo: ' + (d.echo.map((x) => x.nome).join(', ') || 'nessuno')));
      $('#alexa-dispositivi').replaceChildren(...(d.casa.length ? d.casa : ['(elenco non disponibile: usa i nomi che usi con Alexa)']).map((n) =>
        el('button', { class: 'btn piccolo sec', onclick: () => { $('#alexa-testo').value = `accendi ${n}`; $('#alexa-testo').focus(); } }, n)));
    } else {
      $('#alexa-stato').replaceChildren(el('span', { class: 'esito-ko' }, 'Alexa non collegata. '),
        el('span', {}, 'Dal PC server apri '), el('a', { href: s.accesso || 'http://127.0.0.1:3456', target: '_blank', rel: 'noopener' }, s.accesso || 'http://127.0.0.1:3456'),
        el('span', {}, ' e accedi ad Amazon.'));
    }
  } catch (e) { $('#alexa-stato').textContent = e.message; }
  // Spotify
  try {
    const s = await api('/api/spotify/stato');
    if (!s.collegato) {
      $('#spotify-stato').replaceChildren(s.client_id
        ? el('span', {}, 'Non collegato. Dal PC server: ', el('a', { href: '/spotify/accedi' }, 'collega Spotify'))
        : el('span', {}, 'Manca SPOTIFY_CLIENT_ID in config.py (GUIDA, Fase 27).'));
    } else if (s.errore) {
      $('#spotify-stato').textContent = s.errore;
    } else {
      $('#spotify-stato').textContent = s.in_ascolto ? `${s.in_ascolto.in_riproduzione ? '▶' : '⏸'} ${s.in_ascolto.titolo} – ${s.in_ascolto.artisti}` : 'Collegato. Niente in riproduzione.';
    }
  } catch (e) { $('#spotify-stato').textContent = e.message; }
  caricaDiscord();
}

async function caricaDiscord(canale) {
  try {
    const r = await api('/api/discord/messaggi' + (canale ? '?canale=' + encodeURIComponent(canale) : ''));
    const sel = $('#discord-canale');
    if (!sel.options.length) sel.replaceChildren(...r.canali.map((c) => el('option', { value: c }, '#' + c)));
    sel.value = r.canale;
    $('#discord-messaggi').replaceChildren(...(r.messaggi.length ? r.messaggi.map((m) =>
      el('div', { class: 'voce' }, el('div', { class: 'titolo' }, el('span', {}, m.autore), el('span', { class: 'sotto' }, dataOra(m.ora))), el('div', {}, m.testo)))
      : [el('p', { class: 'nota' }, 'Nessun messaggio.')]));
  } catch (e) { $('#discord-messaggi').replaceChildren(el('p', { class: 'nota' }, e.message)); }
}

$('#form-alexa').addEventListener('submit', (e) => {
  e.preventDefault();
  const t = $('#alexa-testo').value.trim();
  if (!t) { scrivi(rimprovero('Cosa devo dire ad Alexa? Niente, a quanto pare.', 'Comando vuoto.'), true); return; }
  $('#alexa-testo').value = '';
  eseguiComando('alexa ' + t);
});
$$('[data-spotify]').forEach((b) => b.addEventListener('click', async () => { await eseguiComando(b.dataset.spotify); setTimeout(caricaCasa, 1200); }));
$('#form-spotify').addEventListener('submit', (e) => {
  e.preventDefault();
  const q = $('#spotify-cerca').value.trim();
  if (q) eseguiComando(`metti ${q} su spotify`);
  $('#spotify-cerca').value = '';
});
$('#discord-canale').addEventListener('change', (e) => caricaDiscord(e.target.value));
$('#form-discord').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const r = await api('/api/discord/scrivi', { canale: $('#discord-canale').value, testo: $('#discord-testo').value });
    scrivi(`Scritto su Discord in #${r.canale}.`); $('#discord-testo').value = ''; caricaDiscord(r.canale);
  } catch (err) { scrivi(err.message, true); }
});

// =========================================================================
// CLASSEVIVA (nella sezione Compiti)
// =========================================================================
async function statoClasseViva() {
  try {
    const s = await api('/api/classeviva/stato');
    $('#form-classeviva').hidden = s.collegato;
    $('#cv-collegato').hidden = !s.collegato;
  } catch { /* niente */ }
}
$('#form-classeviva').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const r = await api('/api/classeviva/accedi', { utente: $('#cv-utente').value, password: $('#cv-password').value });
    $('#cv-password').value = '';
    scrivi(`ClasseViva collegato: ${r.nome || r.utente}.`); statoClasseViva();
  } catch (err) { scrivi(err.message, true); suono('errore'); }
});
$('#btn-cv-scollega').addEventListener('click', async () => {
  if (!confirm('Scollegare ClasseViva? Le credenziali verranno cancellate dal server.')) return;
  await api('/api/classeviva/scollega', {}); statoClasseViva();
});

// =========================================================================
// COMPITI (bozze: si inviano solo scrivendo/dicendo "manda esercizio")
// =========================================================================
async function caricaCompiti() {
  const box = $('#lista-compiti');
  try {
    const lista = await api('/api/compiti');
    const attive = lista.filter((b) => b.stato === 'da_rivedere');
    const altre = lista.filter((b) => b.stato !== 'da_rivedere').slice(0, 10);
    if (!lista.length) { box.replaceChildren(el('p', { class: 'nota' }, 'Nessuna richiesta di esercizi trovata.')); return; }
    box.replaceChildren(...attive.map((b, i) => schedaCompito(b, i + 1)),
      altre.length ? el('h3', {}, 'Già gestite') : null,
      ...altre.map((b) => el('div', { class: 'voce' },
        el('div', { class: 'titolo' }, el('span', {}, `${b.da} – ${b.titolo}`), el('span', { class: 'sotto' }, b.stato === 'inviata' ? 'inviata ' + dataOra(b.inviata) : b.stato)))));
  } catch (e) { box.replaceChildren(el('p', { class: 'errore' }, e.message)); }
}

function schedaCompito(b, numero) {
  const inviabile = ['teams_chat', 'gmail', 'posta_scuola'].includes(b.fonte);
  const area = el('textarea', { class: 'campo editor compito-risposta' });
  area.value = b.risposta;
  const dettagli = el('div', { class: 'compito-dettagli', hidden: !b.mostrato },
    el('h3', {}, 'Cosa devi fare'),
    el('ul', {}, ...b.cosa_fare.map((x) => el('li', {}, x))),
    el('h3', {}, 'Messaggio del professore'),
    el('div', { class: 'citazione-prof' }, b.testo),
    ...b.esercizi.map((e, i) => el('div', { class: 'esercizio' },
      el('strong', {}, `Esercizio ${i + 1}`), el('div', {}, e.testo),
      el('div', { class: 'consigli' }, el('em', {}, 'Consigli: '), el('ul', {}, ...e.consigli.map((c) => el('li', {}, c)))),
      e.risolto ? el('details', {}, el('summary', {}, 'Soluzione per controllo'),
        el('ol', {}, ...e.passi.map((p) => el('li', {}, p))), el('strong', {}, e.risultato))
        : el('div', { class: 'sotto' }, 'Non risolto in automatico: segui i consigli o scrivimi il testo completo.'))),
    inviabile ? el('h3', {}, 'Risposta da inviare (puoi modificarla)') : null,
    inviabile ? area : el('p', { class: 'nota' }, b.fonte === 'teams_compito'
      ? 'Compito di Teams: si consegna dall\'app Teams (apri il link) caricando la foto o il file.'
      : b.fonte === 'classeviva' ? 'Compito da ClasseViva: non si invia da qui, va svolto e consegnato come chiede il professore.' : ''),
    el('div', { class: 'azioni' },
      inviabile ? el('button', {
        class: 'btn',
        onclick: async () => {
          if (area.value !== b.risposta) await api('/api/compiti/modifica', { id: b.id, risposta: area.value });
          const conferma = prompt('Per inviare scrivi esattamente: manda esercizio');
          if (conferma === null) return;
          try {
            const r = await api('/api/compiti/invia', { id: b.id, conferma });
            scrivi(`Esercizio inviato: ${r.dove}.`); caricaCompiti();
          } catch (e) { scrivi(e.message, true); suono('errore'); }
        },
      }, 'Manda esercizio') : null,
      b.url ? el('a', { class: 'btn sec', href: b.url, target: '_blank', rel: 'noopener' }, 'Apri su Teams') : null,
      el('button', { class: 'btn sec', onclick: () => parla(`Esercizio ${numero}. ${b.cosa_fare.join(' ')} ` + b.esercizi.map((e, i) => `Esercizio ${i + 1}: ${e.testo}. ${e.consigli[0] || ''}`).join(' ')) }, 'Leggimelo'),
      el('button', { class: 'btn piccolo pericolo', onclick: async () => { if (confirm('Scartare questa bozza?')) { await api('/api/compiti/scarta', { id: b.id }); caricaCompiti(); } } }, 'Scarta')));
  const vedi = el('button', {
    class: 'btn piccolo' + (b.mostrato ? ' sec' : ''),
    onclick: async () => {
      dettagli.hidden = !dettagli.hidden;
      if (!b.mostrato) { await api('/api/compiti/mostrata', { id: b.id }); b.mostrato = true; vedi.className = 'btn piccolo sec'; }
    },
  }, b.mostrato ? 'Nascondi/mostra' : 'Vedi bozza');
  return el('div', { class: 'voce nuova compito' },
    el('div', { class: 'titolo' }, el('span', {}, `${numero}) ${b.da} – ${b.titolo}`),
      el('span', { class: 'etichetta' }, b.tipo === 'foglio' ? 'SU FOGLIO' : 'DA INVIARE')),
    el('div', { class: 'sotto' }, `${b.esercizi.length} esercizi · ${dataOra(b.creata)}` + (b.scadenza ? ` · scadenza ${dataOra(b.scadenza)}` : '')),
    el('div', { class: 'azioni', style: 'margin:6px 0' }, vedi),
    dettagli);
}

$('#btn-controlla-compiti').addEventListener('click', async () => {
  scrivi('Controllo Teams e posta...');
  try {
    const r = await api('/api/compiti/scansiona', {});
    scrivi(r.nuove ? `Trovate ${r.nuove} nuove richieste di esercizi.` : 'Nessuna nuova richiesta.' + (r.avvisi.length ? ' ' + r.avvisi.join(' ') : ''));
    caricaCompiti();
  } catch (e) { scrivi(e.message, true); }
});

// =========================================================================
// SCRITTURA A MANO
// =========================================================================
let lavagnaPronta = false;
let sessioneScrittura = null;
let modoAllena = false;
const DA_ALLENARE = 'abcdefghijklmnopqrstuvwxyz0123456789'.split('');
let indiceAllena = 0;

function pulisciLavagna() {
  const c = $('#lavagna'); const ctx = c.getContext('2d');
  ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, c.width, c.height);
}

function preparaLavagna() {
  if (lavagnaPronta) return;
  lavagnaPronta = true;
  const c = $('#lavagna'); const ctx = c.getContext('2d');
  pulisciLavagna();
  ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = '#101418'; ctx.lineWidth = 9;
  let disegna = false;
  const punto = (e) => { const r = c.getBoundingClientRect(); return [(e.clientX - r.left) * c.width / r.width, (e.clientY - r.top) * c.height / r.height]; };
  c.addEventListener('pointerdown', (e) => {
    disegna = true; c.setPointerCapture(e.pointerId);
    const [x, y] = punto(e); ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 0.1, y + 0.1); ctx.stroke();
  });
  c.addEventListener('pointermove', (e) => { if (!disegna) return; const [x, y] = punto(e); ctx.lineTo(x, y); ctx.stroke(); });
  const fine = () => { disegna = false; };
  c.addEventListener('pointerup', fine); c.addEventListener('pointercancel', fine);
}

async function statoScrittura() {
  try {
    const s = await api('/api/scrittura/stato');
    $('#stato-scrittura').textContent = `Esempi imparati dalla tua calligrafia: ${s.tuoi} (su ${s.totale} totali) · parole confermate: ${s.parole_imparate}.`;
  } catch (e) { $('#stato-scrittura').textContent = e.message; }
}

function mostraLettura(r) {
  sessioneScrittura = r.sessione;
  const elementi = [];
  r.righe.forEach((riga, i) => {
    if (i) elementi.push(el('div', { class: 'a-capo' }));
    riga.forEach((p) => {
      elementi.push(el('div', { class: 'parola-letta' + (p.dubbio ? ' dubbio' : '') },
        el('input', { class: 'campo', value: p.testo, 'data-id': p.id, autocomplete: 'off', list: 'alt-' + p.id }),
        el('datalist', { id: 'alt-' + p.id }, ...p.alternative.map((a) => el('option', { value: a }))),
        el('span', { class: 'sotto' }, `${Math.round(p.certezza * 100)}%` + (p.dubbio ? ' · non sono sicuro: correggi se serve' : ''))));
    });
  });
  $('#risultato-scrittura').replaceChildren(...elementi);
  $('#risultato-scrittura-zona').hidden = false;
  const letto = r.testo.replace(/\n/g, ' ');
  if (r.dubbi) scrivi(`Ho letto: "${letto}". Non sono sicuro di ${r.dubbi} parol${r.dubbi === 1 ? 'a' : 'e'}: correggi e premi "Conferma e impara".`);
  else scrivi(`Ho letto: "${letto}".`);
}

async function riconosciImmagine(immagine, file) {
  try {
    let r;
    if (file) {
      const dati = new FormData(); dati.append('file', file);
      const risposta = await fetch('/api/scrittura/riconosci', { method: 'POST', body: dati });
      r = await risposta.json();
      if (!risposta.ok) throw new Error(r.errore || 'Errore');
    } else {
      r = await api('/api/scrittura/riconosci', { immagine });
    }
    mostraLettura(r);
  } catch (e) { scrivi(e.message, true); suono('errore'); }
}

$('#btn-riconosci').addEventListener('click', () => { preparaLavagna(); riconosciImmagine($('#lavagna').toDataURL('image/png')); });
$('#btn-cancella-lavagna').addEventListener('click', pulisciLavagna);
$('#foto-scritta').addEventListener('change', (e) => { if (e.target.files[0]) riconosciImmagine(null, e.target.files[0]); e.target.value = ''; });

function testoLetto() {
  return $$('#risultato-scrittura input').map((i) => i.value.trim()).filter(Boolean).join(' ');
}
$('#btn-conferma-scrittura').addEventListener('click', async () => {
  if (!sessioneScrittura) return;
  const correzioni = Object.fromEntries($$('#risultato-scrittura input').map((i) => [i.dataset.id, i.value.trim()]));
  try {
    const r = await api('/api/scrittura/correggi', { sessione: sessioneScrittura, correzioni });
    scrivi(`Imparato: ${r.lettere_imparate} lettere da ${r.parole_imparate} parole` + (r.solo_vocabolario ? `, ${r.solo_vocabolario} parole solo nel vocabolario.` : '.'));
    statoScrittura();
  } catch (e) { scrivi(e.message, true); }
});
$('#btn-usa-comando').addEventListener('click', () => { const t = testoLetto(); if (t) eseguiComando(t); });
$('#btn-copia-testo').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(testoLetto()); scrivi('Testo copiato.'); } catch { scrivi('Copia non permessa da questo browser.', true); }
});

function aggiornaAllena() { $('#lettera-da-allenare').textContent = DA_ALLENARE[indiceAllena % DA_ALLENARE.length]; }
$('#btn-modo-allena').addEventListener('click', () => {
  modoAllena = !modoAllena;
  $('#allena-zona').hidden = !modoAllena;
  $('#btn-modo-allena').textContent = modoAllena ? 'Fine allenamento' : 'Allenamento';
  preparaLavagna(); pulisciLavagna(); aggiornaAllena();
});
$('#btn-salva-lettera').addEventListener('click', async () => {
  try {
    const lettera = DA_ALLENARE[indiceAllena % DA_ALLENARE.length];
    const r = await api('/api/scrittura/allena', { immagine: $('#lavagna').toDataURL('image/png'), lettera });
    scrivi(`"${lettera}": ${r.aggiunti} esempi salvati.`);
    indiceAllena += 1; pulisciLavagna(); aggiornaAllena(); statoScrittura();
  } catch (e) { scrivi(e.message, true); suono('errore'); }
});
$('#btn-salta-lettera').addEventListener('click', () => { indiceAllena += 1; pulisciLavagna(); aggiornaAllena(); });

// =========================================================================
// GITHUB
// =========================================================================
let ghFileAperto = null;

function rigaGh(titolo, sotto, url, ...pulsanti) {
  return el('div', { class: 'voce' },
    el('div', { class: 'titolo' }, el('span', {}, titolo), url ? el('a', { class: 'btn piccolo sec', href: url, target: '_blank', rel: 'noopener' }, 'Apri') : null),
    sotto ? el('div', { class: 'sotto' }, sotto) : null,
    pulsanti.length ? el('div', { class: 'azioni', style: 'margin:4px 0 0' }, ...pulsanti) : null);
}

async function caricaGitHub() {
  try {
    const d = await api('/api/github');
    $('#gh-collega').hidden = d.configurato;
    $('#gh-profilo-zona').hidden = !d.configurato;
    $('#gh-griglia').hidden = !d.configurato;
    if (!d.configurato) return;
    const p = d.profilo || {};
    $('#gh-profilo').textContent = `Collegato come ${p.utente || '?'} · ${p.repo_pubblici ?? '?'} repo pubblici, ${p.repo_privati ?? '?'} privati`
      + (d.errori ? ' · ' + d.errori.join(' ') : '');
    const vuoto = (t) => [el('p', { class: 'nota' }, t)];
    const notif = (d.notifiche || []).filter((n) => n.non_letta);
    $('#gh-notifiche').replaceChildren(...(notif.length ? notif.map((n) => rigaGh(n.titolo, `${n.repo} · ${n.tipo} · ${n.motivo}`)) : vuoto('Nessuna notifica non letta.')));
    $('#gh-pr').replaceChildren(...((d.pr || []).length ? d.pr.map((x) => rigaGh(`#${x.numero} ${x.titolo}`, `${x.repo} · ${x.autore}`, x.url,
      el('button', { class: 'btn piccolo sec', onclick: () => commentaGh(x) }, 'Commenta'),
      el('button', { class: 'btn piccolo pericolo', onclick: () => unisciGh(x) }, 'Unisci'))) : vuoto('Nessuna pull request aperta.')));
    $('#gh-issue').replaceChildren(...((d.issue || []).filter((x) => !x.pr).length ? d.issue.filter((x) => !x.pr).map((x) => rigaGh(`#${x.numero} ${x.titolo}`, `${x.repo} · ${x.autore}`, x.url,
      el('button', { class: 'btn piccolo sec', onclick: () => commentaGh(x) }, 'Commenta'),
      el('button', { class: 'btn piccolo sec', onclick: () => eseguiComando(`chiudi issue ${x.numero} di ${x.repo}`).then(caricaGitHub) }, 'Chiudi'))) : vuoto('Nessuna issue aperta.')));
    $('#gh-repo').replaceChildren(...((d.repository || []).map((r) => {
      const esito = el('span', { class: 'sotto' });
      return rigaGh(r.nome + (r.privato ? ' 🔒' : ''), r.descrizione || `★ ${r.stelle}`, r.url,
        el('button', {
          class: 'btn piccolo sec',
          onclick: async () => {
            esito.textContent = ' controllo...';
            try {
              const b = await api('/api/github/build', { repo: r.nome });
              const u = b[0];
              esito.textContent = u ? ` ultima build: ${u.esito || u.stato}` : ' nessuna build';
              esito.className = 'sotto ' + (u && u.esito === 'success' ? 'esito-ok' : u && u.esito === 'failure' ? 'esito-ko' : '');
            } catch (e) { esito.textContent = ' ' + e.message; }
          },
        }, 'Build'),
        el('button', { class: 'btn piccolo sec', onclick: () => { $('#gh-file-repo').value = r.nome; $('#gh-file-percorso').focus(); } }, 'File'),
        esito);
    })));
  } catch (e) { $('#gh-profilo').textContent = e.message; }
}

async function commentaGh(x) {
  const testo = prompt(`Commento per ${x.repo} #${x.numero}:`);
  if (testo === null) return;
  if (!testo.trim()) { scrivi(rimprovero('Commento vuoto. Bravo.', 'Commento vuoto.'), true); return; }
  await eseguiComando(`commenta la issue ${x.numero} di ${x.repo}: ${testo}`);
}

async function unisciGh(x) {
  if (!confirm(`Unire la pull request #${x.numero} "${x.titolo}" in ${x.repo}? Non si annulla facilmente.`)) return;
  try {
    const r = await api('/api/github/unisci', { repo: x.repo, numero: x.numero, conferma: true });
    scrivi(r.unita ? `Pull request #${x.numero} unita.` : `Non unita: ${r.messaggio}`, !r.unita);
    caricaGitHub();
  } catch (e) { scrivi(e.message, true); }
}

$('#form-gh-token').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const p = await api('/api/github/token', { token: $('#gh-token').value });
    $('#gh-token').value = '';
    scrivi(`GitHub collegato come ${p.utente}.`);
    caricaGitHub();
  } catch (err) { scrivi(err.message, true); suono('errore'); }
});
$('#btn-gh-aggiorna').addEventListener('click', caricaGitHub);
$('#btn-gh-lette').addEventListener('click', async () => {
  try { await api('/api/github/notifiche_lette', {}); scrivi('Notifiche segnate come lette.'); caricaGitHub(); } catch (e) { scrivi(e.message, true); }
});
$('#btn-gh-scollega').addEventListener('click', async () => {
  if (!confirm('Scollegare GitHub? Il token verrà cancellato dal server.')) return;
  await api('/api/github/scollega', {}); caricaGitHub();
});
$('#form-gh-file').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const r = await api('/api/github/file', { repo: $('#gh-file-repo').value, percorso: $('#gh-file-percorso').value });
    const area = $('#gh-file-testo');
    area.hidden = false;
    if (r.cartella) {
      area.value = r.voci.join('\n'); area.readOnly = true; $('#gh-file-azioni').hidden = true; ghFileAperto = null;
    } else {
      area.value = r.testo; area.readOnly = false; $('#gh-file-azioni').hidden = false;
      ghFileAperto = { repo: $('#gh-file-repo').value, percorso: $('#gh-file-percorso').value };
    }
  } catch (err) { scrivi(err.message, true); }
});
$('#btn-gh-salva').addEventListener('click', async () => {
  if (!ghFileAperto) return;
  if (!confirm(`Salvare le modifiche a ${ghFileAperto.percorso} con un commit su GitHub?`)) return;
  try {
    const r = await api('/api/github/salva_file', { ...ghFileAperto, testo: $('#gh-file-testo').value, messaggio: $('#gh-file-messaggio').value });
    scrivi(`Salvato su GitHub (commit ${r.commit}).`);
    $('#gh-file-messaggio').value = '';
  } catch (err) { scrivi(err.message, true); }
});
$('#form-gh-issue').addEventListener('submit', async (e) => {
  e.preventDefault();
  await eseguiComando(`crea issue su ${$('#gh-issue-repo').value}: ${$('#gh-issue-titolo').value}`);
  $('#gh-issue-titolo').value = '';
  caricaGitHub();
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
  $('#chk-ascolto').checked = pref.ascoltoSempre;
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
  if (pref.ascoltoSempre) impostaAscoltoSempre(true);
  setInterval(aggiornaMeteo, 15 * 60 * 1000);
}());
