/*
 * JARVIS - Segreteria WhatsApp
 *
 * Collega il tuo WhatsApp (come WhatsApp Web) e, quando qualcuno ti scrive
 * in privato:
 *   1. risponde con il messaggio di assenza;
 *   2. registra tutto quello che la persona scrive (testi e vocali);
 *   3. quando la persona invia "1" chiude il messaggio e la ringrazia;
 *   4. salva tutto in ..\dati\messaggi_whatsapp.json, che Jarvis ti rilegge.
 * Se ti chiamano su WhatsApp, rifiuta la chiamata e invia lo stesso messaggio.
 *
 * ATTENZIONE: libreria NON ufficiale. Viola i termini di servizio di WhatsApp:
 * il numero puo' essere sospeso.
 */

const fs = require('fs');
const path = require('path');
const qrcode = require('qrcode-terminal');
const { Client, LocalAuth } = require('whatsapp-web.js');

// ----------------------------- IMPOSTAZIONI -----------------------------
const NOME = 'Riccardo';
const MESSAGGIO_ASSENZA =
  `${NOME} non è al momento raggiungibile, cosa volevi dirgli? ` +
  'Scrivi il tuo messaggio (anche più messaggi o vocali) e poi invia 1 per finire il messaggio.';
const MESSAGGIO_CHIAMATA =
  `Ciao, sono Jarvis, l'assistente di ${NOME}. ${NOME} non può rispondere alla chiamata. ` +
  'Cosa volevi dirgli? Scrivi il tuo messaggio e poi invia 1 per finire il messaggio.';
const MESSAGGIO_FINE = `Grazie, messaggio registrato. Lo riferirò a ${NOME} appena possibile.`;
const TASTO_FINE = '1';
// Dopo quanti minuti senza nuovi messaggi la registrazione si chiude da sola.
const MINUTI_INATTIVITA = 15;
// Dopo un messaggio registrato, per quante ore NON rimandare l'avviso alla stessa persona
// (i suoi messaggi vengono comunque registrati).
const ORE_SENZA_NUOVO_AVVISO = 3;
// Rifiutare le chiamate WhatsApp in arrivo?
const RIFIUTA_CHIAMATE = true;
// ------------------------------------------------------------------------

const CARTELLA_DATI = path.join(__dirname, '..', 'dati');
const CARTELLA_VOCALI = path.join(CARTELLA_DATI, 'vocali');
const FILE_MESSAGGI = path.join(CARTELLA_DATI, 'messaggi_whatsapp.json');
fs.mkdirSync(CARTELLA_VOCALI, { recursive: true });

function ora() {
  return new Date().toISOString();
}

function log(testo) {
  console.log(`[${new Date().toLocaleString('it-IT')}] ${testo}`);
}

function caricaMessaggi() {
  try {
    return JSON.parse(fs.readFileSync(FILE_MESSAGGI, 'utf8'));
  } catch {
    return [];
  }
}

let registro = caricaMessaggi();

function salva() {
  // Scrittura sicura: prima su file temporaneo, poi rinomina.
  const tmp = FILE_MESSAGGI + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(registro, null, 2), 'utf8');
  fs.renameSync(tmp, FILE_MESSAGGI);
}

function registrazioneAperta(chatId) {
  return registro.find((r) => r.chat === chatId && r.stato === 'in corso');
}

function ultimoAvviso(chatId) {
  const conAvviso = registro.filter((r) => r.chat === chatId && r.avviso_inviato);
  return conAvviso.length ? new Date(conAvviso[conAvviso.length - 1].inizio) : null;
}

function chiudi(reg, motivo) {
  reg.stato = 'completato';
  reg.fine = ora();
  reg.chiuso_con = motivo; // "tasto 1" oppure "inattività"
  salva();
  log(`Messaggio di ${reg.contatto} chiuso (${motivo}).`);
}

function eChatPrivata(chatId) {
  return !(
    chatId.endsWith('@g.us') ||
    chatId.endsWith('@broadcast') ||
    chatId.endsWith('@newsletter') ||
    chatId === 'status@broadcast'
  );
}

async function nomeContatto(msg) {
  try {
    const c = await msg.getContact();
    return c.name || c.pushname || c.number || msg.from;
  } catch {
    return msg.from;
  }
}

