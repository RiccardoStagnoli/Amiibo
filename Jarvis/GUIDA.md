# JARVIS – Guida di installazione (Windows 11)

Jarvis gira su un **PC che fa da server** (sempre acceso). Funzioni:

1. **Pannello futuristico** nel browser (`http://localhost:8080`), che si apre dicendo **"Jarvis attivazione"** al microfono del PC.
2. **Voce** in stile "vecchio saggio maestro": tono basso, lento, frasi con verbo e soggetto invertiti ("Nuovi messaggi, tre tu hai").
3. **WhatsApp**: legge i messaggi (escluse le chat che scegli), risponde, inoltra, vota nei sondaggi. La **segreteria automatica** risponde solo alle chat che decidi tu.
4. **Gmail** in sola lettura.
5. **Meccanica**: risposte basate **solo** sul manuale nella cartella `manuali`.

Costo: zero. Python, Node.js, Vosk (riconoscimento vocale offline), Gmail API e, facoltativo, Ollama sono gratuiti.

Cartella del progetto: **`C:\Jarvis`**

```
C:\Jarvis\
 ├─ avvia_server_jarvis.bat   AVVIA TUTTO (WhatsApp + pannello + ascolto vocale)
 ├─ installa.bat              installa le librerie Python (una volta sola)
 ├─ installa_whatsapp.bat     installa il servizio WhatsApp (una volta sola)
 ├─ servizio_loop.bat         usato da avvia_server_jarvis.bat (non aprirlo)
 ├─ avvia_jarvis.bat          vecchia versione a menu testuale (facoltativa)
 ├─ config.py                 impostazioni (nome, porta, password, frase di attivazione)
 ├─ server.py                 pannello web
 ├─ ascolto.py                attivazione vocale "Jarvis attivazione"
 ├─ accedi_teams.bat          primo accesso a Teams (Fase 12)
 ├─ comandi.py, personalita.py, gmail_reader.py, gmail_pulizia.py, teams_reader.py,
 │  meccanica.py, whatsapp_reader.py, voce.py, jarvis.py
 ├─ msi\                       agente da copiare sul PC Msi (Fase 13)
 ├─ web\                      grafica del pannello
 ├─ whatsapp\                 servizio WhatsApp
 ├─ manuali\                  manuale di meccanica
 ├─ modelli\                  modello vocale italiano (scaricato da solo, ~50 MB)
 ├─ dati\                     messaggi, vocali, impostazioni (creata da sola)
 └─ credentials.json          lo scarichi tu da Google (Fase 3)
```

---

## Fase 1 – Installare Python

1. Apri <https://www.python.org/downloads/windows/> e scarica l'ultima versione di Python 3 per Windows (64-bit).
2. Avvia il file scaricato.
3. Se compare la casella **"Add python.exe to PATH"**, **spuntala**. Poi clicca **Install Now**.
   (Le schermate dell'installer possono cambiare tra una versione e l'altra: accetta le opzioni predefinite.)
4. Verifica: premi `Win + R`, scrivi `cmd`, premi Invio. Nella finestra nera scrivi:
   ```
   py --version
   ```
   Deve comparire `Python 3.x.x`. Se compare un errore, prova `python --version`. Se nessuno dei due funziona, reinstalla Python spuntando "Add python.exe to PATH".

## Fase 2 – Scaricare Jarvis

