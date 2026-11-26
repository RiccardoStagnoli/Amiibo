"""
JARVIS - Agente per il PC principale "Msi".

Va installato e avviato SUL PC MSI (non sul server).
Si collega da solo al server Jarvis (connessione in uscita: nessuna porta da
aprire sul PC Msi), riceve i comandi e li esegue:
  - aprire programmi (Chrome, Steam, Discord, qualsiasi app del menu Start)
  - cercare su Google o YouTube
  - aprire siti
  - Steam: aprire la pagina di installazione di un gioco
  - screenshot dello schermo
  - bloccare, spegnere, riavviare il PC (spegnimento con 60 s di preavviso)
Comandi liberi del Prompt: DISATTIVATI, salvo COMANDI_LIBERI = True qui sotto.
"""

import base64
import ctypes
import difflib
import glob
import io
import json
import os
import platform
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

import chrome_controllo

# ----------------------------- IMPOSTAZIONI -----------------------------
# Indirizzo del PC server (vedi GUIDA, Fase 13), es. "http://192.168.1.20:8080"
SERVER = "http://192.168.1.20:8080"
# Deve essere UGUALE a TOKEN_AGENTE_MSI nel config.py del server.
TOKEN = "cambia-questo-token"
NOME = "Msi"
# True = Jarvis puo' eseguire qualsiasi comando del Prompt su questo PC. Pericoloso.
COMANDI_LIBERI = False
# True = controllo completo di Chrome (schede, clic, lettura pagine...) tramite il
# "Chrome di Jarvis" (profilo dedicato). Vedi GUIDA, Fase 21.
CHROME_CONTROLLO = True
# ------------------------------------------------------------------------

SOGLIA = 0.90
APP_NOTE = {
    "chrome": "chrome", "google chrome": "chrome", "edge": "msedge", "steam": "steam://open/main",
    "esplora file": "explorer", "blocco note": "notepad", "calcolatrice": "calc",
    "impostazioni": "ms-settings:", "task manager": "taskmgr", "gestione attività": "taskmgr",
    "paint": "mspaint", "prompt dei comandi": "cmd", "word": "winword", "excel": "excel",
    "powerpoint": "powerpnt", "spotify": "spotify:", "discord": "discord:",
}


def log(t):
    print(time.strftime("[%H:%M:%S]"), t, flush=True)


def richiesta(percorso, dati=None, timeout=40):
    url = SERVER.rstrip("/") + percorso
    corpo = json.dumps(dati).encode("utf-8") if dati is not None else None
    req = urllib.request.Request(url, data=corpo, headers={
        "Content-Type": "application/json", "X-Token-Agente": TOKEN})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


# ------------------------------- AZIONI -------------------------------
def collegamenti_start():
    cartelle = [
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.expandvars(r"%Public%\Desktop"),
    ]
    trovati = {}
    for c in cartelle:
        for p in glob.glob(os.path.join(c, "**", "*.lnk"), recursive=True) + glob.glob(os.path.join(c, "**", "*.url"), recursive=True):
            trovati.setdefault(os.path.splitext(os.path.basename(p))[0].lower(), p)
    return trovati


def apri_app(nome):
    n = nome.lower().strip()
    if CHROME_CONTROLLO and n in ("chrome", "google chrome"):
        return chrome_controllo.esegui("apri", {})
    if n in APP_NOTE:
        os.startfile(APP_NOTE[n]) if ":" in APP_NOTE[n] else subprocess.Popen(f'start "" {APP_NOTE[n]}', shell=True)
        return f"{nome} aperto su {NOME}."
    link = collegamenti_start()
    if n in link:
        os.startfile(link[n])
        return f"{nome} aperto su {NOME}."
    simili = difflib.get_close_matches(n, list(link), n=3, cutoff=0.5)
    if simili and difflib.SequenceMatcher(None, n, simili[0]).ratio() >= SOGLIA:
        os.startfile(link[simili[0]])
        return f"{simili[0]} aperto su {NOME}."
    if simili:
        return f"Non sono sicuro al 90%. Intendevi: {', '.join(simili)}?"
    return f"Programma '{nome}' non trovato su {NOME}."


def apri_url(url, browser="chrome"):
    if CHROME_CONTROLLO and browser == "chrome":
        return chrome_controllo.esegui("vai", {"url": url, "nuova": True})
    if browser == "chrome":
        try:
            subprocess.Popen(f'start "" chrome "{url}"', shell=True)
            return f"Aperto in Chrome su {NOME}: {url}"
        except OSError:
            pass
    os.startfile(url)
    return f"Aperto su {NOME}: {url}"


