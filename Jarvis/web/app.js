/* JARVIS - pannello web */
'use strict';

const $ = (s) => document.querySelector(s);

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
  const oggi = new Date().toDateString() === d.toDateString();
  return oggi ? d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleString('it-IT', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
};

// -------------------------------------------------------------------------
// PREFERENZE (salvate solo in questo browser)
// -------------------------------------------------------------------------
const PREF_BASE = { voce: '', tono: 0.35, velocita: 0.85, saggio: null, attiva: true };
let pref = { ...PREF_BASE };
try { pref = { ...PREF_BASE, ...JSON.parse(localStorage.getItem('jarvis_pref') || '{}') }; } catch { /* niente */ }
function salvaPref() { try { localStorage.setItem('jarvis_pref', JSON.stringify(pref)); } catch { /* niente */ } }

let profilo = { nome: 'Riccardo', stile_saggio: true, manuali: [] };
const saggio = () => (pref.saggio === null ? profilo.stile_saggio : pref.saggio);

// -------------------------------------------------------------------------
// FRASI (parlata normale / da saggio maestro)
// -------------------------------------------------------------------------
const F = {
  saluto: (n) => (saggio() ? `Bentornato, ${n}. Attivo, Jarvis ora è.` : `Bentornato, ${n}. Jarvis è attivo.`),
  segreteria: (k) => (k === 0
    ? (saggio() ? 'Messaggi in segreteria, nessuno tu hai.' : 'Nessun messaggio in segreteria.')
    : (saggio() ? `In segreteria, ${k} messaggi tu hai.` : `Hai ${k} messaggi in segreteria.`)),
  detto: (chi, t) => (saggio() ? `Da ${chi}, detto questo fu: ${t}` : `${chi} ha detto: ${t}`),
  chiamato: (chi) => (saggio() ? `Chiamato ti ha, ${chi}.` : `${chi} ti ha chiamato su WhatsApp.`),
  vocale: () => (saggio() ? 'un messaggio vocale lasciato ha' : 'un messaggio vocale'),
  nonLetti: (k) => (k === 0
    ? (saggio() ? 'Nuovi messaggi WhatsApp, nessuno ci sono.' : 'Nessun nuovo messaggio WhatsApp.')
    : (saggio() ? `Nuovi messaggi WhatsApp, in ${k} chat ci sono.` : `Hai nuovi messaggi WhatsApp in ${k} chat.`)),
  chat: (nome, k) => (saggio() ? `In ${nome}, ${k} nuovi messaggi ci sono.` : `${nome}: ${k} nuovi messaggi.`),
  email: (k) => (saggio() ? `Email non lette, ${k} tu hai.` : `Hai ${k} email non lette.`),
  inviato: () => (saggio() ? 'Inviato, il messaggio è.' : 'Messaggio inviato.'),
  inoltrato: (k) => (saggio() ? `Inoltrato a ${k} chat, il messaggio è.` : `Messaggio inoltrato a ${k} chat.`),
  votato: () => (saggio() ? 'Votato, hai.' : 'Voto inviato.'),
  manuale: () => (saggio() ? 'Nel manuale, scritto questo è.' : 'Ecco cosa dice il manuale.'),
  prova: () => (saggio() ? 'Pronto a servirti, io sono. Molto da imparare, tu ancora hai.' : 'Pronto a servirti.'),
  errore: (e) => (saggio() ? `Un problema c'è: ${e}` : `Errore: ${e}`),
};

// -------------------------------------------------------------------------
// VOCE (sintesi vocale del browser, gratuita)
// -------------------------------------------------------------------------
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
  if (!sintesi || !voci.length) { p.textContent = 'Voce: non disponibile'; p.className = 'pillola ko'; return; }
  p.textContent = pref.attiva ? 'Voce: attiva' : 'Voce: spenta';
  p.className = 'pillola ' + (pref.attiva ? 'ok' : '');
}