1. Vai sulla pagina GitHub del repository `riccardostagnoli/amiibo`.
2. In alto a sinistra, nel selettore dei branch, scegli **`claude/jarvis-gmail-reader-k8f67k`**.
3. Clicca il pulsante verde **Code** → **Download ZIP**.
4. Apri lo ZIP scaricato (cartella `Download`) → clic destro → **Estrai tutto**.
5. Dentro la cartella estratta trovi la cartella **`Jarvis`**. Copiala in `C:\` in modo da avere `C:\Jarvis\jarvis.py`.

Per vedere le estensioni dei file (serve nella Fase 3): in Esplora file → **Visualizza** → **Mostra** → spunta **Estensioni nomi file**.

## Fase 3 – Collegare l'account Google (Google Cloud, gratuito)

Jarvis chiede **accesso completo** a Gmail (leggere, archiviare, spam, cestino, eliminazione definitiva), Google Calendar e Google Drive. Non serve carta di credito.

1. Apri <https://console.cloud.google.com/> e accedi con **lo stesso account Gmail** che Jarvis deve leggere. Accetta i termini se richiesto.
2. **Crea il progetto**: in alto clicca il selettore dei progetti → **Nuovo progetto** → Nome: `Jarvis` → **Crea**. Assicurati che in alto sia selezionato il progetto `Jarvis`.
3. **Abilita le tre API** (apri ogni link e premi **Abilita**):
   - Gmail: <https://console.cloud.google.com/apis/library/gmail.googleapis.com>
   - Calendar: <https://console.cloud.google.com/apis/library/calendar-json.googleapis.com>
   - Drive: <https://console.cloud.google.com/apis/library/drive.googleapis.com>
4. **Configura la schermata di consenso**: apri <https://console.cloud.google.com/auth/overview> → **Inizia** (Get started):
   - Nome app: `Jarvis` – Email di assistenza: la tua → Avanti
   - Pubblico (Audience): **Esterno** (External) → Avanti
   - Dati di contatto: la tua email → Avanti
   - Accetta le norme → **Crea**
5. **Aggiungi te stesso come utente di test**: menu a sinistra **Pubblico** (Audience) → sezione **Utenti di test** → **Aggiungi utenti** → scrivi il tuo indirizzo Gmail → **Salva**.
6. **Crea la chiave per Jarvis**: menu a sinistra **Client** (Clients) → **Crea client**:
   - Tipo di applicazione: **App desktop** (Desktop app)
   - Nome: `Jarvis` → **Crea**
   - Nella finestra che compare clicca **Scarica JSON** (Download JSON).
7. Il file scaricato ha un nome tipo `client_secret_123...json`. **Rinominalo in `credentials.json`** e spostalo in `C:\Jarvis`.
   Controlla che non si chiami `credentials.json.json`.

> **Non condividere mai `credentials.json` e `token.json`.** Il file `.gitignore` impedisce che finiscano su GitHub.

## Fase 4 – Installare le librerie

Doppio clic su **`C:\Jarvis\installa.bat`**. Attendi il messaggio `Installazione completata.` e premi un tasto.

Se Windows mostra "Windows ha protetto il PC": **Ulteriori informazioni** → **Esegui comunque**.

## Fase 5 – Primo accesso a Gmail

1. Doppio clic su **`C:\Jarvis\avvia_jarvis.bat`** (menu testuale, serve solo per il primo accesso a Gmail).
2. Scegli `1` e premi Invio.
3. Si apre il browser:
   - scegli il tuo account Gmail;
   - compare "**Google non ha verificato questa app**": è normale, l'app è tua. Clicca **Continua** (oppure **Avanzate** → **Vai a Jarvis**);
   - spunta **tutti** i permessi richiesti (Gmail, Calendar, Drive) → **Continua**;
   - compare `The authentication flow has completed`: chiudi la scheda e torna alla finestra di Jarvis.
4. Jarvis mostra le email. Scrivi il numero di un'email per leggerla, Invio vuoto per tornare al menu.

Jarvis salva l'accesso in `C:\Jarvis\token.json`. **Se avevi già fatto l'accesso con la versione precedente**, Jarvis lo chiede di nuovo da solo perché i permessi sono cambiati. Con l'app in modalità "Test", Google fa scadere l'accesso dopo **7 giorni**: Jarvis riapre il browser da solo e ripeti il punto 3.

### Menu

| Tasto | Funzione |
|---|---|
| 1 | Email non lette (Posta in arrivo) |
| 2 | Ultime email (Posta in arrivo) |
| 3 | Ricerca in tutta la casella. Usa la stessa sintassi di Gmail: `from:amazon`, `subject:fattura`, `after:2026/11/01`, `has:attachment` |
| 4 | Domande di meccanica |
| 5 | Rileggi i messaggi WhatsApp di oggi |
| 0 | Esci |

Leggere un'email con Jarvis **non** la segna come letta.

## Fase 6 (opzionale) – Risposte discorsive con Ollama

Senza Ollama, alla domanda di meccanica Jarvis mostra i 4 passaggi del manuale più pertinenti, testuali.
Con Ollama, Jarvis scrive una risposta in italiano **usando solo quei passaggi** e indica le fonti `[1]`, `[2]`...

1. Scarica e installa Ollama da <https://ollama.com/download> (versione Windows).
2. Apri il Prompt dei comandi (`Win + R` → `cmd` → Invio) e scrivi:
   ```
   ollama pull gemma2:2b
   ```
   Scarica il modello (circa 1,6 GB). Va fatto una volta sola.
3. Ollama resta attivo in background (icona vicino all'orologio). Riavvia Jarvis.

Per usare un altro modello, modifica `MODELLO_OLLAMA` in `C:\Jarvis\config.py` con il Blocco note.
Requisiti hardware indicativi: almeno 8 GB di RAM. Su PC lenti la risposta può richiedere decine di secondi.

## Fase 7 – Servizio WhatsApp

> **Rischio da conoscere prima:** il servizio usa `whatsapp-web.js`, una libreria **non ufficiale** che collega il tuo WhatsApp come se fosse WhatsApp Web. È gratuita, ma **viola i termini di servizio di WhatsApp**: il tuo numero può essere **sospeso o bannato**. Usala a tuo rischio.

1. Installa **Node.js** (gratuito): <https://nodejs.org/> → versione **LTS** per Windows → opzioni predefinite.
2. Doppio clic su **`C:\Jarvis\installa_whatsapp.bat`** e attendi `Installazione completata.` (alcuni minuti).

## Fase 8 – Avviare Jarvis come server

1. Doppio clic su **`C:\Jarvis\installa.bat`** (di nuovo: aggiunge pannello e riconoscimento vocale).
2. Doppio clic su **`C:\Jarvis\avvia_server_jarvis.bat`**. Si aprono 3 finestre ridotte a icona: **WhatsApp**, **Pannello**, **Ascolto**. Non chiuderle: se un servizio si ferma, riparte da solo dopo 15 secondi.
   Al primo avvio la finestra "Ascolto" scarica il modello vocale italiano (~50 MB).
3. Apri **<http://localhost:8080>** → sezione **Impostazioni** → compare il **codice QR**. Sul telefono: WhatsApp → **Dispositivi collegati** → **Collega un dispositivo** → inquadralo. Va fatto una volta sola.
4. Se Windows chiede di consentire l'accesso alla rete a Python o Node.js, consenti solo le **reti private**.

### Attivazione vocale

- Di' chiaramente **"Jarvis attivazione"** vicino al microfono del PC: si apre il pannello a tutto schermo e Jarvis ti fa il **rapporto**:
  1. saluto;
  2. messaggi lasciati in segreteria, letti uno per uno;
  3. chat WhatsApp con messaggi non letti (fino a 5 chat, ultimi 5 messaggi ciascuna), escluse le chat escluse;
  4. numero di email non lette.
- Il riconoscimento avviene **sul PC, senza internet**: l'audio non viene inviato a nessuno.
- Per cambiare la frase: `FRASE_ATTIVAZIONE` in `config.py` (solo parole italiane comuni o "jarvis").
- Il pannello si apre con Microsoft Edge (o Chrome: `BROWSER = "chrome"` in `config.py`) in una finestra dedicata.
- Se il browser blocca la voce compare la scritta *"Tocca lo schermo per attivare la voce"*: cliccala una volta.
- Con il pannello aperto, i nuovi messaggi in segreteria vengono annunciati a voce appena arrivano (controllo ogni 20 secondi).

### La voce "da saggio maestro"

Jarvis parla con frasi invertite ("Inviato, il messaggio è") e con tono basso e lento. **Non** è la voce originale di Yoda: quella appartiene ai suoi doppiatori e a Lucasfilm e non è disponibile gratis né legalmente clonabile. È un effetto ottenuto con le voci italiane di Windows.

In **Impostazioni → Voce** puoi:
- scegliere la voce. Per l'effetto migliore usa una voce **non "Natural"** (es. Microsoft Elsa o Cosimo): le voci "Natural" ignorano il tono;
- regolare **tono** (più a sinistra = più profondo) e **velocità**;
- attivare o spegnere la parlata da saggio maestro;
- premere **Prova voce**.

Mancano voci italiane? Impostazioni di Windows → **Ora e lingua** → **Voce** → **Aggiungi voci** → Italiano.

### WhatsApp dal pannello

| Azione | Dove |
|---|---|
| Leggere una chat | Sezione WhatsApp → clic sulla chat |
| Rispondere | Scrivi in basso e premi **Invia**. Con **Rispondi** sotto un messaggio rispondi citandolo. **Mic** = dettatura (in Edge/Chrome, usa il servizio vocale online del browser) |
| Inoltrare | **Inoltra** sotto il messaggio → spunta le chat → **Inoltra** (funziona verso chat con cui hai già scritto) |
| Votare un sondaggio | Seleziona l'opzione sotto il sondaggio → **Vota** |
| Escludere una chat | Apri la chat → **Escludi chat**. Jarvis non la legge, non la annuncia e non le risponde. Per riammetterla: Impostazioni → Chat escluse → **Rimuovi** |
| Farsi ascoltare un messaggio | **Leggi** sotto il messaggio |

### Segreteria automatica (solo dove decidi tu)

In **Impostazioni → Segreteria automatica** scegli:
- **Solo le chat che scelgo io** (predefinito): attivala per una chat aprendola e spuntando **Risposta automatica**;
- **Tutte le chat private** (tranne le escluse);
- **Nessuna**.

Nelle chat con risposta automatica Jarvis scrive:
*"Riccardo non è al momento raggiungibile, cosa volevi dirgli? Scrivi il tuo messaggio (anche più messaggi o vocali) e poi invia 1 per finire il messaggio."*
Registra tutto fino al messaggio `1`, poi ringrazia. Senza `1`, chiude dopo 15 minuti di silenzio. Alla stessa persona l'avviso viene ripetuto al massimo ogni 3 ore. Le **chiamate WhatsApp** di quelle chat vengono rifiutate con un messaggio che invita a scrivere. I gruppi non ricevono mai risposte automatiche.
Testi e tempi: sezione `IMPOSTAZIONI` all'inizio di `C:\Jarvis\whatsapp\servizio_whatsapp.js`.

## Fase 9 – Il PC server

1. **Non far andare in sospensione il PC:** Impostazioni → **Sistema** → **Alimentazione** → *Schermo e sospensione* → sospensione **Mai** (lo schermo può spegnersi).
2. **Avvio automatico all'accensione:** `Win + R` → `shell:startup` → Invio. Nella cartella che si apre crea un collegamento a `C:\Jarvis\avvia_server_jarvis.bat` (clic destro sul file → *Mostra altre opzioni* → *Crea collegamento*, poi sposta il collegamento lì).
3. **Accesso automatico a Windows** (facoltativo, perché i programmi partono solo dopo il login): se il PC ha una password, l'avvio automatico funziona solo dopo che hai effettuato l'accesso.
4. **Usare il pannello dal telefono o da un altro PC della stessa rete Wi-Fi** (facoltativo):
   - in `config.py` imposta `HOST_PANNELLO = "0.0.0.0"` e una password lunga in `PASSWORD_PANNELLO` (senza password il server non parte);
   - scopri l'indirizzo del server: Prompt dei comandi → `ipconfig` → riga *Indirizzo IPv4* (es. `192.168.1.20`);
   - dal telefono apri `http://192.168.1.20:8080`.
   - **Non** aprire la porta 8080 sul router verso internet: il collegamento non è cifrato.
