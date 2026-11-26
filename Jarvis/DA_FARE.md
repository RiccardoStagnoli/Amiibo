# JARVIS – Tutto quello che devi fare, in ordine

Segui le parti nell'ordine. Ogni punto rimanda alla **Fase** di `GUIDA.md`, dove trovi i dettagli.
Le parti segnate *(facoltativa)* si possono saltare: Jarvis funziona lo stesso, senza quella funzione.

---

## PARTE 0 – Cosa ti serve

- [ ] Un **PC server** con Windows 10/11 sempre acceso, con **microfono** e **casse** (per "Jarvis attivazione"). Meglio collegato al router **via cavo**.
- [ ] Il tuo **PC Msi** *(facoltativo, per il controllo a distanza)*.
- [ ] Gli account che vuoi collegare:
  - **obbligatorio:** Google (Gmail);
  - **facoltativi:** WhatsApp, account Microsoft della scuola (Teams), ClasseViva, Amazon (Alexa), Spotify, Discord, GitHub.

## PARTE 1 – Installare i programmi sul PC server

1. [ ] **Python 3** da python.org. Durante l'installazione spunta **"Add python.exe to PATH"**.
   Controllo: nel Prompt dei comandi `py --version` (Fase 1).
2. [ ] **Node.js LTS** da nodejs.org, con le opzioni predefinite (Fase 7).
3. [ ] **Scarica Jarvis**: GitHub `riccardostagnoli/amiibo` → ramo `claude/jarvis-gmail-reader-k8f67k` → Code → Download ZIP (oppure il `Jarvis.zip` della chat). Estrai e copia la cartella in **`C:\Jarvis`** (Fase 2).
4. [ ] Doppio clic su **`C:\Jarvis\installa.bat`** (Fase 4).
   - Se dà errore su "piper" o "onnxruntime", installa il **Microsoft Visual C++ Redistributable x64** dal sito Microsoft e rilancialo.
5. [ ] Doppio clic su **`C:\Jarvis\installa_whatsapp.bat`**. Installa WhatsApp e Alexa e richiede alcuni minuti.

## PARTE 2 – Account Google (Fase 3 e 5)

6. [ ] Su console.cloud.google.com:
   - crea il progetto **Jarvis**;
   - abilita **Gmail API**, **Google Calendar API** e **Google Drive API**.
7. [ ] Configura la schermata di consenso:
   - tipo **Esterno**;
   - in **Pubblico → Utenti di test** aggiungi il tuo indirizzo Gmail.
8. [ ] In **Client → Crea client** scegli **App desktop**, poi **Scarica JSON**.
   - Rinomina il file in **`credentials.json`** e mettilo in `C:\Jarvis`.
   - Attento che non diventi `credentials.json.json`.