def cerca(motore, testo):
    if CHROME_CONTROLLO:
        return chrome_controllo.esegui("cerca", {"testo": testo, "motore": motore})
    q = urllib.parse.quote_plus(testo)
    url = {"youtube": f"https://www.youtube.com/results?search_query={q}"}.get(
        motore, f"https://www.google.com/search?q={q}")
    apri_url(url)
    return f"Cerco '{testo}' su {'YouTube' if motore == 'youtube' else 'Google'}, su {NOME}."


def steam_scarica(gioco):
    url = ("https://store.steampowered.com/api/storesearch/?cc=it&l=italian&term="
           + urllib.parse.quote(gioco))
    with urllib.request.urlopen(url, timeout=20) as r:
        risultati = json.loads(r.read().decode("utf-8")).get("items", [])
    if not risultati:
        return f"Nessun gioco Steam trovato per '{gioco}'."
    nomi = [x["name"] for x in risultati]
    migliore = max(risultati, key=lambda x: difflib.SequenceMatcher(None, gioco.lower(), x["name"].lower()).ratio())
    somiglianza = difflib.SequenceMatcher(None, gioco.lower(), migliore["name"].lower()).ratio()
    if somiglianza < SOGLIA:
        return f"Non sono sicuro al 90% di quale gioco intendi. Risultati: {', '.join(nomi[:5])}."
    os.startfile(f"steam://install/{migliore['id']}")
    return (f"Steam: aperta l'installazione di {migliore['name']} su {NOME}. "
            "Se Steam chiede conferma, va premuto Avanti. I giochi non posseduti vanno prima acquistati.")


def screenshot():
    from PIL import ImageGrab

    img = ImageGrab.grab()
    img.thumbnail((1600, 1600))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return {"testo": f"Screenshot di {NOME}.", "immagine": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}


def esegui(azione, p):
    if azione == "apri_app":
        return apri_app(p["nome"])
    if azione == "cerca":
        return cerca(p.get("motore", "google"), p["testo"])
    if azione == "apri_url":
        return apri_url(p["url"])
    if azione == "steam_scarica":
        return steam_scarica(p["gioco"])
    if azione == "screenshot":
        return screenshot()
    if azione == "apri_uri":
        uri = p.get("uri", "")
        if not uri.startswith(("spotify:", "discord:", "steam:")):
            return "Indirizzo non permesso."
        os.startfile(uri)
        return "Aperto su " + NOME + "."
    if azione == "chrome":
        if not CHROME_CONTROLLO:
            return "Controllo di Chrome disattivato sul PC Msi (CHROME_CONTROLLO = False)."
        return chrome_controllo.esegui(p.get("op", ""), p)
    if azione == "blocca":
        ctypes.windll.user32.LockWorkStation()
        return f"{NOME} bloccato."
    if azione == "spegni":
        subprocess.Popen("shutdown /s /t 60", shell=True)
        return f"{NOME} si spegne tra 60 secondi. Per annullare: 'annulla spegnimento'."
    if azione == "riavvia":
        subprocess.Popen("shutdown /r /t 60", shell=True)
        return f"{NOME} si riavvia tra 60 secondi."
    if azione == "annulla_spegnimento":
        subprocess.Popen("shutdown /a", shell=True)
        return "Spegnimento annullato."
    if azione == "comando":
        if not COMANDI_LIBERI:
            return "Comandi liberi disattivati sul PC Msi (COMANDI_LIBERI = False)."
        r = subprocess.run(p["comando"], shell=True, capture_output=True, text=True, timeout=120)
        return (r.stdout + r.stderr)[-3000:] or "Eseguito."
    return f"Azione sconosciuta: {azione}"


def stato():
    info = {"nome": NOME, "host": socket.gethostname(), "sistema": platform.platform()}
    try:
        import psutil

        info.update(cpu=psutil.cpu_percent(interval=None), ram=psutil.virtual_memory().percent,
                    batteria=(psutil.sensors_battery().percent if psutil.sensors_battery() else None))
    except Exception:
        pass
    return info


def main():
    log(f"Agente {NOME} avviato. Server: {SERVER}")
    while True:
        try:
            r = richiesta("/api/agente/attesa", stato(), timeout=40)
            c = r.get("comando")
            if not c:
                continue
            log(f"Comando: {c['azione']} {c.get('parametri', {})}")
            try:
                esito = esegui(c["azione"], c.get("parametri", {}))
            except Exception as e:
                esito = f"Errore su {NOME}: {e}"
            if isinstance(esito, str):
                esito = {"testo": esito}
            richiesta("/api/agente/esito", {"id": c["id"], **esito})
        except urllib.error.HTTPError as e:
            log(f"Server ha risposto {e.code}. Token giusto? Riprovo tra 15 s.")
            time.sleep(15)
        except (urllib.error.URLError, OSError, TimeoutError):
            time.sleep(10)  # server spento o non raggiungibile (es. fuori casa)


if __name__ == "__main__":
    main()
