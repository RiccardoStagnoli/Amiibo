/*
 * JARVIS - Servizio WhatsApp
 *
 * - Collega il tuo WhatsApp (come WhatsApp Web).
 * - Registra i messaggi in arrivo, tranne quelli delle chat ESCLUSE.
 * - Segreteria: risponde in automatico SOLO alle chat che scegli tu
 *   (o a tutte, o a nessuna: si decide dal pannello di Jarvis).
 * - Offre a Jarvis (server.py) le funzioni: elenco chat, lettura, risposta,
 *   inoltro, voto nei sondaggi, impostazioni.
 *
 * Ascolta SOLO su 127.0.0.1 (non raggiungibile da altri computer).
 *
 * ATTENZIONE: libreria NON ufficiale. Viola i termini di servizio di WhatsApp:
 * il numero puo' essere sospeso.
 */

const fs = require('fs');
const http = require('http');
const path = require('path');
const QRCode = require('qrcode');
const qrcodeTerminal = require('qrcode-terminal');
const { Client, LocalAuth } = require('whatsapp-web.js');

// ----------------------------- IMPOSTAZIONI -----------------------------
const PORTA = 3010;
const NOME = 'Riccardo';
const MESSAGGIO_ASSENZA =
  `${NOME} non è al momento raggiungibile, cosa volevi dirgli? ` +
  'Scrivi il tuo messaggio (anche più messaggi o vocali) e poi invia 1 per finire il messaggio.';
const MESSAGGIO_CHIAMATA =
  `Ciao, sono Jarvis, l'assistente di ${NOME}. ${NOME} non può rispondere alla chiamata. ` +
  'Cosa volevi dirgli? Scrivi il tuo messaggio e poi invia 1 per finire il messaggio.';
const MESSAGGIO_FINE = `Grazie, messaggio registrato. Lo riferirò a ${NOME} appena possibile.`;
const TASTO_FINE = '1';
const MINUTI_INATTIVITA = 15;
const ORE_SENZA_NUOVO_AVVISO = 3;
const MAX_MESSAGGI_IN_ARCHIVIO = 3000;
// ------------------------------------------------------------------------

const CARTELLA_DATI = path.join(__dirname, '..', 'dati');
const CARTELLA_VOCALI = path.join(CARTELLA_DATI, 'vocali');
const FILE_SEGRETERIA = path.join(CARTELLA_DATI, 'messaggi_whatsapp.json');
const FILE_ARCHIVIO = path.join(CARTELLA_DATI, 'whatsapp_archivio.json');
const FILE_IMPOSTAZIONI = path.join(CARTELLA_DATI, 'impostazioni_whatsapp.json');
fs.mkdirSync(CARTELLA_VOCALI, { recursive: true });

const ora = () => new Date().toISOString();
const log = (t) => console.log(`[${new Date().toLocaleString('it-IT')}] ${t}`);

function leggiJson(file, predefinito) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return predefinito;
  }
}

function scriviJson(file, dati) {
  const tmp = file + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(dati, null, 2), 'utf8');
  fs.renameSync(tmp, file);
}

// risposta_automatica: "scelte" (solo chat_risposta_auto), "tutti" (tutte le private), "nessuno"
let impostazioni = Object.assign(
  { escluse: [], risposta_automatica: 'scelte', chat_risposta_auto: [] },
  leggiJson(FILE_IMPOSTAZIONI, {}),
);
let segreteria = leggiJson(FILE_SEGRETERIA, []);
let archivio = leggiJson(FILE_ARCHIVIO, []);

const salvaSegreteria = () => scriviJson(FILE_SEGRETERIA, segreteria);
const salvaArchivio = () => {
  if (archivio.length > MAX_MESSAGGI_IN_ARCHIVIO) archivio = archivio.slice(-MAX_MESSAGGI_IN_ARCHIVIO);
  scriviJson(FILE_ARCHIVIO, archivio);
};

const eGruppo = (id) => id.endsWith('@g.us');
const eDaIgnorare = (id) =>
  id === 'status@broadcast' || id.endsWith('@broadcast') || id.endsWith('@newsletter');
const eEsclusa = (id) => impostazioni.escluse.includes(id);