9. [ ] Fai il primo accesso:
   - doppio clic su `avvia_jarvis.bat` e premi `1`;
   - nel browser accetta **tutti** i permessi (all'avviso "app non verificata" scegli Continua).
   - Si ripete ogni 7 giorni finché l'app resta in modalità Test.

## PARTE 3 – Impostazioni base in `C:\Jarvis\config.py` (si apre con il Blocco note)

10. [ ] `NOME_UTENTE`, `CITTA_METEO`, `ORA_RIEPILOGO` (es. `"07:00"`).
11. [ ] `MITTENTI_PROTETTI` (es. `["scuola.edu.it"]`): queste email non verranno mai pulite.
12. [ ] `COMPITI_MITTENTI`: domini o indirizzi Gmail dei professori.
13. [ ] Personalizza le `MACRO` (es. "modalita gioco").
14. [ ] Lascia `INSULTI_ATTIVI = True` e `SOGLIA_CERTEZZA = 0.90`, oppure cambiali.

## PARTE 4 – Primo avvio del server

15. [ ] Doppio clic su **`C:\Jarvis\avvia_server_jarvis.bat`**. Si aprono 4 finestre ridotte a icona: **WhatsApp, Pannello, Ascolto, Alexa**. Non chiuderle.
    - Al primo avvio vengono scaricati il modello vocale (50 MB) e la voce di Jarvis (28 MB).
16. [ ] Apri **http://localhost:8080** → **Impostazioni** → inquadra il **QR** con WhatsApp sul telefono (Dispositivi collegati → Collega un dispositivo) (Fase 8).
17. [ ] Impostazioni → Voce → **Prova voce**. Se non senti niente, controlla le casse e il motore "Voce di Jarvis".
18. [ ] Windows → Privacy e sicurezza → **Microfono**: consenti l'accesso alle app desktop.
19. [ ] Prova l'attivazione: di' **"Jarvis attivazione"**, aspetta il **"Sì?"**, poi "che ore sono" (Fase 31).
    - Se capisce male, metti `MODELLO_VOSK = "vosk-model-it-0.22"` (1,3 GB) e riavvia.
20. [ ] Facoltativo: aggiungi le voci italiane di Windows (Impostazioni → Ora e lingua → Voce).

## PARTE 5 – Server sempre acceso (Fase 9)

21. [ ] Impostazioni → Sistema → Alimentazione: sospensione **Mai**.
22. [ ] `Win + R` → `shell:startup` → crea un collegamento a `avvia_server_jarvis.bat`.
23. [ ] Nel router assegna al server un **IP fisso**. Annota l'IP (`ipconfig` → Indirizzo IPv4).

## PARTE 6 – Sicurezza (prima di aprire Jarvis ad altri dispositivi)

24. [ ] In `config.py` metti una `PASSWORD_PANNELLO` di almeno 12 caratteri.
25. [ ] Metti `HOST_PANNELLO = "0.0.0.0"` (serve per telefono e Msi in casa) e riavvia il server.
26. [ ] Ogni tanto controlla **Impostazioni → Registro attività**: accessi e password sbagliate.

## PARTE 7 – Telefono e fuori casa (Fasi 14, 20)

27. [ ] Crea un account **Tailscale** e installalo sul **server** e sul **telefono**, con lo stesso account.
28. [ ] Sul server, nel Prompt dei comandi: `tailscale serve --bg 8080`. Se compare un link per abilitare HTTPS, aprilo e conferma.
29. [ ] In `config.py`:
    - `ACCESSO_REMOTO = True`;
    - `INDIRIZZO_TELEFONO = "https://<nome-pc>.<tuo-nome>.ts.net"`;
    - poi riavvia il server.
30. [ ] Pannello → Impostazioni → **App per telefono** → inquadra il QR con il telefono → installa l'app:
    - Android: menu ⋮ → Installa app;
    - iPhone: Condividi → Aggiungi alla schermata Home.
31. [ ] Sull'app del telefono: Impostazioni → Voce → **Ascolto sempre attivo**, poi consenti il microfono.
32. [ ] *(facoltativa)* Rabbit R1:
    - sul server esegui `tailscale funnel --bg 8080`;
    - sul R1 apri `https://...ts.net/?modo=r1`. La procedura sul R1 non è verificata.

## PARTE 8 – Scuola: Teams e ClasseViva (Fasi 12, 25, 26)

33. [ ] Su entra.microsoft.com (con un account Microsoft personale) → Registrazioni app → **Nuova**:
    - nome `Jarvis`, multi-tenant;
    - in **Autenticazione** metti **Consenti flussi client pubblici = Sì**;
    - copia l'ID applicazione in `TEAMS_CLIENT_ID`.
34. [ ] In `config.py`:
    - `TEAMS_PROFESSORI` (cognomi dei prof);
    - facoltativo: `TEAMS_POSTA_SCUOLA = True` e `TEAMS_LEGGI_COMPITI = True`.
35. [ ] Doppio clic su **`accedi_teams.bat`**, poi inserisci il codice su microsoft.com/devicelogin con l'**account della scuola**.
    - Se compare "approvazione dell'amministratore necessaria", rimetti `False` le opzioni del punto 34. Se continua, la scuola blocca l'accesso: usa le notifiche email di Teams inoltrate a Gmail.
36. [ ] Pannello → **Compiti** → inserisci le credenziali **ClasseViva** → Collega.
37. [ ] Prova: `controlla i compiti` → `mostra esercizio 1`. L'invio avviene solo con **`manda esercizio 1`**.

## PARTE 9 – PC Msi *(facoltativa)* (Fasi 13, 16, 21)

38. [ ] Inventa un token lungo e casuale e scrivilo in `config.py` → `TOKEN_AGENTE_MSI`, poi riavvia il server.
39. [ ] Sul Msi:
    - installa Python;
    - copia la cartella `C:\Jarvis\msi` in `C:\JarvisMsi`;
    - in `msi_agente.py` imposta `SERVER = "http://IP-DEL-SERVER:8080"` e `TOKEN` (uguale al server).
40. [ ] Sul Msi: `installa_msi.bat`, poi `avvia_msi.bat`, poi collegamento di `avvia_msi.bat` in `shell:startup`.
41. [ ] Di' o scrivi `apri chrome`. Nella finestra "Chrome di Jarvis" accedi a Google e attiva la **sincronizzazione**.
42. [ ] *(facoltativa)* Accensione a distanza:
    - collega il Msi al router via cavo;
    - `ipconfig /all` → copia l'Indirizzo fisico in `MAC_MSI`;
    - attiva "Wake on Magic Packet" in Gestione dispositivi e la riattivazione da rete nel BIOS.

## PARTE 10 – Casa, musica e altri servizi *(facoltative)* (Fasi 22, 27, 28, 29)

43. [ ] **Alexa:** dal PC server apri **http://127.0.0.1:3456** e accedi ad Amazon. Prova: `accendi la luce del salotto`.
44. [ ] **Spotify:**
    - developer.spotify.com → Create app;
    - Redirect URI **`http://127.0.0.1:8080/spotify/callback`**, API "Web API";
    - Client ID in `SPOTIFY_CLIENT_ID`, poi riavvia;
    - dal PC server apri **http://127.0.0.1:8080/spotify/accedi**.
    - Il comando della riproduzione richiede Premium.
45. [ ] **Discord:**
    - discord.com/developers → New Application → Bot → copia il token in `DISCORD_BOT_TOKEN`;
    - attiva **Message Content Intent**;
    - OAuth2 → URL Generator (`bot`, View Channels, Send Messages, Read Message History) → aggiungi il bot al tuo server;
    - in `DISCORD_CANALI` metti gli ID dei canali (Modalità sviluppatore → tasto destro sul canale → Copia ID).
46. [ ] **GitHub:**
    - github.com → Settings → Developer settings → Fine-grained token;
    - permessi: Contents, Issues, Pull requests in lettura/scrittura; Actions e Metadata in sola lettura;
    - pannello → **GitHub** → incolla il token → Collega.

## PARTE 11 – Intelligenza artificiale locale *(facoltativa, consigliata)* (Fasi 6, 30)

47. [ ] Installa **Ollama** da ollama.com, poi nel Prompt dei comandi:
    - `ollama pull gemma2:2b`, per le risposte di meccanica e documenti;
    - `ollama pull qwen2.5:7b` (circa 5 GB), per le **guide passo passo**.
48. [ ] In `config.py` metti `MODELLO_GUIDE = "qwen2.5:7b"`. Se il PC è troppo lento, lascialo vuoto.

## PARTE 12 – Insegnare a Jarvis (primi giorni)

49. [ ] **Per te:**
    - scrivi 5–10 cose che ti piacciono (o di' "mi piace ...");
    - scrivi gli oggetti da tenere d'occhio.
50. [ ] **Memoria:**
    - insegna fatti su di te ("ricorda che la mia moto è...");
    - carica i libretti di moto o auto e gli appunti in PDF.
51. [ ] **Scrittura → Allenamento:** scrivi ogni lettera 3–5 volte, staccata (circa 10 minuti).
52. [ ] Ogni settimana:
    - Memoria → "Comandi e domande che non ho capito" → **Insegna**;
    - Scrittura → correggi le parole arancioni → **Conferma e impara**.
53. [ ] Ogni tanto copia la cartella **`C:\Jarvis\dati`** su una chiavetta o su Drive. Contiene tutto quello che Jarvis sa.

## PARTE 13 – Controllo finale (se tutti funzionano, Jarvis è a posto)

- [ ] "Jarvis attivazione" → "che ore sono" → risposta a voce dalle casse.
- [ ] `leggi la posta` → elenco delle email non lette.
- [ ] `agenda` → impegni di Google Calendar e ClasseViva.
- [ ] `controlla i compiti` → bozze nella sezione Compiti.
- [ ] Scrivi a te stesso su WhatsApp da un altro numero → compare nel pannello.
- [ ] `risolvi x^2-5x+6=0` → x = 2; x = 3.
- [ ] `novità per me` → notizie sui tuoi interessi.
- [ ] Dal telefono (app Jarvis) → "Jarvis attivazione" → "meteo".
- [ ] *(se configurati)* `apri chrome e cerca youtube` (Msi), `accendi la luce` (Alexa), `metti ... su spotify`, `messaggi discord`, `github`.

Se qualcosa non va: `GUIDA.md` → **Problemi frequenti**, e le 4 finestre di Jarvis (gli errori sono scritti lì).

---

### Cose che non si possono fare gratis (già spiegate)
- **Chiamate al cellulare Vodafone:** puoi registrare il saluto della segreteria al 42020, ma Jarvis non può leggere quei messaggi. La versione automatica richiede **Twilio**, a pagamento.
- **Prezzi dei negozi:** Jarvis prepara i link di ricerca, ma non legge i prezzi.
- **Voce originale del Jarvis dei film:** non usata, perché sarebbe la copia della voce di un attore reale.

### Mai provato con i tuoi account veri (controllalo tu ai punti sopra)
WhatsApp, Google, Teams, ClasseViva, Alexa, Spotify, Discord, GitHub, PC Msi, microfono e casse reali, Windows.
Tutto è stato provato con servizi simulati e su Linux.
