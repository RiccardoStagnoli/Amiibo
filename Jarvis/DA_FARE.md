# JARVIS – Cose da fare a mano (in ordine)

Qui c'è tutto quello che non ho potuto fare io, dall'inizio della conversazione.
I dettagli di ogni passo sono in `GUIDA.md`, nella Fase indicata tra parentesi.
Spunta ogni riga quando l'hai fatta.

## A. Una volta sola, sul PC SERVER

- [ ] **1. Python** (Fase 1)
  - Scarica Python 3 da python.org e installalo spuntando "Add python.exe to PATH".
  - Verifica: `py --version` nel Prompt dei comandi.
- [ ] **2. Cartella Jarvis** (Fase 2)
  - Estrai `Jarvis.zip` e metti la cartella in `C:\Jarvis`.
- [ ] **3. Google Cloud** (Fase 3)
  - Crea il progetto `Jarvis`.
  - Abilita **Gmail API**, **Google Calendar API** e **Google Drive API**.
  - Configura la schermata di consenso: tipo "Esterno", tu come **utente di test**.
  - Crea un client di tipo **App desktop** e scarica il JSON.
  - Rinominalo `credentials.json` e mettilo in `C:\Jarvis`.
- [ ] **4. Librerie Python** (Fase 4)
  - Doppio clic su `C:\Jarvis\installa.bat`.
- [ ] **5. Primo accesso a Google** (Fase 5)
  - Doppio clic su `avvia_jarvis.bat`, poi tasto `1`.
  - Nel browser accetta **tutti** i permessi.
  - In modalità Test va ripetuto ogni 7 giorni: Jarvis riapre il browser da solo.
- [ ] **6. Node.js e WhatsApp** (Fase 7)
  - Installa Node.js LTS da nodejs.org.
  - Doppio clic su `installa_whatsapp.bat`.
- [ ] **7. Personalizza `config.py`** (aprilo con il Blocco note)
  - `NOME_UTENTE`
  - `CITTA_METEO`
  - `MITTENTI_PROTETTI`: domini da non toccare mai, es. `"scuola.it"`.
  - `INSULTI_ATTIVI`
  - `SOGLIA_CERTEZZA`: lascia 0.90.
- [ ] **8. Avvio** (Fase 8)
  - Doppio clic su `avvia_server_jarvis.bat`.
  - Apri http://localhost:8080 → Impostazioni → inquadra il **QR** con WhatsApp sul telefono (Dispositivi collegati).
- [ ] **9. Microfono e voce** (Fasi 8 e 15)
  - Collega il microfono al server.
  - Impostazioni Windows → Privacy → Microfono: consenti alle app desktop.
  - Impostazioni Windows → Ora e lingua → Voce: aggiungi le voci **Italiano**.
  - Nel pannello → Impostazioni → Voce: scegli una voce non "Natural" e regola il tono.
- [ ] **10. Server sempre acceso** (Fase 9)
  - Sospensione **Mai**.
  - Collegamento di `avvia_server_jarvis.bat` in `shell:startup`.
  - IP fisso del server nel router.
- [ ] **11. Ollama** (Fase 6, facoltativo)
  - Installa Ollama, poi esegui `ollama pull gemma2:2b`.
  - Serve per risposte di meccanica scritte in modo discorsivo.

## B. Teams (Fase 12)

- [ ] **12.** Registra l'app `Jarvis` su entra.microsoft.com:
  - tipo di account: multi-tenant;
  - "Consenti flussi client pubblici" = **Sì**.
- [ ] **13.** In `config.py`:
  - copia l'ID applicazione in `TEAMS_CLIENT_ID`;
  - scrivi i cognomi dei prof in `TEAMS_PROFESSORI`.
- [ ] **14.** Doppio clic su `accedi_teams.bat`, poi inserisci il codice su microsoft.com/devicelogin con l'**account della scuola**.
- [ ] **15.** Se compare "Approvazione dell'amministratore necessaria": la scuola blocca l'accesso. Usa l'alternativa: notifiche email di Teams inoltrate al tuo Gmail.

## C. PC Msi (Fase 13)

- [ ] **16.** Sul server, in `config.py`:
  - `TOKEN_AGENTE_MSI`: un token lungo e casuale;
  - `HOST_PANNELLO = "0.0.0.0"`;
  - `PASSWORD_PANNELLO`: almeno 12 caratteri.
  - Poi riavvia il server.
- [ ] **17.** Sul Msi: installa Python e copia la cartella `msi` in `C:\JarvisMsi`.
- [ ] **18.** In `msi_agente.py` imposta `SERVER` (IP del server) e `TOKEN` (lo stesso del server).
- [ ] **19.** Doppio clic su `installa_msi.bat`, poi su `avvia_msi.bat`. Poi metti il collegamento ad `avvia_msi.bat` in `shell:startup`.

## D. Accesso da ovunque e Rabbit R1 (Fase 14)

- [ ] **20.** Installa Tailscale su server e telefono, con lo stesso account.
- [ ] **21.** In `config.py` imposta `ACCESSO_REMOTO = True` (la password è obbligatoria).
- [ ] **22.** Dal telefono apri `http://100.x.y.z:8080`, poi "Aggiungi a schermata Home".
- [ ] **23.** Rabbit R1:
  - sul server esegui `tailscale funnel --bg 8080`;
  - sul R1 apri l'indirizzo `https://...ts.net/?modo=r1`.
  - Procedura sul R1: **non verificata** (vedi Fase 14).

## E. Funzioni extra (Fase 16, facoltative)

