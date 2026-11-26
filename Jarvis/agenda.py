"""
Jarvis - Agenda unificata: Google Calendar + ClasseViva (compiti, verifiche, annotazioni).

- prossimi(): cosa c'e' nei prossimi giorni, in ordine di data.
- nuovi(): impegni comparsi da poco che Jarvis non ti ha ancora detto.
  Il rapporto e il riepilogo te li dicono PRIMA di tutto il resto.
"""

import json
import os
import threading
from datetime import datetime

CARTELLA = os.path.dirname(os.path.abspath(__file__))
FILE_STATO = os.path.join(CARTELLA, "dati", "agenda_stato.json")
_blocco = threading.Lock()


def _stato():
    try:
        with open(FILE_STATO, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"conosciuti": [], "riferiti": [], "notificati": [], "fonti_viste": []}


def _salva(s):
    os.makedirs(os.path.dirname(FILE_STATO), exist_ok=True)
    for k in ("conosciuti", "riferiti", "notificati"):
        s[k] = s[k][-3000:]
    with open(FILE_STATO, "w", encoding="utf-8") as f:
        json.dump(s, f)


def prossimi(giorni=7):
    """Restituisce (impegni, avvisi)."""
    impegni, avvisi = [], []
    try:
        import gmail_reader

        if os.path.exists(os.path.join(CARTELLA, "token.json")):
            for e in gmail_reader.eventi_prossimi(giorni):
                impegni.append({"id": "gc-" + e["id"], "fonte": "Calendario", "quando": e["inizio"],
                                "titolo": e["titolo"], "dettaglio": e.get("luogo", "")})
    except Exception as e:
        avvisi.append(f"Calendario: {e}")
    try:
        import classeviva

        if classeviva.configurato():
            for e in classeviva.agenda(giorni):
                etichetta = {"compito": "Compito", "verifica": "Verifica", "annotazione": "Agenda"}[e["tipo"]]
                impegni.append({"id": e["id"], "fonte": "ClasseViva", "quando": e["inizio"],
                                "titolo": f"{etichetta} {e['materia']}".strip(), "dettaglio": e["testo"][:300],
                                "tipo": e["tipo"]})
    except Exception as e:
        avvisi.append(f"ClasseViva: {e}")
    impegni.sort(key=lambda x: x["quando"] or "")
    return impegni, avvisi


def _aggiorna_conosciuti(impegni):
    """Registra gli impegni mai visti. La PRIMA volta che una fonte (Calendario, ClasseViva) viene letta,
    i suoi impegni gia' esistenti non sono 'nuovi': si evita una valanga di avvisi al collegamento."""
    with _blocco:
        s = _stato()
        fonti_viste = set(s.get("fonti_viste", []))
        conosciuti = set(s["conosciuti"])
        nuovi = [i for i in impegni if i["id"] not in conosciuti]
        gia_esistenti = [i["id"] for i in nuovi if i["fonte"] not in fonti_viste]
        s["riferiti"] += gia_esistenti
        s["notificati"] += gia_esistenti
        s["conosciuti"] += [i["id"] for i in nuovi]
        s["fonti_viste"] = sorted(fonti_viste | {i["fonte"] for i in impegni})
        _salva(s)
        return s


def da_notificare(giorni=14):
    """Impegni nuovi non ancora notificati (per l'avviso immediato). Li segna come notificati."""
    impegni, _ = prossimi(giorni)
    s = _aggiorna_conosciuti(impegni)
    gia = set(s["notificati"])
    nuovi = [i for i in impegni if i["id"] not in gia]
    if nuovi:
        with _blocco:
            s = _stato()
            s["notificati"] += [i["id"] for i in nuovi]
            _salva(s)
    return nuovi


def nuovi_da_riferire(giorni=14, segna=True):
    """Impegni nuovi che il rapporto non ti ha ancora detto (vanno detti per primi)."""
    impegni, _ = prossimi(giorni)
    s = _aggiorna_conosciuti(impegni)
    gia = set(s["riferiti"])
    nuovi = [i for i in impegni if i["id"] not in gia]
    if segna and nuovi:
        with _blocco:
            s = _stato()
            s["riferiti"] += [i["id"] for i in nuovi]
            _salva(s)
    return nuovi


def quando_leggibile(iso):
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if d.tzinfo:
            d = d.astimezone()
    except ValueError:
        return iso
    giorni = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
    oggi = datetime.now().date()
    differenza = (d.date() - oggi).days
    giorno = "oggi" if differenza == 0 else "domani" if differenza == 1 else f"{giorni[d.weekday()]} {d:%d/%m}"
    ora = "" if (d.hour, d.minute) == (0, 0) or len(iso) <= 10 else f" alle {d:%H:%M}"
    return giorno + ora


def frase(impegno):
    testo = f"{quando_leggibile(impegno['quando'])}: {impegno['titolo']}"
    if impegno.get("dettaglio"):
        testo += f" ({impegno['dettaglio'][:120]})"
    return testo
