"""
Jarvis - Foto e video: caricati dal pannello o fatti al momento con la fotocamera.

Ogni foto/video ha una DESCRIZIONE scritta da te (es. "targa della moto",
"lavagna di fisica del 26/11"): Jarvis la impara come fatto, quindi puoi
chiedere "mostrami la foto della targa" e ritrovarla.
I file restano sul PC server, nella cartella dati/media.
"""

import json
import os
import re
import threading
import time
from datetime import datetime

CARTELLA = os.path.dirname(os.path.abspath(__file__))
CARTELLA_MEDIA = os.path.join(CARTELLA, "dati", "media")
FILE_INDICE = os.path.join(CARTELLA, "dati", "media.json")
FORMATI = {
    ".jpg": "foto", ".jpeg": "foto", ".png": "foto", ".webp": "foto", ".gif": "foto", ".heic": "foto",
    ".mp4": "video", ".webm": "video", ".mov": "video", ".m4v": "video", ".3gp": "video",
}
MAX_MB = {"foto": 25, "video": 200}
_blocco = threading.Lock()


def _leggi():
    try:
        with open(FILE_INDICE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _scrivi(lista):
    os.makedirs(os.path.dirname(FILE_INDICE), exist_ok=True)
    tmp = FILE_INDICE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=1)
    os.replace(tmp, FILE_INDICE)


def elenco():
    return list(reversed(_leggi()))


def percorso(file):
    """Percorso sicuro di un file media (solo nomi generati da Jarvis)."""
    if not re.fullmatch(r"\d+\.[a-z0-9]+", file or ""):
        raise ValueError("Nome file non valido")
    return os.path.join(CARTELLA_MEDIA, file)


def aggiungi(nome_originale, flusso, descrizione):
    est = os.path.splitext(nome_originale or "")[1].lower()
    tipo = FORMATI.get(est)
    if not tipo:
        raise ValueError(f"Formato non supportato ({est or 'nessuno'}). Foto: jpg, png, webp, gif, heic. Video: mp4, webm, mov.")
    os.makedirs(CARTELLA_MEDIA, exist_ok=True)
    id_media = str(int(time.time() * 1000))
    file = id_media + est
    dest = percorso(file)
    limite = MAX_MB[tipo] * 1024 * 1024
    scritti = 0
    with open(dest, "wb") as f:
        while True:
            pezzo = flusso.read(1024 * 1024)
            if not pezzo:
                break
            scritti += len(pezzo)
            if scritti > limite:
                f.close()
                os.remove(dest)
                raise ValueError(f"File troppo grande: massimo {MAX_MB[tipo]} MB per {tipo}.")
            f.write(pezzo)
    voce = {"id": id_media, "file": file, "tipo": tipo, "descrizione": descrizione.strip(),
            "kb": round(scritti / 1024), "ora": datetime.now().isoformat(timespec="minutes")}
    with _blocco:
        lista = _leggi()
        lista.append(voce)
        _scrivi(lista)
    return voce


def trova(id_media):
    return next((m for m in _leggi() if m["id"] == id_media), None)


def elimina(id_media):
    with _blocco:
        lista = _leggi()
        m = next((x for x in lista if x["id"] == id_media), None)
        if not m:
            return None
        _scrivi([x for x in lista if x["id"] != id_media])
    try:
        os.remove(percorso(m["file"]))
    except OSError:
        pass
    return m


def cerca(testo, soglia=0.9):
    """Media la cui descrizione contiene almeno il 90% delle parole cercate."""
    from comandi import normalizza

    parole = [p for p in normalizza(testo).split() if len(p) > 2 and p not in
              ("foto", "video", "della", "dello", "delle", "degli", "mostrami", "mostra", "fammi", "vedere", "che", "con", "sul", "sulla")]
    if not parole:
        return []
    trovati = []
    for m in elenco():
        d = normalizza(m["descrizione"])
        quota = sum(1 for p in parole if p[:5] in d) / len(parole)
        if quota >= soglia:
            trovati.append(m)
    return trovati