5. Il microfono per l'attivazione vocale deve essere collegato al **PC server**.

## Fase 10 – Chiamate normali al cellulare (Vodafone): NON automatizzabili gratis

Non esiste un servizio gratuito che risponda al tuo numero di cellulare, faccia ascoltare un messaggio, registri e si fermi premendo `1`.

- **Segreteria Vodafone:** puoi registrare tu il saluto (*"Riccardo non è al momento raggiungibile..."*) chiamando il **42020**. Però non ho trovato una funzione Vodafone che mandi i messaggi via email, quindi Jarvis **non** può leggerli. Le fonti consultate indicano anche un possibile costo di 1,50 €/giorno quando la segreteria viene usata, salvo offerte che la includono. Verifica al 190.
- **Alternativa che fa esattamente quello che vuoi (a pagamento):** inoltrare le chiamate senza risposta verso un numero Twilio che legge il messaggio, registra, si ferma con `1` e manda la registrazione a Jarvis. Ha un costo mensile più i minuti e per un numero italiano servono documenti d'identità.

## Fase 11 – Google: pulizia spam e spazio

Sezione **Google** del pannello:
- **Spazio account**: quanto occupano Gmail, Drive e Foto.
- **Analizza posta in arrivo**: Jarvis assegna a ogni email un punteggio da 0 a 100%.
  - **≥ 90%**: preselezionata (bordo rosso): pubblicità o spam quasi certi.
  - **60–89%**: mostrata ma **non** selezionata (dubbia).
  - sotto 60%: ignorata.
  - Non tocca **mai**: email con stella o importanti, mittenti a cui hai scritto almeno una volta, mittenti in `MITTENTI_PROTETTI` (`config.py`, es. `["scuola.it", "banca.it"]`).
  - Il punteggio è calcolato con regole (categoria Promozioni di Gmail, link di disiscrizione, mittenti noreply/newsletter, parole tipo "sconto", "-50%"). **Non è una probabilità misurata**: controlla la lista prima di confermare.
- Pulsanti: **Archivia** (toglie dalla posta in arrivo), **Segna come spam**, **Sposta nel cestino**.
- **Email pesanti**: email oltre 5 MB e più vecchie di un anno (di solito allegati), per liberare spazio.
- **Svuota cestino Gmail**: elimina **definitivamente** tutto il cestino. Irreversibile; Jarvis chiede conferma. Senza svuotarlo, Gmail lo svuota da solo dopo 30 giorni.

