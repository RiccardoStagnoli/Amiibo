"""
JARVIS - Attivazione vocale.

Ascolta il microfono del PC (tutto in locale, gratis, senza internet) e quando
senti la frase "Jarvis attivazione" apre il pannello di Jarvis.
Subito dopo resta in ascolto per SECONDI_COMANDO secondi: se dici un comando
(es. "apri chrome e cerca youtube") lo invia a Jarvis, che risponde a voce
dal pannello.

Riconoscimento vocale: Vosk + modello italiano piccolo (circa 50 MB), scaricato
automaticamente al primo avvio nella cartella "modelli".
"""

import json
import os
import queue
import re
import subprocess
import sys
import time
import urllib.request
import webbrowser
import zipfile

import config

CARTELLA = os.path.dirname(os.path.abspath(__file__))
CARTELLA_MODELLI = os.path.join(CARTELLA, "modelli")
NOME_MODELLO = getattr(config, "MODELLO_VOSK", "vosk-model-small-it-0.22")
URL_MODELLO = f"https://alphacephei.com/vosk/models/{NOME_MODELLO}.zip"
PROFILO_BROWSER = os.path.join(CARTELLA, "dati", "browser_jarvis")
PAUSA_TRA_ATTIVAZIONI = 10  # secondi
SECONDI_COMANDO = 7
FILE_TOKEN = os.path.join(CARTELLA, "dati", ".token_interno")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass


def prepara_modello():
    percorso = os.path.join(CARTELLA_MODELLI, NOME_MODELLO)
    if os.path.isdir(percorso):
        return percorso
    os.makedirs(CARTELLA_MODELLI, exist_ok=True)
    zip_locale = os.path.join(CARTELLA_MODELLI, NOME_MODELLO + ".zip")
    print(f"Scarico il modello vocale {NOME_MODELLO} (solo la prima volta, puo' richiedere tempo)...")
    urllib.request.urlretrieve(URL_MODELLO, zip_locale)
    with zipfile.ZipFile(zip_locale) as z:
        z.extractall(CARTELLA_MODELLI)
    os.remove(zip_locale)
    return percorso


def trova_browser():
    candidati = {
        "edge": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ],
    }
    ordine = [config.BROWSER] + [b for b in candidati if b != config.BROWSER]
    for nome in ordine:
        for p in candidati.get(nome, []):
            if os.path.exists(p):
                return p
    return None


def apri_pannello():
    url = f"http://localhost:{config.PORTA_PANNELLO}/?attivazione=1"
    browser = trova_browser()
    if browser:
        os.makedirs(PROFILO_BROWSER, exist_ok=True)
        subprocess.Popen([
            browser,
            f"--app={url}",
            f"--user-data-dir={PROFILO_BROWSER}",
            "--autoplay-policy=no-user-gesture-required",
            "--start-maximized",
            "--no-first-run",
        ])
    else:
        webbrowser.open(url)


def _token_interno():
    with open(FILE_TOKEN, encoding="utf-8") as f:
        return f.read().strip()


def _post(percorso, dati, timeout=120):
    req = urllib.request.Request(
        f"http://127.0.0.1:{config.PORTA_PANNELLO}{percorso}", data=json.dumps(dati).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Token-Interno": _token_interno()})
    return urllib.request.urlopen(req, timeout=timeout)


def invia_comando(testo, annuncia=False):
    """Manda il comando al server e restituisce la risposta (dizionario)."""
    try:
        with _post("/api/comando", {"testo": testo, "annuncia": annuncia}) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"testo": f"Il server di Jarvis non risponde: {e}", "esito": "errore"}


def per_la_voce(testo):
    """Testo adatto a essere detto: niente elenchi di estratti, lunghezza limitata."""
    t = str(testo or "")
    if t.startswith("(Ollama"):
        m = re.search(r"\[1\][^\n]*\n([\s\S]*?)(\n\[2\]|$)", t)
        t = "Ecco cosa dicono le mie fonti. " + (m.group(1) if m else "")
    t = re.sub(r"\[\d+\]", "", t)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > 600:
        t = t[:600]
        t = t[: max(t.rfind(". "), 300) + 1]
    return t


def suona_bip(frequenza=880, durata=0.12):
    try:
        import numpy as np
        import sounddevice as sd

        x = np.linspace(0, durata, int(22050 * durata), False)
        onda = (np.sin(2 * np.pi * frequenza * x) * np.hanning(len(x)) * 0.3).astype(np.float32)
        sd.play(onda, 22050)
        sd.wait()
    except Exception:
        pass


