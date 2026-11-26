"""
Jarvis - Voce neurale offline con Piper (progetto open source su GitHub:
github.com/OHF-Voice/piper1-gpl, licenza GPL).

- Gira sul PC server, senza internet (tranne il primo download della voce).
- La voce viene scaricata da sola al primo uso nella cartella modelli/voci.
- L'audio e' mandato al browser (PC, telefono, Rabbit R1), che lo riproduce:
  stessa voce su tutti i dispositivi.
- EFFETTO_VOCE = "jarvis" aggiunge un leggero effetto metallico da assistente.

Voci italiane disponibili (config.VOCE_PIPER):
  it_IT-riccardo-x_low  maschile, qualita' bassa (28 MB)
  it_IT-paola-medium    femminile, qualita' media (63 MB)
  it_IT-serena-medium   femminile, qualita' media (64 MB)
  it_IT-serena-high     femminile, qualita' alta (114 MB)
"""

import hashlib
import io
import os
import threading
import wave

import config

CARTELLA = os.path.dirname(os.path.abspath(__file__))
CARTELLA_VOCI = os.path.join(CARTELLA, "modelli", "voci")
CARTELLA_CACHE = os.path.join(CARTELLA, "dati", "cache_voce")
MAX_CACHE = 300  # file audio tenuti in cache

_voce = None
_nome_caricato = None
_blocco = threading.Lock()


def disponibile():
    import importlib.util

    return importlib.util.find_spec("piper") is not None


def _carica():
    global _voce, _nome_caricato
    from piper import PiperVoice

    nome = getattr(config, "VOCE_PIPER", "it_IT-riccardo-x_low")
    if _voce is not None and _nome_caricato == nome:
        return _voce
    modello = os.path.join(CARTELLA_VOCI, nome + ".onnx")
    if not os.path.exists(modello) or not os.path.exists(modello + ".json"):
        os.makedirs(CARTELLA_VOCI, exist_ok=True)
        from pathlib import Path

        from piper.download_voices import download_voice

        print(f"Scarico la voce {nome} (solo la prima volta)...")
        download_voice(nome, Path(CARTELLA_VOCI))
    _voce = PiperVoice.load(modello)
    _nome_caricato = nome
    return _voce


def _effetto_jarvis(campioni, frequenza):
    """Leggero effetto metallico: due eco brevissimi (filtro a pettine) + normalizzazione."""
    import numpy as np

    x = campioni.astype(np.float32)
    y = x.copy()
    for ritardo_ms, guadagno in ((7, 0.35), (19, 0.18)):
        d = int(frequenza * ritardo_ms / 1000)
        y[d:] += guadagno * x[:-d]
    picco = float(np.max(np.abs(y))) or 1.0
    return (y / picco * 30000).astype(np.int16)


def sintetizza(testo):
    """Restituisce i byte di un file WAV con il testo detto dalla voce di Jarvis."""
    testo = (testo or "").strip()[:1500]
    if not testo:
        raise ValueError("Testo vuoto")
    nome = getattr(config, "VOCE_PIPER", "it_IT-riccardo-x_low")
    effetto = getattr(config, "EFFETTO_VOCE", "jarvis")
    velocita = float(getattr(config, "VELOCITA_PIPER", 1.0))
    chiave = hashlib.sha1(f"{nome}|{effetto}|{velocita}|{testo}".encode("utf-8")).hexdigest()
    os.makedirs(CARTELLA_CACHE, exist_ok=True)
    in_cache = os.path.join(CARTELLA_CACHE, chiave + ".wav")
    if os.path.exists(in_cache):
        with open(in_cache, "rb") as f:
            return f.read()

    import numpy as np
    from piper import SynthesisConfig

    with _blocco:
        voce = _carica()
        grezzo = io.BytesIO()
        with wave.open(grezzo, "wb") as w:
            voce.synthesize_wav(testo, w, syn_config=SynthesisConfig(length_scale=velocita))
    grezzo.seek(0)
    with wave.open(grezzo, "rb") as r:
        frequenza = r.getframerate()
        campioni = np.frombuffer(r.readframes(r.getnframes()), dtype=np.int16)
    if effetto == "jarvis":
        campioni = _effetto_jarvis(campioni, frequenza)
    uscita = io.BytesIO()
    with wave.open(uscita, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(frequenza)
        w.writeframes(campioni.tobytes())
    dati = uscita.getvalue()
    with open(in_cache, "wb") as f:
        f.write(dati)
    _pulisci_cache()
    return dati


def _pulisci_cache():
    file = sorted((os.path.join(CARTELLA_CACHE, n) for n in os.listdir(CARTELLA_CACHE)), key=os.path.getmtime)
    for p in file[:-MAX_CACHE]:
        try:
            os.remove(p)
        except OSError:
            pass