function parla(testo) {
  if (!testo) return;
  $('#parlato').textContent = testo;
  if (!sintesi || !pref.attiva) return;
  coda.push(testo);
  if (!parlaOra) prossimo();
}

function prossimo() {
  const testo = coda[0];
  if (testo === undefined) { parlaOra = false; $('#nucleo').classList.remove('parla'); return; }
  parlaOra = true;
  const u = new SpeechSynthesisUtterance(testo);
  const v = voci.find((x) => x.name === pref.voce);
  if (v) u.voice = v;
  u.lang = v ? v.lang : 'it-IT';
  u.pitch = Number(pref.tono);
  u.rate = Number(pref.velocita);
  let partito = false;
  u.onstart = () => {
    partito = true;
    $('#sblocca').hidden = true;
    $('#nucleo').classList.add('parla');
    $('#parlato').textContent = testo;
  };
  u.onend = u.onerror = () => { if (!partito) return; coda.shift(); prossimo(); };
  sintesi.speak(u);
  // Se il browser blocca la voce finche' non si tocca la pagina, chiedilo.
  setTimeout(() => { if (!partito) { sintesi.cancel(); $('#sblocca').hidden = false; } }, 2500);
}

$('#sblocca').addEventListener('click', () => { $('#sblocca').hidden = true; prossimo(); });
$('#btn-zitto').addEventListener('click', () => {
  coda.length = 0; if (sintesi) sintesi.cancel(); parlaOra = false; $('#nucleo').classList.remove('parla');
});

// -------------------------------------------------------------------------
// NAVIGAZIONE E OROLOGIO
// -------------------------------------------------------------------------
$('#menu').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-sezione]');
  if (!b) return;
  mostraSezione(b.dataset.sezione);
});

function mostraSezione(nome) {
  document.querySelectorAll('#menu button').forEach((x) => x.classList.toggle('attivo', x.dataset.sezione === nome));
  document.querySelectorAll('.sezione').forEach((s) => s.classList.toggle('visibile', s.id === nome));
  if (nome === 'whatsapp') caricaChat();
  if (nome === 'impostazioni') caricaImpostazioni();
}

setInterval(() => { $('#orologio').textContent = new Date().toLocaleTimeString('it-IT'); }, 1000);

// -------------------------------------------------------------------------
// SEGRETERIA
// -------------------------------------------------------------------------
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
      nuove.forEach((r) => { giaAnnunciati.add(r.id); parla(testoRegistrazione(r)); });
      await api('/api/segreteria/letti', { ids: nuove.map((r) => r.id) });
    }
    return nuove;
  } catch (e) {
    $('#lista-segreteria').replaceChildren(el('p', { class: 'errore' }, e.message));
    return [];
  }
}

function testoParlato(m) {
  if (m.sondaggio) return `un sondaggio: ${m.sondaggio.domanda}. Opzioni: ${m.sondaggio.opzioni.join(', ')}.`;
  if (m.vocale || m.tipo === 'ptt') return F.vocale();
  return m.testo;
}

// Rapporto completo: segreteria + WhatsApp non letti + Gmail.
async function rapporto() {
  parla(F.saluto(profilo.nome));
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
    const email = await api('/api/gmail/lista?q=is:unread');
    parla(F.email(email.length));
  } catch { /* Gmail non configurato */ }
}
$('#btn-rapporto').addEventListener('click', rapporto);

// -------------------------------------------------------------------------
// WHATSAPP
// -------------------------------------------------------------------------
let chatCache = [];
let chatAperta = null;
let citazione = null;
let impWa = { escluse: [], risposta_automatica: 'scelte', chat_risposta_auto: [] };

