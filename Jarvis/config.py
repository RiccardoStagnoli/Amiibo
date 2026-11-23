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

# ------------------------- ATTIVAZIONE VOCALE -------------------------
FRASE_ATTIVAZIONE = "jarvis attivazione"
# Browser usato per aprire il pannello: "edge" oppure "chrome".
BROWSER = "edge"
