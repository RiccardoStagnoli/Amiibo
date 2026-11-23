"""
Jarvis - Funzioni aggiuntive:
  - promemoria a tempo ("ricordami tra 20 minuti di ...", "ricordami alle 18 di ...")
  - note veloci ("annota ...", "leggi le note", "cancella le note")
  - accensione del PC Msi via rete (Wake-on-LAN)
  - registro attivita' (comandi eseguiti e accessi al pannello)
"""

import json
import os
import re
import socket
import threading
import time
from datetime import datetime, timedelta

CARTELLA = os.path.dirname(os.path.abspath(__file__))
CARTELLA_DATI = os.path.join(CARTELLA, "dati")
FILE_PROMEMORIA = os.path.join(CARTELLA_DATI, "promemoria.json")
FILE_NOTE = os.path.join(CARTELLA_DATI, "note.json")
FILE_REGISTRO = os.path.join(CARTELLA_DATI, "registro.jsonl")
_blocco = threading.Lock()


def _leggi(percorso, predefinito):
    try:
        with open(percorso, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return predefinito


def _scrivi(percorso, dati):
    os.makedirs(CARTELLA_DATI, exist_ok=True)
    tmp = percorso + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=1)
    os.replace(tmp, percorso)


# =============================== PROMEMORIA ===============================
NUMERI = {"un": 1, "uno": 1, "una": 1, "un'": 1, "due": 2, "tre": 3, "quattro": 4, "cinque": 5, "sei": 6,
          "sette": 7, "otto": 8, "nove": 9, "dieci": 10, "quindici": 15, "venti": 20, "trenta": 30,
          "quaranta": 40, "mezz'": 0.5, "mezza": 0.5}


def _numero(t):
    t = t.strip().lower()
    if re.fullmatch(r"\d+([.,]\d+)?", t):
        return float(t.replace(",", "."))
    return NUMERI.get(t)


def interpreta_quando(testo, adesso=None):
    """
    Riconosce: 'tra 20 minuti', 'tra un'ora', 'tra 2 ore', 'tra mezz'ora',
    'alle 18', 'alle 18:30', 'domani alle 8', 'domani alle 8 e 15'.
    Restituisce (datetime, testo_rimanente) oppure (None, testo).
    """
    adesso = adesso or datetime.now()
    t = testo.strip()
    m = re.match(r"^(?:tra|fra)\s+(un'|mezz'|\S+)\s*(minut[oi]|or[ae]|secondi)\s*(?:di|che|a|:)?\s*(.*)$", t, re.I)
    if m:
        n = _numero(m.group(1))
        if n is None:
            return None, testo
        unita = m.group(2).lower()
        delta = timedelta(minutes=n) if unita.startswith("minut") else (
            timedelta(hours=n) if unita.startswith("or") else timedelta(seconds=n))
        return adesso + delta, m.group(3).strip()
    m = re.match(r"^(domani\s+)?alle\s+(\d{1,2})(?:[:.](\d{2})|\s+e\s+(\d{1,2}))?\s*(?:di|che|a|:)?\s*(.*)$", t, re.I)
    if m:
        ora, minuti = int(m.group(2)), int(m.group(3) or m.group(4) or 0)
        if ora > 23 or minuti > 59:
            return None, testo
        quando = adesso.replace(hour=ora, minute=minuti, second=0, microsecond=0)
        if m.group(1):
            quando += timedelta(days=1)
        elif quando <= adesso:
            quando += timedelta(days=1)  # orario gia' passato: domani
        return quando, m.group(5).strip()
    return None, testo


def aggiungi_promemoria(quando, testo):
    with _blocco:
        lista = _leggi(FILE_PROMEMORIA, [])
        p = {"id": f"{int(time.time() * 1000)}", "quando": quando.isoformat(timespec="minutes"), "testo": testo}
        lista.append(p)
        _scrivi(FILE_PROMEMORIA, lista)
    return p


def promemoria():
    return sorted(_leggi(FILE_PROMEMORIA, []), key=lambda p: p["quando"])


def cancella_promemoria(tutti=True):
    with _blocco:
        _scrivi(FILE_PROMEMORIA, [])


def promemoria_scaduti(adesso=None):
    """Toglie dalla lista e restituisce i promemoria arrivati a scadenza."""
    adesso = adesso or datetime.now()
    with _blocco:
        lista = _leggi(FILE_PROMEMORIA, [])
        scaduti = [p for p in lista if datetime.fromisoformat(p["quando"]) <= adesso]
        if scaduti:
            _scrivi(FILE_PROMEMORIA, [p for p in lista if p not in scaduti])
    return scaduti


# ================================== NOTE ==================================
def aggiungi_nota(testo):
    with _blocco:
        note = _leggi(FILE_NOTE, [])
        note.append({"ora": datetime.now().isoformat(timespec="minutes"), "testo": testo})
        _scrivi(FILE_NOTE, note)
    return len(note)


def note():
    return _leggi(FILE_NOTE, [])


def cancella_note():
    with _blocco:
        _scrivi(FILE_NOTE, [])


# ============================== WAKE-ON-LAN ==============================
def wake_on_lan(mac, broadcast="255.255.255.255"):
    """Invia il 'pacchetto magico' che accende un PC con Wake-on-LAN attivo."""
    pulito = re.sub(r"[^0-9a-fA-F]", "", mac or "")
    if len(pulito) != 12:
        raise ValueError("Indirizzo MAC non valido (servono 12 cifre esadecimali, es. 1C:2B:3D:4E:5F:60).")
    pacchetto = bytes.fromhex("FF" * 6 + pulito * 16)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for porta in (9, 7):
            s.sendto(pacchetto, (broadcast, porta))
    return True


# ================================ REGISTRO ================================
def registra(tipo, dettaglio, ip=""):
    riga = {"ora": datetime.now().isoformat(timespec="seconds"), "tipo": tipo, "dettaglio": str(dettaglio)[:300], "ip": ip}
    with _blocco:
        os.makedirs(CARTELLA_DATI, exist_ok=True)
        with open(FILE_REGISTRO, "a", encoding="utf-8") as f:
            f.write(json.dumps(riga, ensure_ascii=False) + "\n")
        # tiene il file sotto ~1 MB
        if os.path.getsize(FILE_REGISTRO) > 1_000_000:
            with open(FILE_REGISTRO, encoding="utf-8") as f:
                righe = f.readlines()[-2000:]
            with open(FILE_REGISTRO, "w", encoding="utf-8") as f:
                f.writelines(righe)


def registro(n=100):
    try:
        with open(FILE_REGISTRO, encoding="utf-8") as f:
            righe = f.readlines()[-n:]
        return [json.loads(r) for r in reversed(righe)]
    except (OSError, ValueError):
        return []