async function statoWa() {
  const p = $('#stato-wa');
  try {
    const s = await api('/api/wa/stato');
    p.textContent = s.pronto ? 'WhatsApp: collegato' : (s.qr ? 'WhatsApp: serve QR' : 'WhatsApp: avvio...');
    p.className = 'pillola ' + (s.pronto ? 'ok' : 'ko');
    return s;
  } catch {
    p.textContent = 'WhatsApp: spento'; p.className = 'pillola ko';
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
          if (!scelte.length) return;
          try { await api('/api/wa/vota', { messaggio: m.id, opzioni: scelte }); parla(F.votato()); } catch (e) { parla(F.errore(e.message)); }
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
  if (!testo || !chatAperta) return;
  try {
    await api('/api/wa/invia', { chat: chatAperta.id, testo, cita: citazione ? citazione.id : undefined });
    $('#testo-invio').value = '';
    citazione = null; $('#citazione').hidden = true;
    parla(F.inviato());
    setTimeout(caricaMessaggi, 800);
  } catch (err) { parla(F.errore(err.message)); }
});

// Dettatura (riconoscimento vocale del browser, se disponibile)
const Riconoscitore = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!Riconoscitore) $('#btn-detta').hidden = true;
$('#btn-detta').addEventListener('click', () => {
  const r = new Riconoscitore();
  r.lang = 'it-IT';
  r.onresult = (ev) => { $('#testo-invio').value = ev.results[0][0].transcript; };
  r.start();
});

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

// Inoltro
let daInoltrare = null;
function apriInoltro(m) {
  daInoltrare = m;
  $('#cerca-inoltra').value = '';
  disegnaInoltro();
  $('#dlg-inoltra').showModal();
}
function disegnaInoltro() {
  const f = $('#cerca-inoltra').value.toLowerCase();
  const selezionate = new Set([...document.querySelectorAll('#lista-inoltra input:checked')].map((i) => i.value));
  $('#lista-inoltra').replaceChildren(...chatCache.filter((c) => c.nome.toLowerCase().includes(f)).map((c) =>
    el('label', { class: 'interruttore' },
      el('input', { type: 'checkbox', value: c.id, checked: selezionate.has(c.id) }), el('span', {}, c.nome))));
}
$('#cerca-inoltra').addEventListener('input', disegnaInoltro);
$('#dlg-inoltra').addEventListener('close', async () => {
  if ($('#dlg-inoltra').returnValue !== 'ok' || !daInoltrare) return;
  const dest = [...document.querySelectorAll('#lista-inoltra input:checked')].map((i) => i.value);
  if (!dest.length) return;
  try {
    const r = await api('/api/wa/inoltra', { messaggio: daInoltrare.id, destinazioni: dest });
    parla(F.inoltrato(r.inoltrati));
  } catch (e) { parla(F.errore(e.message)); }
});

// -------------------------------------------------------------------------
// GMAIL
// -------------------------------------------------------------------------
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
    a.replaceChildren(
      el('h3', {}, m.oggetto),
      el('div', { class: 'sotto' }, `Da: ${m.mittente}\nData: ${m.data}`),
      el('div', { class: 'azioni' }, el('button', { class: 'btn piccolo', onclick: () => parla(`${m.oggetto}. ${m.corpo.slice(0, 1500)}`) }, 'Leggi ad alta voce')),
      el('div', {}, m.corpo));
    a.scrollIntoView({ behavior: 'smooth' });
  } catch (e) { a.replaceChildren(el('p', { class: 'errore' }, e.message)); }
}
document.querySelectorAll('[data-gmail]').forEach((b) => b.addEventListener('click', () => caricaGmail(b.dataset.gmail, false)));
$('#btn-cerca-gmail').addEventListener('click', () => caricaGmail($('#cerca-gmail').value, true));

