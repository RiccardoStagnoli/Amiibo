# Impostazioni di Jarvis. Puoi modificarle con il Blocco note.

# Quante email mostrare in ogni elenco.
EMAIL_DA_MOSTRARE = 10

# Intelligenza artificiale locale e gratuita (Ollama) usata per formulare
# le risposte di meccanica. Se Ollama non e' installato, Jarvis mostra
# direttamente i passaggi del manuale.
INDIRIZZO_OLLAMA = "http://localhost:11434"
MODELLO_OLLAMA = "gemma2:2b"

# Quanti passaggi del manuale passare all'intelligenza artificiale.
BRANI_PER_RISPOSTA = 4

# Voce di Jarvis (sintesi vocale di Windows). False = solo testo.
VOCE_ATTIVA = True
VELOCITA_VOCE = 175

# ------------------------- PANNELLO WEB (server) -------------------------
NOME_UTENTE = "Riccardo"
# Stile di parlata "saggio maestro" (frasi con soggetto e verbo invertiti).
STILE_SAGGIO = True
PORTA_PANNELLO = 8080
# "127.0.0.1" = pannello visibile solo da questo PC.
# "0.0.0.0"   = visibile anche da telefono/altri PC della stessa rete Wi-Fi
#               (in quel caso PASSWORD_PANNELLO e' obbligatoria).
HOST_PANNELLO = "127.0.0.1"
PASSWORD_PANNELLO = ""
# True se usi Tailscale (o simili) per usare Jarvis fuori casa / dal Rabbit R1.
# In quel caso PASSWORD_PANNELLO (almeno 12 caratteri) e' obbligatoria.
ACCESSO_REMOTO = False

# ------------------------- ATTIVAZIONE VOCALE -------------------------
FRASE_ATTIVAZIONE = "jarvis attivazione"
# Modello vocale offline:
#  "vosk-model-small-it-0.22" = leggero (50 MB), sbaglia spesso i comandi dopo l'attivazione
#  "vosk-model-it-0.22"       = piu preciso (1,3 GB da scaricare, usa molta piu RAM)
MODELLO_VOSK = "vosk-model-small-it-0.22"
# Browser usato per aprire il pannello: "edge" oppure "chrome".
BROWSER = "edge"

# ------------------------- PERSONALITA' -------------------------
# Jarvis agisce/risponde solo se e' sicuro almeno al 90%.
SOGLIA_CERTEZZA = 0.90
# Insulti quando sbagli TU (comando vuoto, nome inesistente, password errata...).
INSULTI_ATTIVI = True

# ------------------------- METEO (Open-Meteo, gratis) -------------------------
CITTA_METEO = "Milano"

# ------------------------- GMAIL: pulizia -------------------------
# Mittenti o domini da non toccare MAI nella pulizia (es. "scuola.it", "banca.it").
MITTENTI_PROTETTI = []

# ------------------------- PC MSI (controllo remoto) -------------------------
# Token segreto condiviso con l'agente sul PC Msi (GUIDA, Fase 13).
# Lascia vuoto per disattivare il controllo del PC Msi.
TOKEN_AGENTE_MSI = ""

# ------------------------- TEAMS (GUIDA, Fase 12) -------------------------
TEAMS_CLIENT_ID = ""
# "organizations" oppure il dominio della scuola, es. "scuola.edu.it"
TEAMS_TENANT = "organizations"
# Nomi (o parti di nome) dei professori. Lista vuota = tutti i messaggi.
TEAMS_PROFESSORI = []
# Leggere anche i post nei canali dei corsi: richiede il consenso dell'amministratore della scuola.
# Lascialo False finche' la scuola non approva, altrimenti l'accesso a Teams puo' fallire del tutto.
TEAMS_LEGGI_CANALI = False

# ------------------------- FUNZIONI EXTRA (GUIDA, Fase 16) -------------------------
# Riepilogo automatico ogni giorno a quest'ora (formato "HH:MM"). "" = disattivato.
ORA_RIEPILOGO = "07:00"
# Manda il riepilogo e i promemoria anche come messaggio WhatsApp a te stesso
# (chat "Tu"/"Messaggi a te stesso"), utile quando sei fuori casa.
RIEPILOGO_SU_WHATSAPP = True
PROMEMORIA_SU_WHATSAPP = True

# Accensione del PC Msi via rete (Wake-on-LAN). Indirizzo MAC della scheda di rete del Msi,
# es. "1C:2B:3D:4E:5F:60". "" = disattivato.
MAC_MSI = ""
BROADCAST_RETE = "255.255.255.255"

# Macro: una frase che esegue piu' comandi in sequenza.
MACRO = {
    "modalita gioco": ["apri steam", "apri discord"],
    "modalita studio": ["non disturbare per 2 ore", "ricordami tra 50 minuti di fare una pausa"],
    "buonanotte": ["spegni msi", "promemoria"],
}

# ------------------------- VOCE DI JARVIS (GUIDA, Fase 18) -------------------------
# "piper"   = voce neurale offline generata dal server (stessa voce su PC, telefono, R1)
# "browser" = voci del browser/di Windows (come prima)
VOCE_MOTORE = "piper"
# Voci italiane: it_IT-riccardo-x_low (maschile), it_IT-paola-medium, it_IT-serena-medium, it_IT-serena-high
VOCE_PIPER = "it_IT-riccardo-x_low"
# "jarvis" = leggero effetto metallico da assistente; "nessuno" = voce pulita
EFFETTO_VOCE = "jarvis"
# Velocita': 1.0 normale, 1.15 piu' lenta, 0.9 piu' veloce
VELOCITA_PIPER = 1.0

# ------------------------- APP PER TELEFONO (GUIDA, Fase 19) -------------------------
# Indirizzo da aprire sul telefono (mostrato come QR in Impostazioni), es. l'indirizzo
# https://....ts.net di Tailscale. Vuoto = Jarvis prova a ricavare l'IP di rete del server.
INDIRIZZO_TELEFONO = ""

# ------------------------- COMPITI DAI PROFESSORI (GUIDA, Fase 25) -------------------------
# Leggere i compiti di Teams (Assignments): permesso EduAssignments.ReadBasic, potrebbe servire l'ok della scuola.
TEAMS_LEGGI_COMPITI = False
# Leggere e rispondere alla posta della scuola (Outlook/Microsoft 365): permessi Mail.Read e Mail.Send.
TEAMS_POSTA_SCUOLA = False
# Indirizzi o domini dei professori su Gmail (es. "scuola.edu.it"). Vuoto = Jarvis usa solo
# le email con "esercizi"/"compiti" nell'oggetto.
COMPITI_MITTENTI = []
# Ogni quanti minuti controllare Teams e la posta. 0 = mai in automatico.
COMPITI_OGNI_MINUTI = 15
