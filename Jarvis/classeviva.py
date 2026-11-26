"""
Jarvis - ClasseViva (registro elettronico Spaggiari).

ClasseViva non ha un'API pubblica ufficiale. Jarvis usa l'interfaccia delle app
ClasseViva, documentata dalla community (non ufficiale): puo' cambiare senza preavviso.
Si usano SOLO le tue credenziali, salvate sul PC server in dati/.classeviva.json.

Legge: agenda (compiti "AGHW", verifiche/annotazioni "AGNT"), cosi' Jarvis puo'
- dirti i compiti e preparare le bozze (come per Teams, ma SENZA invio: ClasseViva non lo permette);
- avvisarti dei nuovi impegni in agenda.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

import config

CARTELLA = os.path.dirname(os.path.abspath(__file__))
FILE_CREDENZIALI = os.path.join(CARTELLA, "dati", ".classeviva.json")
_sessione = {"token": None, "scade": 0, "studente": None}


class ErroreClasseViva(Exception):
    pass


def _base():
    return getattr(config, "CLASSEVIVA_API", "https://web.spaggiari.eu/rest/v1").rstrip("/")


def _intestazioni():
    return {
        "User-Agent": getattr(config, "CLASSEVIVA_USER_AGENT", "CVVS/std/4.1.7 Android/10"),
        "Z-Dev-Apikey": getattr(config, "CLASSEVIVA_APIKEY", "Tg1NWEwNGIgIC0K"),
        "Content-Type": "application/json",
    }


def configurato():
    return os.path.exists(FILE_CREDENZIALI)


def salva_credenziali(utente, password):
    utente, password = (utente or "").strip(), password or ""
    if not utente or not password:
        raise ErroreClasseViva("Servono codice utente (o email) e password di ClasseViva.")
    os.makedirs(os.path.dirname(FILE_CREDENZIALI), exist_ok=True)
    with open(FILE_CREDENZIALI, "w", encoding="utf-8") as f:
        json.dump({"utente": utente, "password": password}, f)
    _sessione.update(token=None, scade=0)
    try:
        return accedi()
    except ErroreClasseViva:
        os.remove(FILE_CREDENZIALI)
        raise


def elimina_credenziali():
    if os.path.exists(FILE_CREDENZIALI):
        os.remove(FILE_CREDENZIALI)
    _sessione.update(token=None, scade=0, studente=None)


def _richiesta(metodo, percorso, dati=None, token=None):
    intest = _intestazioni()
    if token:
        intest["Z-Auth-Token"] = token
    corpo = json.dumps(dati).encode("utf-8") if dati is not None else None
    req = urllib.request.Request(_base() + percorso, data=corpo, method=metodo, headers=intest)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        if e.code in (401, 422):
            raise ErroreClasseViva("ClasseViva: credenziali non valide o accesso rifiutato.")
        raise ErroreClasseViva(f"ClasseViva ha risposto con errore {e.code} (l'interfaccia non ufficiale potrebbe essere cambiata).")
    except urllib.error.URLError as e:
        raise ErroreClasseViva(f"ClasseViva non raggiungibile: {e.reason}")


def accedi():
    if not configurato():
        raise ErroreClasseViva("ClasseViva non collegato: inserisci le credenziali nella sezione Compiti (GUIDA, Fase 26).")
    with open(FILE_CREDENZIALI, encoding="utf-8") as f:
        cred = json.load(f)
    r = _richiesta("POST", "/auth/login", {"ident": None, "pass": cred["password"], "uid": cred["utente"]})
    if not r.get("token"):
        raise ErroreClasseViva("ClasseViva: accesso non riuscito.")
    ident = r.get("ident", "")
    studente = re.sub(r"\D", "", ident) or ident
    _sessione.update(token=r["token"], scade=time.time() + 80 * 60, studente=studente)
    return {"utente": ident, "nome": f"{r.get('firstName', '')} {r.get('lastName', '')}".strip()}


def _token():
    if not _sessione["token"] or time.time() > _sessione["scade"]:
        accedi()
    return _sessione["token"], _sessione["studente"]


def agenda(giorni=14, da=None):
    """Eventi dell'agenda da oggi (o 'da') per 'giorni' giorni."""
    token, studente = _token()
    inizio = da or date.today()
    fine = inizio + timedelta(days=giorni)
    r = _richiesta("GET", f"/students/{studente}/agenda/all/{inizio:%Y%m%d}/{fine:%Y%m%d}", token=token)
    eventi = []
    for e in r.get("agenda", []):
        codice = e.get("evtCode", "")
        tipo = "compito" if codice == "AGHW" else ("verifica" if re.search(r"verific|compito in classe|interrogaz", e.get("notes", ""), re.I) else "annotazione")
        eventi.append({
            "id": f"cv-{e.get('evtId')}", "tipo": tipo, "inizio": e.get("evtDatetimeBegin"),
            "materia": e.get("subjectDesc") or "", "docente": e.get("authorName") or "",
            "testo": (e.get("notes") or "").strip(), "classe": e.get("classDesc") or "",
        })
    eventi.sort(key=lambda x: x["inizio"] or "")
    return eventi


def compiti(giorni=14):
    return [e for e in agenda(giorni) if e["tipo"] == "compito"]


def quando_leggibile(iso):
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        giorni = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
        return f"{giorni[d.weekday()]} {d:%d/%m}"
    except (AttributeError, ValueError):
        return iso or ""