def parla_locale(testo):
    """Jarvis risponde a voce dalle casse del PC server (voce Piper; ripiego: voce di Windows)."""
    testo = per_la_voce(testo)
    if not testo:
        return
    print("Jarvis:", testo)
    try:
        import io
        import wave

        import numpy as np
        import sounddevice as sd

        with _post("/api/voce", {"testo": testo}, timeout=60) as r:
            dati = r.read()
        with wave.open(io.BytesIO(dati), "rb") as w:
            frequenza = w.getframerate()
            campioni = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        sd.play(campioni, frequenza)
        sd.wait()
    except Exception:
        try:
            import voce

            voce.parla(testo)
        except Exception as e:
            print("Voce non disponibile:", e)


def ascolta_comando(coda, modello, secondi=None):
    """Riconoscimento libero (tutte le parole): si ferma alla fine della frase o dopo 'secondi'."""
    from vosk import KaldiRecognizer

    libero = KaldiRecognizer(modello, 16000)
    fine = time.time() + (secondi or SECONDI_COMANDO)
    parti = []
    while time.time() < fine:
        try:
            dati = coda.get(timeout=0.5)
        except queue.Empty:
            continue
        if libero.AcceptWaveform(dati):
            t = json.loads(libero.Result()).get("text", "")
            if t:
                parti.append(t)
                break  # frase completa
    if not parti:
        parti.append(json.loads(libero.FinalResult()).get("text", ""))
    return " ".join(p for p in parti if p).strip()


def svuota(coda):
    """Butta l'audio registrato mentre Jarvis parlava (cosi' non sente se stesso)."""
    try:
        while True:
            coda.get_nowait()
    except queue.Empty:
        pass


def gestisci_attivazione(coda, modello):
    """Come Alexa: bip, 'Si'?', comando, risposta a voce, poi qualche secondo per una domanda successiva."""
    risposta_locale = getattr(config, "RISPOSTA_VOCALE_SERVER", True)
    if getattr(config, "APRI_PANNELLO_CON_ATTIVAZIONE", False):
        apri_pannello()
    suona_bip()
    if risposta_locale and getattr(config, "RISPONDI_SI", True):
        parla_locale("Sì?")
    svuota(coda)
    primo = True
    while True:
        print("Ti ascolto...")
        comando = ascolta_comando(coda, modello, SECONDI_COMANDO if primo else getattr(config, "SECONDI_CONVERSAZIONE", 6))
        if not comando:
            if primo and risposta_locale:
                parla_locale("Non ho sentito niente.")
            suona_bip(660)
            svuota(coda)
            return
        print("Comando sentito:", comando)
        if re.fullmatch(r"(basta|grazie|niente|stop|fine|ok grazie|a posto)( jarvis)?", comando):
            suona_bip(660)
            return
        r = invia_comando(comando, annuncia=not risposta_locale)
        if r.get("azione_pannello") == "rapporto":
            r = invia_comando("riepilogo", annuncia=not risposta_locale)
        elif r.get("azione_pannello") and not getattr(config, "APRI_PANNELLO_CON_ATTIVAZIONE", False):
            apri_pannello()  # risultati da guardare (foto, guide, compiti...)
        if risposta_locale:
            parla_locale(r.get("testo", ""))
        else:
            print("Jarvis:", r.get("testo"))
        svuota(coda)
        primo = False
        if not getattr(config, "CONVERSAZIONE_CONTINUA", True):
            return
        suona_bip(1046, 0.08)  # segnale: puoi fare un'altra domanda senza ripetere "Jarvis attivazione"


def main():
    try:
        import sounddevice as sd
        from vosk import KaldiRecognizer, Model, SetLogLevel
    except ImportError:
        print("Librerie mancanti: fai doppio clic su installa.bat")
        input("Premi Invio per chiudere...")
        return

    SetLogLevel(-1)
    frase = config.FRASE_ATTIVAZIONE.lower().strip()
    parole = frase.split()
    # Vocabolario ristretto: il riconoscitore cerca solo queste parole.
    grammatica = json.dumps([frase] + parole + ["[unk]"])
    modello = Model(prepara_modello())
    riconoscitore = KaldiRecognizer(modello, 16000, grammatica)

    coda = queue.Queue()

    def ricevi_audio(dati, _frames, _tempo, stato):
        if stato:
            print(stato, file=sys.stderr)
        coda.put(bytes(dati))

    ultima = 0.0
    with sd.RawInputStream(
        samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=ricevi_audio
    ):
        print(f'Jarvis in ascolto. Di\' "{config.FRASE_ATTIVAZIONE}" e poi il comando, come con Alexa.')
        print("Lascia aperta questa finestra. Ctrl+C per fermare.")
        while True:
            dati = coda.get()
            if riconoscitore.AcceptWaveform(dati):
                testo = json.loads(riconoscitore.Result()).get("text", "")
                if frase in testo and time.time() - ultima > PAUSA_TRA_ATTIVAZIONI:
                    print(time.strftime("[%H:%M:%S]"), "Attivazione riconosciuta.")
                    gestisci_attivazione(coda, modello)
                    ultima = time.time()
                    riconoscitore = KaldiRecognizer(modello, 16000, grammatica)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAscolto fermato.")
