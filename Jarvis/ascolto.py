"""
JARVIS - Attivazione vocale.

Ascolta il microfono del PC (tutto in locale, gratis, senza internet) e quando
senti la frase "Jarvis attivazione" apre il pannello di Jarvis.

Riconoscimento vocale: Vosk + modello italiano piccolo (circa 50 MB), scaricato
automaticamente al primo avvio nella cartella "modelli".
"""

import json
import os
import queue
import subprocess
import sys
import time
import urllib.request
import webbrowser
import zipfile

import config

CARTELLA = os.path.dirname(os.path.abspath(__file__))
CARTELLA_MODELLI = os.path.join(CARTELLA, "modelli")
NOME_MODELLO = "vosk-model-small-it-0.22"
URL_MODELLO = f"https://alphacephei.com/vosk/models/{NOME_MODELLO}.zip"
PROFILO_BROWSER = os.path.join(CARTELLA, "dati", "browser_jarvis")
PAUSA_TRA_ATTIVAZIONI = 10  # secondi

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
    print("Scarico il modello vocale italiano (circa 50 MB, solo la prima volta)...")
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
        print(f'Jarvis in ascolto. Di\' "{config.FRASE_ATTIVAZIONE}" per aprire il pannello.')
        print("Lascia aperta questa finestra. Ctrl+C per fermare.")
        while True:
            dati = coda.get()
            if riconoscitore.AcceptWaveform(dati):
                testo = json.loads(riconoscitore.Result()).get("text", "")
                if frase in testo and time.time() - ultima > PAUSA_TRA_ATTIVAZIONI:
                    ultima = time.time()
                    print(time.strftime("[%H:%M:%S]"), "Attivazione riconosciuta: apro il pannello.")
                    apri_pannello()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAscolto fermato.")