Comandi utili nella barra: `pulisci la posta`, `spazio account`, `agenda`, `aggiungi al calendario: dentista domani alle 15` (data e ora le interpreta Google: verifica sempre l'evento creato), `cerca su drive verifica di storia`.

## Fase 12 – Teams (messaggi dei professori)

Jarvis usa Microsoft Graph (gratuito) con il **tuo** account della scuola. Limiti reali, da sapere prima:
- Molte scuole **impediscono** agli studenti di autorizzare app esterne. Se al punto 5 compare "Approvazione dell'amministratore necessaria", Teams via Jarvis non è possibile senza il permesso della scuola: usa l'alternativa in fondo.
- Jarvis legge sicuramente solo le **chat** (private e di gruppo). I **post nei canali** dei corsi richiedono un permesso che solo l'amministratore della scuola può concedere (`TEAMS_LEGGI_CANALI`, lasciato a `False`).

1. Vai su <https://entra.microsoft.com> (o <https://portal.azure.com>) e accedi con un account Microsoft **personale** (es. Outlook/Hotmail). Se ti chiede di creare una directory o un abbonamento gratuito, segui la procedura. *Dati insufficienti per verificare se per tutti gli account è richiesta una carta: alcuni utenti la vedono chiesta per l'abbonamento Azure gratuito.*
2. **Registrazioni app** (App registrations) → **Nuova registrazione**:
   - Nome: `Jarvis`
   - Tipi di account supportati: **Account in qualsiasi directory organizzativa e account Microsoft personali** (multi-tenant)
   - URI di reindirizzamento: lascia vuoto → **Registra**.
3. Copia l'**ID applicazione (client)** e incollalo in `config.py` → `TEAMS_CLIENT_ID = "..."`.
4. Menu **Autenticazione** → in fondo **Consenti flussi client pubblici** → **Sì** → **Salva**.
5. In `config.py`, in `TEAMS_PROFESSORI` scrivi i cognomi dei prof, es. `["Rossi", "Bianchi"]` (lista vuota = tutti i messaggi).
6. Doppio clic su **`C:\Jarvis\accedi_teams.bat`**: compare un codice. Apri <https://microsoft.com/devicelogin>, inserisci il codice, accedi con l'**account della scuola** e accetta.
7. Riavvia `avvia_server_jarvis.bat`. Da ora i nuovi messaggi dei prof vengono letti nel **rapporto** all'attivazione e nella sezione **Teams**.

**Alternativa se la scuola blocca l'accesso:** in Teams → Impostazioni → Notifiche, attiva le **notifiche via email** per i messaggi persi. Se l'email della scuola è inoltrabile, inoltra quelle notifiche al tuo Gmail: Jarvis le leggerà come email (comando `leggi la posta`).

## Fase 13 – Controllo del PC "Msi"

Sul PC Msi gira un piccolo **agente** che si collega al server e riceve i comandi. Sul PC Msi non serve aprire porte.

**Sul PC server:**
1. Inventa un token lungo e casuale (almeno 30 caratteri, lettere e numeri) e scrivilo in `config.py` → `TOKEN_AGENTE_MSI = "..."`.
2. Imposta `HOST_PANNELLO = "0.0.0.0"` e una `PASSWORD_PANNELLO` di almeno 12 caratteri (il PC Msi deve raggiungere il server in rete).
3. Prendi nota dell'indirizzo IP del server: Prompt dei comandi → `ipconfig` → *Indirizzo IPv4* (es. `192.168.1.20`).
   Consiglio: nel router assegna al server un **IP fisso** (DHCP statico), altrimenti l'indirizzo può cambiare.
4. Riavvia `avvia_server_jarvis.bat`.

**Sul PC Msi:**
1. Installa Python (Fase 1) anche sul Msi.
2. Copia la cartella `C:\Jarvis\msi` del server sul Msi, ad esempio in `C:\JarvisMsi`.
3. Apri `C:\JarvisMsi\msi_agente.py` con il Blocco note e modifica:
   - `SERVER = "http://192.168.1.20:8080"` (l'IP del server)
   - `TOKEN = "..."` (lo stesso token del server)
   - `COMANDI_LIBERI = False` (lascia così: con `True` Jarvis può eseguire qualsiasi comando del Prompt sul Msi; pericoloso se qualcuno entra nel pannello).
4. Doppio clic su `installa_msi.bat`, poi su `avvia_msi.bat`. Se Windows chiede l'accesso alla rete, consenti le reti private.
5. Avvio automatico: `Win + R` → `shell:startup` → crea un collegamento ad `avvia_msi.bat`.

Nel pannello, il widget **Msi** diventa **ONLINE**. Comandi (barra in alto, oppure a voce):

| Esempio | Cosa fa sul Msi |
|---|---|
| `apri chrome e cerca youtube` | Chrome con la ricerca Google "youtube" |
| `cerca su youtube musica lofi` | Ricerca su YouTube |
| `apri youtube.com` | Apre il sito |
| `apri steam e scarica Portal 2` | Cerca il gioco su Steam e apre la finestra di installazione (va confermata in Steam; i giochi non posseduti vanno prima comprati) |
| `apri discord` / `apri spotify` / `apri <qualsiasi programma del menu Start>` | Apre il programma |
| `screenshot msi` | Mostra nel pannello lo schermo del Msi |
| `blocca msi` / `spegni msi` / `riavvia msi` / `annulla spegnimento` | Spegnimento e riavvio con 60 secondi di preavviso |

Regola del 90%: se il nome del programma o del gioco non corrisponde almeno al 90%, Jarvis **non** apre nulla e propone i nomi simili.

## Fase 14 – Usare Jarvis da qualsiasi dispositivo (anche fuori casa) e Rabbit R1

**In casa (stessa rete Wi-Fi):** Fase 9, punto 4 (`HOST_PANNELLO = "0.0.0.0"` + password), poi apri `http://IP-DEL-SERVER:8080` dal telefono.

**Fuori casa – Tailscale (gratuito per uso personale):** crea una rete privata tra i tuoi dispositivi, senza aprire porte sul router.
1. Crea un account su <https://tailscale.com> e installa Tailscale sul **server**, sul **telefono** e (se vuoi) sul **Msi**, accedendo sempre con lo stesso account.
2. In `config.py` del server: `ACCESSO_REMOTO = True` e `PASSWORD_PANNELLO` di almeno 12 caratteri.
3. Nell'app Tailscale del server leggi l'indirizzo `100.x.y.z`. Dal telefono, con Tailscale attivo, apri `http://100.x.y.z:8080`.
4. Sul telefono: menu del browser → **Aggiungi a schermata Home**: Jarvis si apre come un'app.

**Rabbit R1:** sul R1 non si può installare Tailscale, quindi serve un indirizzo pubblico HTTPS:
1. Sul server, nel Prompt dei comandi: `tailscale funnel --bg 8080`. La prima volta Tailscale può mostrare un link per abilitare HTTPS/Funnel nel pannello di amministrazione: aprilo e conferma, poi ripeti il comando. Tailscale mostra un indirizzo tipo `https://nome-pc.tuo-nome.ts.net`. Con `ACCESSO_REMOTO = True` e la password, chi apre quell'indirizzo deve fare l'accesso. Dopo 5 password sbagliate l'IP viene bloccato per 10 minuti.
2. Indirizzo da usare sul R1: `https://nome-pc.tuo-nome.ts.net/?modo=r1` (layout compatto: nucleo, stato, microfono).
3. Come aprire una pagina web sul R1: *dati insufficienti per verificare la procedura attuale.* Il R1 supporta le "creations" (app web caricate tramite codice QR dal portale rabbithole); se il tuo R1 lo permette, crea una creation con l'indirizzo del punto 2. Il layout compatto è stato provato a 240×282 e 360×480 pixel.
4. Per spegnere l'accesso pubblico: `tailscale funnel reset`.

## Fase 15 – Personalità e regole di Jarvis

- **Serio e diretto**: niente saluti di cortesia né complimenti.
- **Regola del 90%** (`SOGLIA_CERTEZZA` in `config.py`):
  - meccanica: risponde solo se il manuale contiene almeno il 90% dei termini della domanda, altrimenti dice *"Dati insufficienti per verificare"*;
  - WhatsApp, programmi, giochi: agisce solo se il nome corrisponde almeno al 90%;
  - pulizia Gmail: preseleziona solo punteggi ≥ 90%.
- **Insulti** (`INSULTI_ATTIVI`): solo quando sbagli tu (comando vuoto o incompleto, chat inesistente, password errata, messaggio vuoto, nessuna opzione selezionata). Mai per errori di Jarvis (servizio spento, rete, ecc.). Per disattivarli: `INSULTI_ATTIVI = False`.
- **Comandi a voce dal PC server**: dopo "Jarvis attivazione" hai 7 secondi per dire il comando. Il modello vocale leggero sbaglia spesso le parole straniere (Chrome, YouTube, Steam). Se capita, in `config.py` imposta `MODELLO_VOSK = "vosk-model-it-0.22"` (più preciso, 1,3 GB da scaricare, usa molta più RAM). Il pulsante **Mic** del pannello usa invece il riconoscimento vocale del browser (online), che di solito è più preciso.
- **Aspetto** (Impostazioni → Aspetto): 4 temi colore, effetti sonori, particelle animate, sequenza di avvio. Pulsante ⛶ in alto per lo schermo intero.

## Fase 16 – Funzioni extra

| Comando | Cosa fa |
|---|---|
| `ricordami tra 20 minuti di studiare storia` | Promemoria. Accetta anche `fra`, `tra un'ora`, `tra mezz'ora`, `alle 18:30 di ...`, `domani alle 8 di ...` |
| `promemoria` / `cancella promemoria` | Elenca o cancella i promemoria |
| `annota comprare olio motore` / `leggi le note` / `cancella le note` | Note veloci |
| `non disturbare per 2 ore` / `fine non disturbare` | La segreteria risponde a **tutte** le chat private per il tempo indicato, poi torna da sola come prima |
| `riepilogo` | Data, meteo, agenda, email non lette, WhatsApp, segreteria, Teams, promemoria di oggi |
| `accendi msi` | Accende il PC Msi tramite la rete (vedi sotto) |
| `modalita gioco`, `modalita studio`, `buonanotte` | **Macro**: più comandi con una frase. Le modifichi in `config.py` → `MACRO` |

- I **promemoria** vengono detti a voce dal pannello aperto e arrivano anche come **messaggio WhatsApp a te stesso** (la chat "Tu" / "Messaggi a te stesso"), quindi li ricevi anche fuori casa. Per disattivarlo: `PROMEMORIA_SU_WHATSAPP = False`.
- Il **riepilogo automatico** arriva ogni giorno all'ora `ORA_RIEPILOGO` (predefinita `"07:00"`), a voce e su WhatsApp. `""` lo disattiva.
- Il **registro attività** (Impostazioni) mostra i comandi eseguiti, gli accessi al pannello e le **password sbagliate** con l'indirizzo IP: se vedi accessi che non riconosci, cambia subito `PASSWORD_PANNELLO`.

**Accendere il Msi dalla rete (Wake-on-LAN).** Funziona di solito solo se il Msi è collegato al router **via cavo**; via Wi-Fi quasi mai.
1. Sul Msi: Prompt dei comandi → `ipconfig /all` → nella scheda **Ethernet** copia l'**Indirizzo fisico** (es. `1C-2B-3D-4E-5F-60`) in `config.py` del server → `MAC_MSI`.
2. Sul Msi: Gestione dispositivi → Schede di rete → la scheda Ethernet → Proprietà:
   - scheda **Risparmio energia**: spunta "Consenti al dispositivo di riattivare il computer";
   - scheda **Avanzate**: imposta "Wake on Magic Packet" su **Abilitato**.
3. Nel BIOS del Msi attiva la riattivazione da rete. Il nome dell'opzione cambia da scheda madre a scheda madre (es. "Wake On LAN", "Resume by PCI-E Device"): *dati insufficienti per indicarti il nome esatto sul tuo modello.*
4. Se non si accende da spento, disattiva l'**Avvio rapido** di Windows: Pannello di controllo → Opzioni risparmio energia → Specifica comportamento pulsanti di alimentazione → togli "Attiva avvio rapido".

## Fase 17 – Jarvis impara da te (sezione Memoria)

Jarvis non "riaddestra" un'intelligenza artificiale: **salva** le informazioni che gli dai (sul server, cartella `C:\Jarvis\dati`) e le **usa** per rispondere, sempre con la regola del 90%. Più gli insegni, più risponde.

**1. Fatti** – barra comandi, a voce o sezione Memoria:
- `ricorda che la mia moto è una Honda CB500 del 2019` → poi `qual è la mia moto?` risponde *"Dalla memoria: ..."*.
- `impara: il prof di matematica si chiama Rossi` · `cosa sai del prof di matematica` · `cosa hai imparato` · `dimentica moto`.
- Le domande **personali** (con *mio, mia, me, io, ho, sono*) cercano **solo** nella memoria, mai nei manuali: Jarvis non risponde "la tua moto" leggendo il libro del 1907.

**2. Documenti** – sezione Memoria → **Carica**: PDF, Word (.docx), .txt, .md, fino a 25 MB.
- Esempi: libretto d'uso e manutenzione della tua moto o auto, appunti, programma delle verifiche.
- Da quel momento le domande (che finiscono con `?`, oppure `domanda: ...`) cercano anche lì e citano la fonte (nome del file e pagina).
- I PDF fatti di **sole immagini** (scansioni) non contengono testo leggibile: Jarvis lo segnala.

**3. Comandi nuovi** – `quando dico buongiorno mamma intendi scrivi a Mamma: buongiorno!`
- Da allora basta dire "buongiorno mamma".
- Jarvis accetta solo comandi che esistono davvero; se sbagli, te lo dice a modo suo.
- Per cancellarlo: `dimentica il comando buongiorno mamma`, oppure **Elimina** nel pannello.

**4. Comandi non capiti** – ogni frase che Jarvis non capisce finisce nella lista *"Comandi e domande che non ho capito"*. Premi **Insegna** e scrivi a quale comando corrisponde. Così Jarvis si adatta al tuo modo di parlare.

Per fare una copia di sicurezza di tutto ciò che Jarvis ha imparato, copia la cartella `C:\Jarvis\dati` su una chiavetta o su Google Drive.

## Fase 18 – Voce di Jarvis e risposte a voce o per iscritto

**Voce.** Jarvis usa **Piper**, una sintesi vocale neurale open source presa da GitHub (`github.com/OHF-Voice/piper1-gpl`). Funziona offline sul PC server e manda l'audio al browser, quindi hai **la stessa voce su PC, telefono e Rabbit R1**.
- Al primo utilizzo il server scarica la voce (28 MB) nella cartella `C:\Jarvis\modelli\voci`.
- In `config.py`:
  - `VOCE_PIPER` = voce: `it_IT-riccardo-x_low` (maschile, predefinita), `it_IT-paola-medium`, `it_IT-serena-medium`, `it_IT-serena-high` (femminili, qualità migliore);
  - `EFFETTO_VOCE = "jarvis"` aggiunge un leggero effetto metallico da assistente (`"nessuno"` per voce pulita);
  - `VELOCITA_PIPER`: 1.0 normale, 1.15 più lenta.
- Pannello → Impostazioni → Voce → **Motore**: "Voce di Jarvis" oppure "Voce del browser" (quella di prima, con tono regolabile).
- **Non è la voce del Jarvis dei film.** Quella è la voce dell'attore Paul Bettany: copiarla con un modello "clonato" significa imitare una persona reale senza il suo consenso, quindi non l'ho usata.

**Risposte.**
- Domande **a voce** (pulsante **Mic**, oppure "Jarvis attivazione" + comando sul PC server) → risposta **a voce** (e anche scritta).
- Domande **scritte** (barra comandi, moduli) → risposta **solo scritta**, senza parlare. Se non sei nella sezione Centrale, compare in una notifica.
- Rapporto, promemoria, riepilogo e pulsanti **Leggi** usano sempre la voce.

## Fase 19 – Foto e video

Sezione **Media** del pannello:
1. Scrivi una **descrizione** (almeno due parole, es. "targa della moto", "lavagna di fisica 26/11").
2. Poi scegli come aggiungere:
   - **Scegli file**: foto (jpg, png, webp, gif, heic, max 25 MB) o video (mp4, webm, mov, max 200 MB);
   - **Scatta foto (telefono)** / **Registra video (telefono)**: apre direttamente la fotocamera del telefono;
   - **Fotocamera / webcam**: anteprima live con **Scatta** e **Registra video** (sul PC con webcam e sul telefono). Funziona solo da `localhost` o da un indirizzo **https** (es. Tailscale, Fase 20); da un indirizzo `http://192.168...` il browser la blocca, ma i due pulsanti "(telefono)" funzionano lo stesso.
3. Nella **Galleria** ogni file ha i pulsanti **WhatsApp** (invia a una chat; oltre 16 MB viene mandato come documento), **Scarica**, **Elimina**.
4. Comandi: `mostrami la foto della targa` (cerca nelle descrizioni con la regola del 90%), `mostra la galleria`.

I file restano sul PC server in `C:\Jarvis\dati\media`.

## Fase 20 – App sul telefono

Jarvis si installa sul telefono come un'**app** (icona nella schermata Home, apertura a schermo intero). Non è un file .apk: è un'app web installabile, ed è il modo gratuito per averla sia su Android sia su iPhone. **Funziona solo se il PC server è acceso**, perché tutte le funzioni girano lì.

**Metodo consigliato (funziona anche fuori casa, con https):**
1. Installa **Tailscale** sul server e sul telefono, con lo stesso account (Fase 14).
2. Sul server, nel Prompt dei comandi: `tailscale serve --bg 8080`. La prima volta può chiederti di abilitare HTTPS nel pannello di Tailscale: apri il link e conferma. Tailscale mostra un indirizzo tipo `https://nome-pc.tuo-nome.ts.net`, visibile **solo** dai tuoi dispositivi.
3. In `config.py`:
   - `ACCESSO_REMOTO = True`;
   - `PASSWORD_PANNELLO` di almeno 12 caratteri;
   - `INDIRIZZO_TELEFONO = "https://nome-pc.tuo-nome.ts.net"`.
   Poi riavvia `avvia_server_jarvis.bat`.
4. Sul PC: pannello → **Impostazioni → App per telefono** → compare un **codice QR**. Inquadralo con la fotocamera del telefono.
5. Installa:
   - **Android (Chrome):** menu **⋮** → **Installa app** (oppure "Aggiungi a schermata Home"). Se compare il pulsante **Installa Jarvis su questo dispositivo** nelle Impostazioni, puoi usare quello.
   - **iPhone (Safari):** pulsante **Condividi** → **Aggiungi alla schermata Home**.
6. Apri l'app dall'icona **Jarvis** e fai l'accesso con la password.

**Solo in casa (senza Tailscale):** `HOST_PANNELLO = "0.0.0.0"` + password. Nel QR compare `http://IP-DEL-SERVER:8080`. Su Android diventa un collegamento nella Home invece di un'app completa (serve https per l'installazione vera), e la webcam live non funziona; tutto il resto sì.

Con il server spento, l'app mostra *"Server non raggiungibile"* con il pulsante **Riprova**.

## Fase 21 – Controllo completo di Chrome (PC Msi)

Jarvis controlla Chrome sul Msi: apre e chiude schede, naviga, legge le pagine, clicca pulsanti e link, scrive nei campi, scorre, mette in pausa i video e mostra lo schermo di Chrome.

**Come funziona.** Usa il Chrome DevTools Protocol, lo stesso degli strumenti di automazione. Da Chrome 136 Google **non permette** questo controllo sul profilo normale di Chrome. Jarvis apre quindi il **"Chrome di Jarvis"**, un profilo separato (cartella `C:\JarvisMsi\chrome_jarvis`).

**Preparazione (una volta):**
1. Sul Msi esegui di nuovo `installa_msi.bat` (aggiunge la libreria `websocket-client`).
2. Riavvia `avvia_msi.bat`.
3. Dal pannello o a voce: `apri chrome`. Si apre una finestra di Chrome nuova.
4. In quella finestra accedi con il tuo **account Google** e attiva la **sincronizzazione**: arrivano segnalibri, password salvate, cronologia ed estensioni. Da quel momento Jarvis lavora con i tuoi siti già loggati.
5. Usa quella finestra come Chrome principale sul Msi (puoi fissarla sulla barra delle applicazioni).

**Comandi** (barra in alto, Mic, o pulsanti nella sezione Msi):

| Comando | Cosa fa |
|---|---|
| `apri chrome` | Apre il Chrome di Jarvis |
| `apri chrome e cerca ...` / `cerca su google ...` / `cerca su youtube ...` | Ricerca in una nuova scheda |
| `nuova scheda youtube.com` / `apri youtube.com` | Apre un sito |
| `schede` | Elenca le schede aperte |
| `passa alla scheda gmail` / `chiudi scheda` / `chiudi la scheda youtube` / `chiudi tutte le schede` | Gestione schede |
| `indietro` / `avanti` / `ricarica la pagina` | Navigazione |
| `scorri giù` / `scorri su` / `vai in fondo` / `vai in cima` | Scorrimento |
| `leggi la pagina` | Ti legge il testo della pagina (a voce se l'hai chiesto a voce) |
| `clicca su iscriviti` | Clicca il pulsante o link con quel testo |
| `digita motori a scoppio e premi invio` / `premi invio` | Scrive nel campo selezionato (o nel primo campo di testo) |
| `pausa` / `riproduci` / `muto` / `a schermo intero` | Video (YouTube e simili) |
| `screenshot chrome` | Mostra nel pannello cosa c'è nella scheda |

**Regola del 90%:** se nessun pulsante o scheda corrisponde almeno al 90% a quello che hai detto, Jarvis non clicca nulla e ti elenca i nomi simili.

**Sicurezza:**
- La porta di controllo di Chrome (9222) è aperta solo sul PC Msi stesso (127.0.0.1), non in rete.
- Qualsiasi programma installato sul Msi però potrebbe usarla mentre il Chrome di Jarvis è aperto: non installare programmi di dubbia provenienza.
- Per disattivare il controllo: `CHROME_CONTROLLO = False` in `msi_agente.py`.

## Fase 22 – GitHub

Jarvis usa l'API ufficiale di GitHub con un **token personale** che crei tu. Il token vale come una password: resta solo sul PC server (`C:\Jarvis\dati\.github_token`) e il pannello non lo mostra mai.

**Creare il token (una volta):**
1. Su github.com: foto profilo in alto a destra → **Settings** → in fondo **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. Token name: `Jarvis`. Expiration: a scelta (es. 1 anno; alla scadenza ne crei uno nuovo).
3. Repository access: **All repositories**.
4. Permissions → Repository permissions, imposta **Read and write** su: **Contents**, **Issues**, **Pull requests**; **Read-only** su: **Actions**, **Metadata**.
5. **Generate token** e copialo subito (inizia con `github_pat_`): GitHub non lo mostra più.
6. Pannello Jarvis → sezione **GitHub** → incolla il token → **Collega**. Se il token è sbagliato, Jarvis non lo salva.
7. Per creare repository e leggere le notifiche: le notifiche richiedono un token "classic". *Dati insufficienti per verificare* se i token fine-grained le permettono nel tuo account: se nella sezione compare un errore sulle notifiche, crea invece un token **classic** (stessa pagina → Tokens (classic)) con gli ambiti `repo`, `workflow`, `notifications`.

**Sezione GitHub del pannello:**
- profilo, notifiche (con "segna come lette"), pull request e issue aperte che ti riguardano;
- elenco dei repository con lo stato dell'ultima **build** (GitHub Actions);
- apertura e **modifica di file** con salvataggio (commit) su GitHub;
- nuove issue, commenti, chiusura issue, **unione di pull request** (con conferma).

**Comandi:** `github`, `i miei repository`, `pull request`, `issue aperte`, `stato build jarvis`, `crea issue su jarvis: il microfono non va`, `commenta la pr 5 di jarvis: testato`, `chiudi issue 7 di jarvis`, `leggi il file README.md di Amiibo`, `crea repository privato prova`, `stella a owner/repo`, `cerca su github piper tts`.
- Unire una pull request a voce o per iscritto richiede la parola **confermo**: `unisci la pr 5 di jarvis confermo`.
- Nomi dei repository: regola del 90%. "jarvs" trova "jarvis"; un nome che non corrisponde non fa nulla.

Il rapporto all'attivazione e il riepilogo quotidiano includono le notifiche GitHub non lette. Ogni operazione su GitHub finisce nel **Registro attività**.

## Fase 23 – Esercizi di matematica, meccanica e tecnologia

Jarvis risolve gli esercizi con **calcoli esatti** (libreria SymPy, gratuita): non "indovina" come un'intelligenza artificiale generica. Se un dato è ambiguo o l'esercizio non è riconosciuto, lo dice invece di dare un risultato sbagliato. Mostra sempre i **passaggi**.

**Matematica** (scrivi o detta):
- `risolvi x^2 - 5x + 6 = 0` (mostra Δ e le soluzioni) · `risolvi 2x + 3 = 11` · sistemi: `risolvi x + y = 5; x - y = 1`
- `deriva x^3*sin(x)` · `integra x^2 da 0 a 3` · `integra 1/x` · `limite di sin(x)/x per x che tende a 0`
- `scomponi x^2 - 9` · `espandi (x+1)^3` · `semplifica ...` · `calcola 3/4 + 2^5 * sqrt(2)`
- Si possono usare `sen`, `tg`, `radice di`, `π`, `²`, la virgola decimale.

**Fisica, meccanica, elettrotecnica, tecnologia**: scrivi l'esercizio come sul libro, con i dati e le unità di misura. Esempi provati:
- "Un'auto parte da ferma e accelera a 2 m/s² per 10 s. Che velocità raggiunge?" → 20 m/s
- "Un'auto a 72 km/h frena fino a fermarsi in 4 s. Calcola l'accelerazione." → -5 m/s²
- "Una lampadina da 60 W è alimentata a 230 V. Quale corrente assorbe?" → 0,26 A
- "Due resistenze da 10 ohm e 20 ohm in parallelo. Calcola la resistenza equivalente." → 6,67 Ω
- "Una ruota dentata motrice da 20 denti gira a 1500 giri/min ... ruota condotta da 60 denti. Quanti giri fa la ruota condotta?" → 500 giri/min
- "Un motore eroga una coppia di 50 Nm a 3000 giri/min. Calcola la potenza." → 15708 W
- Forma rapida: `m=10 kg, a=3 m/s^2, F=?`
- Conversioni: `converti 120 km/h in m/s`

Argomenti coperti: moto uniforme e accelerato, caduta libera, dinamica, lavoro/energia/potenza/rendimento, moto circolare, leve e momenti, trasmissioni a ingranaggi, pressione e fluidi, legge di Ohm, potenza ed energia elettrica, resistenze in serie e in parallelo, calorimetria. Jarvis concatena più formule quando serve (es. coppia + giri → frequenza → velocità angolare → potenza).

**Limiti:**
- se due dati hanno la stessa unità e non dici quale è quale (es. due velocità senza "iniziale/finale"), te lo chiede;
- esercizi fuori da questi argomenti, o con figure e grafici, non li risolve: risponde "Dati insufficienti per verificare".

## Fase 24 – Riconoscimento della scrittura a mano

Sezione **Scrittura** del pannello: scrivi col dito o col mouse sulla lavagna, oppure carica/scatta la **foto di un foglio**, poi **Riconosci**.

**Come funziona:**
1. divide l'immagine in righe, parole e **lettere**;
2. riconosce ogni lettera confrontando la forma, la direzione dei tratti, quanto sale e scende rispetto alla riga (è ciò che distingue l da i, d da a, p da o) e la presenza del puntino o degli accenti;
3. se due lettere si toccano, prova i punti di taglio possibili e sceglie la divisione più sicura;
4. ogni parola ha una **certezza**: sotto il 90% prova a correggerla con le parole che conosce. Se resta in dubbio, la evidenzia in arancione e **te la chiede**;
5. quando premi **Conferma e impara**, ogni lettera diventa un nuovo esempio della **tua** calligrafia. Funziona anche se le lettere erano attaccate: Jarvis trova i tagli che corrispondono alla parola giusta. I pattern che si ripetono vengono riconosciuti sempre meglio.

**Per iniziare bene:**
- **Allenamento**: Jarvis ti mostra una lettera alla volta (a–z, 0–9). Scrivila 3–5 volte staccata sulla lavagna e premi **Salva e passa alla prossima**. Bastano 10 minuti per un grosso miglioramento.
- All'inizio Jarvis usa esempi creati dai caratteri "scritti a mano" di Windows (Ink Free, Segoe Print, Comic Sans).

**Risultati delle mie prove** (su caratteri diversi da quelli di partenza, usati come "calligrafia sconosciuta"):
- lettere staccate, tratto normale: dal 51–98% di lettere giuste;
- dopo **3 sole correzioni**, nella maggior parte delle prove si sale fino al 90–96%.
- **Lettere molto spesse e fuse tra loro** (corsivo tutto attaccato): resta debole (20–58%) e chiede spesso.

Una calligrafia vera **non l'ho potuta provare**.

**Limiti:**
- riconosce solo lettere e numeri (non simboli come + = ^);
- foto storte o scure peggiorano il risultato;
- scrivi su sfondo chiaro e uniforme.

Il pulsante **Esegui come comando** manda il testo letto a Jarvis, come se lo avessi scritto nella barra.

## Fase 25 – Compiti dai professori (Teams e posta)

Jarvis controlla ogni 15 minuti (`COMPITI_OGNI_MINUTI`) le chat di Teams, i compiti di Teams, la posta della scuola e Gmail. Quando un professore chiede degli esercizi:
1. ti avvisa (a voce, nel pannello e con un WhatsApp a te stesso) e crea una **bozza** nella sezione **Compiti**;
2. per ogni esercizio prepara **soluzione con i passaggi** (quelli che sa risolvere, Fase 23), **consigli** (formule, metodo, errori da evitare) e **cosa devi fare** (scadenza, pagine del libro, consegna);
3. se è un esercizio **su foglio/quaderno** te lo spiega e ti dà i consigli; la soluzione è nascosta sotto "Soluzione per controllo", così puoi farlo tu e poi verificare;
4. se è da consegnare **in digitale** (chat di Teams, email) prepara la risposta, che puoi modificare.

**Niente viene inviato da solo.** Per inviare:
- prima devi **vedere** la bozza: `mostra esercizio 1` oppure "Vedi bozza" nel pannello. Senza questo passaggio Jarvis rifiuta;
- poi devi dire o scrivere chiaramente **`manda esercizio 1`**. Nel pannello, il pulsante "Manda esercizio" chiede di scrivere esattamente "manda esercizio".

I compiti di **Teams (Assignments)** non si possono consegnare da Jarvis: apri il link "Apri su Teams" e carica la foto o il file.

Comandi: `controlla i compiti`, `compiti`, `mostra esercizio 1`, `consigli 1`, `manda esercizio 1`, `scarta esercizio 1`.

**Impostazioni** (`config.py`):
- `COMPITI_MITTENTI = ["scuola.edu.it"]`: domini o indirizzi dei professori su Gmail.
- `TEAMS_POSTA_SCUOLA = True`: posta della scuola (Outlook).
- `TEAMS_LEGGI_COMPITI = True`: compiti di Teams. *Dati insufficienti per verificare* se la tua scuola concede questi permessi: se dopo averli attivati `accedi_teams.bat` dà errore di approvazione, rimettili a `False`.
- Dopo aver cambiato queste impostazioni esegui di nuovo `accedi_teams.bat`: Jarvis ora chiede anche il permesso di scrivere nelle chat (per "manda esercizio").

**Nota:** consegnare come proprio un lavoro preparato da Jarvis può essere contro le regole della scuola. Usa soluzioni e consigli per capire e verificare.

## Il manuale di meccanica

- **Titolo:** *La Vettura Automobile – Sue parti, suo funzionamento*
- **Autore:** Ing. Alamanno De Maria – Torino, S. Lattes & C., **1907**
- **Fonte:** Project Gutenberg, eBook n. 44067 – <https://www.gutenberg.org/ebooks/44067> – pubblico dominio
- **Contenuto:** carburazione e carburatori, motore a quattro tempi, accensione (magnete, accumulatori, bobine), raffreddamento e radiatori, motori policilindrici, regolazione, innesto (frizione), cambio di velocità, differenziale, trasmissione, freni, sterzo, sospensioni, ruote e pneumatici, telai, automobili a vapore ed elettriche, camion, vetture da corsa.

**Limite importante:** il manuale è del 1907. Non contiene tecnologia moderna (iniezione elettronica, centraline, ABS, turbo moderni, auto ibride ecc.). Su questi argomenti Jarvis risponde che il manuale non contiene l'informazione.

**Aggiungere altri manuali:** copia qualsiasi file di testo `.txt` (codifica UTF-8) nella cartella `C:\Jarvis\manuali`. Jarvis lo legge automaticamente al successivo avvio.

## Problemi frequenti

| Messaggio | Soluzione |
|---|---|
| `'py' non è riconosciuto...` | Python non installato o non nel PATH: ripeti la Fase 1. |
| `File credentials.json non trovato` | Ripeti la Fase 3, punto 7. Controlla il nome esatto del file. |
| `librerie Google mancanti` | Doppio clic su `installa.bat`. |
| `Errore 403: access_denied` nel browser | Non hai aggiunto la tua email come utente di test (Fase 3, punto 5). |
| `Gmail API has not been used in project...` | Gmail API non abilitata (Fase 3, punto 3). |
| Gmail nel pannello dà errore di accesso | Cancella `C:\Jarvis\token.json` e riavvia Jarvis. |
| "Ollama non attivo o modello non scaricato" | Fase 6. Verifica con `ollama list` nel Prompt dei comandi. |
| `Node.js non installato` | Fase 7, punto 1. Dopo l'installazione riavvia il PC. |
| WhatsApp non funziona più | WhatsApp aggiorna spesso il suo sito e la libreria smette di funzionare. Chiudi le finestre di Jarvis ed esegui di nuovo `installa_whatsapp.bat` per scaricare l'ultima versione. Se non basta, cancella `C:\Jarvis\whatsapp\sessione` e ricollega col QR. |
| "Jarvis attivazione" non viene riconosciuto | Controlla nella finestra "JARVIS - Ascolto" che non ci siano errori. Impostazioni di Windows → Sistema → Audio → Input: scegli il microfono giusto e alza il volume. Parla vicino al microfono, scandendo. |
| La finestra "Ascolto" dà errore sul microfono | Impostazioni → Privacy e sicurezza → Microfono → attiva "Consenti alle app desktop di accedere al microfono". |
| Il pannello dice "Servizio WhatsApp spento" | La finestra "JARVIS - WhatsApp" è chiusa o in errore: riavvia `avvia_server_jarvis.bat`. |
| Pagina `localhost:8080` non raggiungibile | La finestra "JARVIS - Pannello" è chiusa o in errore: leggi il messaggio e riavvia `avvia_server_jarvis.bat`. |
| Jarvis non parla | La voce usa la sintesi vocale di Windows. Per una voce italiana: Impostazioni → Ora e lingua → Voce → Aggiungi voci → Italiano. Per spegnere la voce: `VOCE_ATTIVA = False` in `config.py`. |