- [ ] **24.** In `config.py` scegli `ORA_RIEPILOGO` (es. `"07:00"`) e personalizza le `MACRO`.
- [ ] **25.** Accensione del Msi dalla rete:
  - collega il Msi al router via cavo;
  - copia il suo MAC in `MAC_MSI`;
  - attiva Wake-on-LAN in Windows e nel BIOS.
- [ ] **26.** Ogni tanto controlla il **Registro attività** (Impostazioni) per verificare gli accessi.

## E2. Insegnare a Jarvis (Fase 17)

- [ ] **26b.** Sezione **Memoria** del pannello:
  - insegna i primi fatti (moto, auto, prof, orari);
  - carica il libretto della tua moto o auto in PDF.
- [ ] **26c.** Ogni settimana controlla *"Comandi e domande che non ho capito"* e premi **Insegna**.
- [ ] **26d.** Fai ogni tanto una copia della cartella `C:\Jarvis\dati`.

## E3. Voce, foto/video e app sul telefono (Fasi 18–20)

- [ ] **26e.** Esegui di nuovo `installa.bat`: aggiunge la voce Piper e il generatore di QR.
  - Al primo avvio il server scarica la voce (28 MB).
  - Se Piper dà errore all'avvio, installa il "Microsoft Visual C++ Redistributable" (x64) dal sito Microsoft. *Dati insufficienti per verificare se serve su ogni PC.*
- [ ] **26f.** In `config.py` scegli `VOCE_PIPER` ed `EFFETTO_VOCE`, poi prova la voce in Impostazioni → Voce → "Prova voce".
- [ ] **26g.** Telefono:
  - esegui `tailscale serve --bg 8080`;
  - in `config.py` imposta `ACCESSO_REMOTO = True`, la password e `INDIRIZZO_TELEFONO`;
  - inquadra il QR in Impostazioni → "App per telefono" e installa l'app.

## E4. Chrome sul Msi (Fase 21)

- [ ] **26h.** Sul Msi:
  - aggiorna la cartella `C:\JarvisMsi` con la nuova cartella `msi`, tenendo `SERVER` e `TOKEN` in `msi_agente.py`;
  - esegui `installa_msi.bat`, poi `avvia_msi.bat`.
- [ ] **26i.** Di' o scrivi `apri chrome`, poi nella nuova finestra accedi a Google e attiva la sincronizzazione.

## E5. GitHub (Fase 22)

- [ ] **26l.** Crea un token su GitHub (Fine-grained, permessi indicati nella guida).
- [ ] **26m.** Incollalo nel pannello: sezione GitHub → Collega.

## E6. Esercizi e scrittura a mano (Fasi 23–24)

- [ ] **26n.** Esegui di nuovo `installa.bat`: aggiunge SymPy, NumPy e Pillow.
- [ ] **26o.** Sezione **Scrittura** → **Allenamento**: scrivi ogni lettera 3–5 volte (circa 10 minuti).
- [ ] **26p.** Quando Jarvis evidenzia una parola in arancione, correggila e premi **Conferma e impara**.

## E7. ClasseViva, Spotify, Discord, Alexa (Fasi 26–29)

- [ ] **26q.** Sezione Compiti → collega **ClasseViva**.
- [ ] **26r.** Esegui di nuovo `installa_whatsapp.bat`, poi riavvia `avvia_server_jarvis.bat` (4 finestre).
- [ ] **26s.** Dal PC server apri http://127.0.0.1:3456 e accedi ad **Amazon** (Alexa).
- [ ] **26t.** **Spotify**:
  - crea l'app sul Developer Dashboard (Redirect `http://127.0.0.1:8080/spotify/callback`);
  - metti il Client ID in `config.py`;
  - dal PC server apri http://127.0.0.1:8080/spotify/accedi.
- [ ] **26u.** **Discord**:
  - crea il bot e attiva il Message Content Intent;
  - aggiungi il bot al tuo server;
  - in `config.py` metti il token e gli ID dei canali.

## E8. Per te (Fase 30)

- [ ] **26v.** Sezione **Per te**: scrivi 5–10 cose che ti piacciono e gli oggetti da tenere d'occhio.
- [ ] **26w.** Per le guide passo passo installa Ollama ed esegui `ollama pull qwen2.5:7b`, poi imposta `MODELLO_GUIDE = "qwen2.5:7b"`. Se il PC è lento, lascia vuoto (usa gemma2:2b).
- [ ] **26x.** Se avevi già collegato Spotify, rifai l'accesso da http://127.0.0.1:8080/spotify/accedi (nuovo permesso per gli artisti preferiti).

## F. Telefono Vodafone (non automatizzabile gratis)

- [ ] **27.** Facoltativo: chiama il **42020** e registra il saluto della segreteria: *"Riccardo non è al momento raggiungibile..."*.
  - Jarvis **non** può leggere questi messaggi: non ho trovato un invio via email da parte di Vodafone.
- [ ] **28.** Se vuoi esattamente quello che hai chiesto (risposta, registrazione, tasto 1, lettura in Jarvis), serve **Twilio**, a pagamento: chiedilo e lo costruisco.

## Cosa NON è stato provato da me (da controllare al primo avvio)

- Collegamento reale a WhatsApp, Google, Teams e PC Msi: li ho provati con servizi **simulati**.
- Funzionamento su Windows: l'ho provato su Linux. I file `.bat` non li ho eseguiti.
- Voce reale del browser e microfono: il riconoscimento della frase "Jarvis attivazione" l'ho provato con audio sintetico.
- Meteo: il servizio Open-Meteo era bloccato dal limite di richieste del mio ambiente. Il formato dei dati è quello documentato.
- La voce originale di Yoda non è disponibile: c'è solo lo stile "saggio maestro" (frasi invertite e tono basso).