async function contenuto(msg) {
  if (msg.type === 'chat') return msg.body;
  if (msg.hasMedia && (msg.type === 'ptt' || msg.type === 'audio')) {
    try {
      const media = await msg.downloadMedia();
      if (media && media.data) {
        const nomeFile = `${Date.now()}_${msg.id.id}.ogg`;
        fs.writeFileSync(path.join(CARTELLA_VOCALI, nomeFile), Buffer.from(media.data, 'base64'));
        return { vocale: nomeFile };
      }
    } catch (e) {
      log('Impossibile scaricare il vocale: ' + e.message);
    }
    return '[Messaggio vocale non scaricabile]';
  }
  const tipi = {
    image: 'Foto', video: 'Video', document: 'Documento', sticker: 'Sticker',
    location: 'Posizione', vcard: 'Contatto',
  };
  const etichetta = tipi[msg.type] || `Contenuto (${msg.type})`;
  return msg.body ? `[${etichetta}] ${msg.body}` : `[${etichetta}]`;
}

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: path.join(__dirname, 'sessione') }),
  puppeteer: { headless: true, args: ['--no-sandbox'] },
});

client.on('qr', (qr) => {
  console.log('\nInquadra questo codice con il telefono:');
  console.log('WhatsApp > Impostazioni > Dispositivi collegati > Collega un dispositivo\n');
  qrcode.generate(qr, { small: true });
});

client.on('ready', () => log('Segreteria WhatsApp ATTIVA. Lascia aperta questa finestra.'));
client.on('auth_failure', (m) => log('Accesso non riuscito: ' + m));
client.on('disconnected', (m) => {
  log('WhatsApp disconnesso: ' + m + '. Riavvia la segreteria.');
  process.exit(1);
});

client.on('message', async (msg) => {
  try {
    if (msg.fromMe || !eChatPrivata(msg.from)) return;

    const testo = (msg.body || '').trim();
    let reg = registrazioneAperta(msg.from);

    if (reg && msg.type === 'chat' && testo === TASTO_FINE) {
      chiudi(reg, 'tasto 1');
      await client.sendMessage(msg.from, MESSAGGIO_FINE);
      return;
    }

    if (!reg) {
      const ultimo = ultimoAvviso(msg.from);
      const mandaAvviso =
        !ultimo || Date.now() - ultimo.getTime() > ORE_SENZA_NUOVO_AVVISO * 3600 * 1000;
      if (msg.type === 'chat' && testo === TASTO_FINE && !mandaAvviso) return; // "1" isolato
      reg = {
        id: `${Date.now()}_${msg.id.id}`,
        chat: msg.from,
        contatto: msg.from,
        inizio: ora(),
        ultimo_messaggio: ora(),
        fine: null,
        stato: 'in corso',
        chiuso_con: null,
        avviso_inviato: mandaAvviso,
        origine: 'messaggio',
        contenuti: [],
      };
      registro.push(reg); // subito, prima di ogni attesa, per non creare doppioni
      reg.contatto = await nomeContatto(msg);
      if (mandaAvviso) await client.sendMessage(msg.from, MESSAGGIO_ASSENZA);
      log(`Nuovo messaggio da ${reg.contatto}.`);
    }

    reg.contenuti.push({ ora: ora(), contenuto: await contenuto(msg) });
    reg.ultimo_messaggio = ora();
    salva();
  } catch (e) {
    log('Errore nella gestione del messaggio: ' + e.message);
  }
});

client.on('call', async (chiamata) => {
  if (!RIFIUTA_CHIAMATE || chiamata.fromMe || chiamata.isGroup) return;
  try {
    await chiamata.reject();
    let reg = registrazioneAperta(chiamata.from);
    if (!reg) {
      let contatto = chiamata.from;
      try {
        const c = await client.getContactById(chiamata.from);
        contatto = c.name || c.pushname || c.number || chiamata.from;
      } catch { /* nome non disponibile */ }
      reg = {
        id: `${Date.now()}_chiamata`,
        chat: chiamata.from,
        contatto,
        inizio: ora(),
        ultimo_messaggio: ora(),
        fine: null,
        stato: 'in corso',
        chiuso_con: null,
        avviso_inviato: true,
        origine: chiamata.isVideo ? 'videochiamata WhatsApp rifiutata' : 'chiamata WhatsApp rifiutata',
        contenuti: [],
      };
      registro.push(reg);
      salva();
    }
    await client.sendMessage(chiamata.from, MESSAGGIO_CHIAMATA);
    log(`Chiamata WhatsApp rifiutata da ${reg.contatto}.`);
  } catch (e) {
    log('Errore nella gestione della chiamata: ' + e.message);
  }
});

// Chiude le registrazioni ferme da troppo tempo.
setInterval(() => {
  const limite = Date.now() - MINUTI_INATTIVITA * 60 * 1000;
  registro
    .filter((r) => r.stato === 'in corso' && new Date(r.ultimo_messaggio).getTime() < limite)
    .forEach((r) => chiudi(r, 'inattività'));
}, 60 * 1000);

log('Avvio della segreteria WhatsApp...');
client.initialize();