// -------------------------------------------------------------------------
// MECCANICA
// -------------------------------------------------------------------------
$('#form-meccanica').addEventListener('submit', async (e) => {
  e.preventDefault();
  const domanda = $('#domanda').value.trim();
  if (!domanda) return;
  const box = $('#risposta-meccanica');
  box.replaceChildren(el('p', { class: 'nota' }, 'Consulto il manuale...'));
  try {
    const r = await api('/api/meccanica', { domanda });
    box.replaceChildren(el('div', {}, r.risposta),
      r.fonti.length ? el('h3', {}, 'Fonti') : null,
      ...r.fonti.map((f, i) => el('div', { class: 'sotto' }, `[${i + 1}] ${f.manuale} — ${f.sezione}`)));
    const senzaAI = r.risposta.startsWith('(Ollama');
    parla(F.manuale() + ' ' + (senzaAI ? r.risposta.split('\n').slice(2, 6).join(' ').slice(0, 600) : r.risposta));
  } catch (err) { box.replaceChildren(el('p', { class: 'errore' }, err.message)); }
});

// -------------------------------------------------------------------------
// IMPOSTAZIONI
// -------------------------------------------------------------------------
async function caricaImpostazioni() {
  const s = await statoWa();
  const zona = $('#qr-zona');
  if (!s) zona.replaceChildren('Servizio WhatsApp spento. Avvialo con avvia_server_jarvis.bat.');
  else if (s.pronto) zona.replaceChildren('WhatsApp collegato.');
  else if (s.qr) {
    zona.replaceChildren(
      el('p', {}, 'Sul telefono: WhatsApp → Dispositivi collegati → Collega un dispositivo, poi inquadra:'),
      el('img', { class: 'qr', src: s.qr, alt: 'Codice QR di collegamento WhatsApp' }));
  } else zona.replaceChildren('Avvio di WhatsApp in corso... riapri questa sezione tra qualche secondo.');

  if (!s || !s.pronto) return;
  try {
    const [imp, tutte] = await Promise.all([api('/api/wa/impostazioni'), api('/api/wa/chat?escluse=1&n=300')]);
    impWa = imp;
    const nomi = Object.fromEntries(tutte.map((c) => [c.id, c.nome]));
    document.querySelectorAll('input[name=modo]').forEach((r) => { r.checked = r.value === imp.risposta_automatica; });
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

document.querySelectorAll('input[name=modo]').forEach((r) => r.addEventListener('change', async () => {
  try { impWa = await api('/api/wa/impostazioni', { risposta_automatica: r.value }); } catch (e) { parla(F.errore(e.message)); }
}));

function preparaControlliVoce() {
  $('#tono').value = pref.tono;
  $('#velocita').value = pref.velocita;
  $('#chk-saggio').checked = saggio();
  $('#chk-voce').checked = pref.attiva;
  $('#sel-voce').addEventListener('change', (e) => { pref.voce = e.target.value; salvaPref(); });
  $('#tono').addEventListener('input', (e) => { pref.tono = e.target.value; salvaPref(); });
  $('#velocita').addEventListener('input', (e) => { pref.velocita = e.target.value; salvaPref(); });
  $('#chk-saggio').addEventListener('change', (e) => { pref.saggio = e.target.checked; salvaPref(); });
  $('#chk-voce').addEventListener('change', (e) => { pref.attiva = e.target.checked; salvaPref(); aggiornaStatoVoce(); });
  $('#btn-prova-voce').addEventListener('click', () => parla(F.prova()));
}

// -------------------------------------------------------------------------
// AVVIO
// -------------------------------------------------------------------------
(async function avvio() {
  try { profilo = await api('/api/profilo'); } catch { /* valori predefiniti */ }
  $('#nota-manuale').textContent = 'Fonte: ' + (profilo.manuali || []).join(', ') + ' (manuale del 1907).';
  preparaControlliVoce();
  if (sintesi) { caricaVoci(); sintesi.addEventListener('voiceschanged', caricaVoci); }
  statoWa();
  const attivazione = new URLSearchParams(location.search).get('attivazione') === '1';
  if (attivazione) {
    history.replaceState(null, '', '/');
    await rapporto();
  } else {
    aggiornaSegreteria(false);
  }
  // Controllo periodico: i nuovi messaggi in segreteria vengono annunciati subito.
  setInterval(() => { aggiornaSegreteria(true); statoWa(); }, 20000);
})();
