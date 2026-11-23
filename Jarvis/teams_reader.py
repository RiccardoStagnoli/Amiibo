"""
Jarvis - Lettura dei messaggi di Microsoft Teams (account scolastico).

Usa Microsoft Graph (gratuito) con accesso delegato: Jarvis legge solo cio'
che puoi leggere tu.
- Chat private e di gruppo: permesso "Chat.Read" (di solito consentito allo studente).
- Post nei canali dei corsi: permesso "ChannelMessage.Read.All", che spesso
  la scuola NON consente senza approvazione dell'amministratore. Se negato,
  Jarvis legge solo le chat e lo segnala.

Primo accesso: python teams_reader.py  (mostra un codice da inserire su
microsoft.com/devicelogin con l'account della scuola).
"""

import html
import json
import os
import re
import urllib.error
import urllib.request

import config

CARTELLA = os.path.dirname(os.path.abspath(__file__))
CARTELLA_DATI = os.path.join(CARTELLA, "dati")
FILE_CACHE = os.path.join(CARTELLA_DATI, "teams_token.json")
FILE_VISTI = os.path.join(CARTELLA_DATI, "teams_visti.json")
GRAPH = "https://graph.microsoft.com/v1.0"
PERMESSI_BASE = ["User.Read", "Chat.Read"]
PERMESSI_CANALI = ["Team.ReadBasic.All", "Channel.ReadBasic.All", "ChannelMessage.Read.All"]


class ErroreTeams(Exception):
    pass


def configurato():
    return bool(getattr(config, "TEAMS_CLIENT_ID", ""))


def _app():
    import msal

    os.makedirs(CARTELLA_DATI, exist_ok=True)
    cache = msal.SerializableTokenCache()
    if os.path.exists(FILE_CACHE):
        with open(FILE_CACHE, encoding="utf-8") as f:
            cache.deserialize(f.read())
    app = msal.PublicClientApplication(
        config.TEAMS_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{getattr(config, 'TEAMS_TENANT', 'organizations')}",
        token_cache=cache,
    )
    return app, cache


def _salva_cache(cache):
    if cache.has_state_changed:
        with open(FILE_CACHE, "w", encoding="utf-8") as f:
            f.write(cache.serialize())


def _permessi():
    return PERMESSI_BASE + (PERMESSI_CANALI if getattr(config, "TEAMS_LEGGI_CANALI", False) else [])


def _token():
    if not configurato():
        raise ErroreTeams("Teams non configurato: manca TEAMS_CLIENT_ID in config.py (GUIDA, Fase 12).")
    app, cache = _app()
    conti = app.get_accounts()
    risultato = app.acquire_token_silent(_permessi(), account=conti[0]) if conti else None
    if not risultato:
        raise ErroreTeams("Accesso a Teams non effettuato: esegui accedi_teams.bat (GUIDA, Fase 12).")
    _salva_cache(cache)
    if "access_token" not in risultato:
        raise ErroreTeams(risultato.get("error_description", "Token Teams non valido."))
    return risultato["access_token"]


def accedi_interattivo():
    """Accesso con codice dispositivo (da usare una volta, dalla finestra di comando)."""
    app, cache = _app()
    flusso = app.initiate_device_flow(scopes=_permessi())
    if "user_code" not in flusso:
        raise ErroreTeams(flusso.get("error_description", "Impossibile avviare l'accesso."))
    print(flusso["message"])
    risultato = app.acquire_token_by_device_flow(flusso)
    _salva_cache(cache)
    if "access_token" not in risultato:
        raise ErroreTeams(risultato.get("error_description", "Accesso non riuscito."))
    print("Accesso a Teams completato.")


def _get(percorso, token):
    url = percorso if percorso.startswith("http") else GRAPH + percorso
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _testo(corpo):
    t = corpo.get("content", "") if corpo else ""
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def _da_professore(nome):
    prof = [p.lower() for p in getattr(config, "TEAMS_PROFESSORI", [])]
    if not prof:
        return True  # lista vuota = tutti i messaggi
    n = (nome or "").lower()
    return any(p in n for p in prof)


def _visti():
    try:
        with open(FILE_VISTI, encoding="utf-8") as f:
            return set(json.load(f))
    except (OSError, ValueError):
        return set()


def segna_visti(ids):
    v = _visti() | set(ids)
    with open(FILE_VISTI, "w", encoding="utf-8") as f:
        json.dump(sorted(v)[-5000:], f)


def nuovi_messaggi(massimo_chat=20):
    """Messaggi non ancora riferiti, filtrati per professori (TEAMS_PROFESSORI)."""
    token = _token()
    io = _get("/me?$select=id,displayName", token)
    visti = _visti()
    trovati, avvisi = [], []

    def aggiungi(m, dove):
        mittente = ((m.get("from") or {}).get("user") or {})
        if not mittente or mittente.get("id") == io["id"] or m.get("id") in visti:
            return
        if m.get("messageType") != "message" or not _da_professore(mittente.get("displayName")):
            return
        trovati.append({"id": m["id"], "da": mittente.get("displayName", "?"), "dove": dove,
                        "ora": m.get("createdDateTime"), "testo": _testo(m.get("body"))})

    chat = _get(f"/me/chats?$top={massimo_chat}&$expand=members", token).get("value", [])
    for c in chat:
        nome = c.get("topic") or ", ".join(
            x.get("displayName", "") for x in c.get("members", []) if x.get("userId") != io["id"])
        try:
            for m in _get(f"/me/chats/{c['id']}/messages?$top=10", token).get("value", []):
                aggiungi(m, "Chat: " + (nome or "chat"))
        except urllib.error.HTTPError:
            continue

    if getattr(config, "TEAMS_LEGGI_CANALI", False):
        try:
            for team in _get("/me/joinedTeams", token).get("value", []):
                for canale in _get(f"/teams/{team['id']}/channels", token).get("value", []):
                    url = f"/teams/{team['id']}/channels/{canale['id']}/messages?$top=5"
                    for m in _get(url, token).get("value", []):
                        aggiungi(m, f"{team.get('displayName')} / {canale.get('displayName')}")
        except urllib.error.HTTPError as e:
            avvisi.append(f"Post dei canali non leggibili (errore {e.code}): la scuola non concede il permesso.")

    trovati.sort(key=lambda x: x["ora"] or "")
    return {"messaggi": trovati, "avvisi": avvisi}


if __name__ == "__main__":
    try:
        accedi_interattivo()
    except ErroreTeams as e:
        print("Errore:", e)
    input("Premi Invio per chiudere...")