function rispostaAutoAttiva(chatId) {
  if (eGruppo(chatId) || eEsclusa(chatId)) return false;
  if (impostazioni.risposta_automatica === 'tutti') return true;
  if (impostazioni.risposta_automatica === 'scelte') return impostazioni.chat_risposta_auto.includes(chatId);
  return false;
}

// ------------------------------- WHATSAPP -------------------------------
let qrAttuale = null;
let pronto = false;

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: path.join(__dirname, 'sessione') }),
  puppeteer: { headless: true, args: ['--no-sandbox'] },
});

client.on('qr', (qr) => {
  qrAttuale = qr;
  pronto = false;
  console.log('\nInquadra il QR (anche dal pannello di Jarvis, sezione Impostazioni):');
  console.log('WhatsApp > Impostazioni > Dispositivi collegati > Collega un dispositivo\n');
  qrcodeTerminal.generate(qr, { small: true });
});
client.on('ready', () => {
  qrAttuale = null;
  pronto = true;
  log('WhatsApp collegato. Servizio ATTIVO: lascia aperta questa finestra.');
});
client.on('auth_failure', (m) => log('Accesso non riuscito: ' + m));
client.on('disconnected', (m) => {
  log('WhatsApp disconnesso: ' + m);
  process.exit(1); // il file .bat lo riavvia
});

async function nomeDi(id) {
  try {
    const c = await client.getContactById(id);
    return c.name || c.pushname || c.number || id;
  } catch {
    return id;
  }
}

async function salvaVocale(msg) {
  try {
    const media = await msg.downloadMedia();
    if (media && media.data) {
      const nome = `${Date.now()}_${msg.id.id}.ogg`;
      fs.writeFileSync(path.join(CARTELLA_VOCALI, nome), Buffer.from(media.data, 'base64'));
      return nome;
    }
  } catch (e) {
    log('Vocale non scaricabile: ' + e.message);
  }
  return null;
}

const ETICHETTE = {
  image: 'Foto', video: 'Video', document: 'Documento', sticker: 'Sticker',
  location: 'Posizione', vcard: 'Contatto', ptt: 'Vocale', audio: 'Audio',
};

function descriviTesto(msg) {
  if (msg.type === 'chat') return msg.body;
  if (msg.type === 'poll_creation') return `[Sondaggio] ${msg.pollName || msg.body}`;
  const e = ETICHETTE[msg.type] || msg.type;
  return msg.body ? `[${e}] ${msg.body}` : `[${e}]`;
}

function sondaggioDi(msg) {
  if (msg.type !== 'poll_creation') return null;
  return {
    domanda: msg.pollName || msg.body,
    opzioni: (msg.pollOptions || []).map((o) => o.name),
    multipla: Boolean(msg.allowMultipleAnswers),
  };
}

// ---- Segreteria ----
const registrazioneAperta = (chatId) =>
  segreteria.find((r) => r.chat === chatId && r.stato === 'in corso');

function ultimoAvviso(chatId) {
  const l = segreteria.filter((r) => r.chat === chatId && r.avviso_inviato);
  return l.length ? new Date(l[l.length - 1].inizio) : null;
}

function chiudi(reg, motivo) {
  reg.stato = 'completato';
  reg.fine = ora();
  reg.chiuso_con = motivo;
  salvaSegreteria();
  log(`Segreteria: messaggio di ${reg.contatto} chiuso (${motivo}).`);
}

async function gestisciSegreteria(msg, nomeContatto, contenuto) {
  const testo = (msg.body || '').trim();
  let reg = registrazioneAperta(msg.from);

  if (reg && msg.type === 'chat' && testo === TASTO_FINE) {
    chiudi(reg, 'tasto 1');
    await client.sendMessage(msg.from, MESSAGGIO_FINE);
    return;
  }
  if (!reg) {
    const ultimo = ultimoAvviso(msg.from);
    const avvisa = !ultimo || Date.now() - ultimo.getTime() > ORE_SENZA_NUOVO_AVVISO * 3600e3;
    if (msg.type === 'chat' && testo === TASTO_FINE && !avvisa) return;
    reg = {
      id: `${Date.now()}_${msg.id.id}`,
      chat: msg.from,
      contatto: nomeContatto,
      inizio: ora(),
      ultimo_messaggio: ora(),
      fine: null,
      stato: 'in corso',
      chiuso_con: null,
      avviso_inviato: avvisa,
      origine: 'messaggio',
      contenuti: [],
    };
    segreteria.push(reg);
    if (avvisa) await client.sendMessage(msg.from, MESSAGGIO_ASSENZA);
  }
  reg.contenuti.push({ ora: ora(), contenuto });
  reg.ultimo_messaggio = ora();
  salvaSegreteria();
}

