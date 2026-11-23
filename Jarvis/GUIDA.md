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
 ├─ gmail_reader.py, meccanica.py, whatsapp_reader.py, voce.py, jarvis.py
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

## Fase 3 – Autorizzare Jarvis a leggere Gmail (Google Cloud, gratuito)

Non serve carta di credito: la Gmail API non richiede un account di fatturazione.

1. Apri <https://console.cloud.google.com/> e accedi con **lo stesso account Gmail** che Jarvis deve leggere. Accetta i termini se richiesto.
2. **Crea il progetto**: in alto clicca il selettore dei progetti → **Nuovo progetto** → Nome: `Jarvis` → **Crea**. Assicurati che in alto sia selezionato il progetto `Jarvis`.
3. **Abilita la Gmail API**: apri <https://console.cloud.google.com/apis/library/gmail.googleapis.com> → **Abilita**.
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
   - consenti la lettura della posta → **Continua**;
   - compare `The authentication flow has completed`: chiudi la scheda e torna alla finestra di Jarvis.
4. Jarvis mostra le email. Scrivi il numero di un'email per leggerla, Invio vuoto per tornare al menu.

Jarvis salva l'accesso in `C:\Jarvis\token.json`. Con l'app in modalità "Test", Google fa scadere l'accesso dopo **7 giorni**: Jarvis riapre il browser da solo e ripeti il punto 3.

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
