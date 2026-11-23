"""
Jarvis - Lettura dei messaggi registrati dalla segreteria WhatsApp.

La segreteria (cartella "whatsapp") salva i messaggi in dati\\messaggi_whatsapp.json.
Questo modulo li legge; i messaggi gia' riferiti vengono annotati in
dati\\whatsapp_letti.json (file separato, cosi' non si interferisce con la segreteria).
"""

import json
import os
from datetime import datetime

CARTELLA = os.path.dirname(os.path.abspath(__file__))
CARTELLA_DATI = os.path.join(CARTELLA, "dati")
CARTELLA_VOCALI = os.path.join(CARTELLA_DATI, "vocali")
FILE_MESSAGGI = os.path.join(CARTELLA_DATI, "messaggi_whatsapp.json")
FILE_LETTI = os.path.join(CARTELLA_DATI, "whatsapp_letti.json")


def _leggi_json(percorso, predefinito):
    try:
        with open(percorso, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return predefinito


def _data_locale(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone().strftime(
            "%d/%m/%Y alle %H:%M"
        )
    except (AttributeError, ValueError):
        return str(iso)


def tutti():
    """Tutte le registrazioni, dalla piu' vecchia alla piu' recente."""
    return _leggi_json(FILE_MESSAGGI, [])


def nuovi():
    """Registrazioni non ancora riferite (anche quelle ancora in corso)."""
    letti = set(_leggi_json(FILE_LETTI, []))
    return [r for r in tutti() if r.get("id") not in letti]


def segna_letti(registrazioni):
    """Segna come riferite solo le registrazioni completate."""
    letti = set(_leggi_json(FILE_LETTI, []))
    letti.update(r["id"] for r in registrazioni if r.get("stato") == "completato")
    os.makedirs(CARTELLA_DATI, exist_ok=True)
    tmp = FILE_LETTI + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sorted(letti), f)
    os.replace(tmp, FILE_LETTI)


def percorso_vocale(nome_file):
    return os.path.join(CARTELLA_VOCALI, nome_file)


def descrivi(reg, vocali_precedenti=0):
    """
    Restituisce (testo_da_mostrare, testo_da_leggere_ad_alta_voce, lista_file_vocali).
    """
    chi = reg.get("contatto", "Sconosciuto")
    quando = _data_locale(reg.get("inizio"))
    origine = reg.get("origine", "messaggio")
    intestazione = f"{chi} - {quando}"
    if origine != "messaggio":
        intestazione += f" ({origine})"
    if reg.get("stato") != "completato":
        intestazione += " [sta ancora scrivendo]"
    elif reg.get("chiuso_con") == "inattività":
        intestazione += " [non ha premuto 1]"

    righe, parlato, vocali = [intestazione], [], []
    for elemento in reg.get("contenuti", []):
        c = elemento.get("contenuto")
        if isinstance(c, dict) and c.get("vocale"):
            vocali.append(percorso_vocale(c["vocale"]))
            righe.append(f"   [Messaggio vocale n. {vocali_precedenti + len(vocali)}]")
            parlato.append("un messaggio vocale")
        else:
            righe.append(f"   {c}")
            parlato.append(str(c))

    if not reg.get("contenuti"):
        righe.append("   (nessun messaggio scritto)")

    if "chiamata" in origine:
        testo_voce = f"{chi} ti ha chiamato su WhatsApp."
        if parlato:
            testo_voce += " Ha lasciato detto: " + ". ".join(parlato)
    else:
        testo_voce = f"{chi} ha detto: " + (". ".join(parlato) or "niente")
    return "\n".join(righe), testo_voce, vocali
