# JARVIS – Guida di installazione (Windows 11)

Funzioni di questa versione:

1. **Lettura di Gmail** (sola lettura: Jarvis non può inviare, cancellare o modificare email).
2. **Risposte di meccanica** basate **solo** sul manuale nella cartella `manuali`.

Costo: zero. Si usano la Gmail API di Google (gratuita), Python (gratuito) e, opzionale, Ollama (intelligenza artificiale locale gratuita).

Cartella finale del progetto: **`C:\Jarvis`**

```
C:\Jarvis\
 ├─ jarvis.py              programma principale
 ├─ gmail_reader.py        lettura Gmail
 ├─ meccanica.py           risposte di meccanica
 ├─ config.py              impostazioni
 ├─ requirements.txt       elenco librerie
 ├─ installa.bat           installa le librerie (una volta sola)
 ├─ avvia_jarvis.bat       avvia Jarvis
 ├─ credentials.json       lo scarichi tu da Google (Fase 3)
 └─ manuali\
     └─ la_vettura_automobile_1907.txt
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

## Fase 5 – Primo avvio

1. Doppio clic su **`C:\Jarvis\avvia_jarvis.bat`**.
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
| Errori di accesso persistenti | Cancella `C:\Jarvis\token.json` e riavvia Jarvis. |
| "Ollama non attivo o modello non scaricato" | Fase 6. Verifica con `ollama list` nel Prompt dei comandi. |