client.on('message', async (msg) => {
  try {
    if (msg.fromMe || eDaIgnorare(msg.from) || eEsclusa(msg.from)) return;

    const gruppo = eGruppo(msg.from);
    const nomeChat = gruppo ? (await msg.getChat()).name : await nomeDi(msg.from);
    const autore = gruppo ? await nomeDi(msg.author || msg.from) : nomeChat;

    let vocale = null;
    if (msg.hasMedia && (msg.type === 'ptt' || msg.type === 'audio')) vocale = await salvaVocale(msg);

    archivio.push({
      id: msg.id._serialized,
      chat: msg.from,
      chat_nome: nomeChat,
      gruppo,
      autore,
      ora: ora(),
      tipo: msg.type,
      testo: descriviTesto(msg),
      vocale,
      sondaggio: sondaggioDi(msg),
    });
    salvaArchivio();

    if (rispostaAutoAttiva(msg.from)) {
      const contenuto = vocale ? { vocale } : descriviTesto(msg);
      await gestisciSegreteria(msg, nomeChat, contenuto);
    }
  } catch (e) {
    log('Errore messaggio: ' + e.message);
  }
});

client.on('call', async (chiamata) => {
  try {
    if (chiamata.fromMe || chiamata.isGroup || !rispostaAutoAttiva(chiamata.from)) return;
    await chiamata.reject();
    if (!registrazioneAperta(chiamata.from)) {
      segreteria.push({
        id: `${Date.now()}_chiamata`,
        chat: chiamata.from,
        contatto: await nomeDi(chiamata.from),
        inizio: ora(),
        ultimo_messaggio: ora(),
        fine: null,
        stato: 'in corso',
        chiuso_con: null,
        avviso_inviato: true,
        origine: chiamata.isVideo ? 'videochiamata WhatsApp rifiutata' : 'chiamata WhatsApp rifiutata',
        contenuti: [],
      });
      salvaSegreteria();
    }
    await client.sendMessage(chiamata.from, MESSAGGIO_CHIAMATA);
    log('Chiamata WhatsApp rifiutata da ' + chiamata.from);
  } catch (e) {
    log('Errore chiamata: ' + e.message);
  }
});

setInterval(() => {
  const limite = Date.now() - MINUTI_INATTIVITA * 60e3;
  segreteria
    .filter((r) => r.stato === 'in corso' && new Date(r.ultimo_messaggio).getTime() < limite)
    .forEach((r) => chiudi(r, 'inattività'));
}, 60e3);

// --------------------------------- API ----------------------------------
function rispondi(res, codice, dati) {
  res.writeHead(codice, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(dati));
}

function corpo(req) {
  return new Promise((ok, ko) => {
    let d = '';
    req.on('data', (c) => {
      d += c;
      if (d.length > 1e6) req.destroy();
    });
    req.on('end', () => {
      try {
        ok(d ? JSON.parse(d) : {});
      } catch (e) {
        ko(e);
      }
    });
  });
}

async function serializzaMessaggio(m) {
  const salvato = archivio.find((a) => a.id === m.id._serialized);
  return {
    id: m.id._serialized,
    da_me: m.fromMe,
    autore: m.fromMe ? 'Tu' : salvato?.autore || (m.author ? await nomeDi(m.author) : null),
    ora: new Date(m.timestamp * 1000).toISOString(),
    tipo: m.type,
    testo: descriviTesto(m),
    vocale: salvato?.vocale || null,
    sondaggio: sondaggioDi(m),
  };
}

const rotte = {
  'GET /stato': async () => ({
    pronto,
    qr: qrAttuale ? await QRCode.toDataURL(qrAttuale) : null,
  }),

  'GET /impostazioni': async () => impostazioni,

  'POST /impostazioni': async (b) => {
    const modi = ['scelte', 'tutti', 'nessuno'];
    if (Array.isArray(b.escluse)) impostazioni.escluse = b.escluse.map(String);
    if (Array.isArray(b.chat_risposta_auto)) impostazioni.chat_risposta_auto = b.chat_risposta_auto.map(String);
    if (modi.includes(b.risposta_automatica)) impostazioni.risposta_automatica = b.risposta_automatica;
    scriviJson(FILE_IMPOSTAZIONI, impostazioni);
    return impostazioni;
  },

  'GET /chat': async (_b, q) => {
    const tutte = await client.getChats();
    const mostraEscluse = q.get('escluse') === '1';
    return tutte
      .filter((c) => !eDaIgnorare(c.id._serialized))
      .filter((c) => mostraEscluse || !eEsclusa(c.id._serialized))
      .slice(0, Number(q.get('n')) || 60)
      .map((c) => ({
        id: c.id._serialized,
        nome: c.name || c.id.user,
        gruppo: c.isGroup,
        non_letti: c.unreadCount,
        ultimo: c.lastMessage ? descriviTesto(c.lastMessage) : '',
        ora: c.timestamp ? new Date(c.timestamp * 1000).toISOString() : null,
        esclusa: eEsclusa(c.id._serialized),
        risposta_auto: rispostaAutoAttiva(c.id._serialized),
      }));
  },

  'GET /messaggi': async (_b, q) => {
    const id = q.get('chat');
    if (eEsclusa(id)) throw new Error('Chat esclusa');
    const chat = await client.getChatById(id);
    const lista = await chat.fetchMessages({ limit: Number(q.get('n')) || 40 });
    return Promise.all(lista.map(serializzaMessaggio));
  },

  'POST /invia': async (b) => {
    if (!b.chat || !b.testo) throw new Error('Servono chat e testo');
    const opzioni = b.cita ? { quotedMessageId: b.cita } : {};
    await client.sendMessage(b.chat, String(b.testo), opzioni);
    return { ok: true };
  },

  // Messaggio a se stessi (chat "Tu" di WhatsApp): usato per promemoria e riepilogo.
  'POST /invia_a_me': async (b) => {
    if (!b.testo) throw new Error('Testo mancante');
    await client.sendMessage(client.info.wid._serialized, String(b.testo));
    return { ok: true };
  },

  'POST /inoltra': async (b) => {
    const m = await client.getMessageById(b.messaggio);
    if (!m) throw new Error('Messaggio non trovato');
    for (const dest of b.destinazioni || []) await m.forward(dest);
    return { ok: true, inoltrati: (b.destinazioni || []).length };
  },

  'POST /vota': async (b) => {
    const m = await client.getMessageById(b.messaggio);
    if (!m || m.type !== 'poll_creation') throw new Error('Sondaggio non trovato');
    const valide = (m.pollOptions || []).map((o) => o.name);
    const scelte = (b.opzioni || []).filter((o) => valide.includes(o));
    if (!scelte.length) throw new Error('Nessuna opzione valida');
    await m.vote(scelte);
    return { ok: true, votate: scelte };
  },

  'POST /letta': async (b) => {
    await client.sendSeen(b.chat);
    return { ok: true };
  },
};

http
  .createServer(async (req, res) => {
    const url = new URL(req.url, 'http://localhost');
    const rotta = rotte[`${req.method} ${url.pathname}`];
    if (!rotta) return rispondi(res, 404, { errore: 'Funzione inesistente' });
    if (url.pathname !== '/stato' && !pronto)
      return rispondi(res, 503, { errore: 'WhatsApp non ancora collegato' });
    try {
      const b = req.method === 'POST' ? await corpo(req) : {};
      rispondi(res, 200, await rotta(b, url.searchParams));
    } catch (e) {
      rispondi(res, 400, { errore: String(e.message || e) });
    }
  })
  .listen(PORTA, '127.0.0.1', () => log(`API WhatsApp su http://127.0.0.1:${PORTA}`));

log('Avvio del servizio WhatsApp...');
client.initialize();
