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
PERMESSI_BASE = ["User.Read", "Chat.Read", "ChatMessage.Send"]
PERMESSI_COMPITI = ["EduAssignments.ReadBasic"]
PERMESSI_POSTA = ["Mail.Read", "Mail.Send"]
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
    p = list(PERMESSI_BASE)
    if getattr(config, "TEAMS_LEGGI_CANALI", False):
        p += PERMESSI_CANALI
    if getattr(config, "TEAMS_LEGGI_COMPITI", False):
        p += PERMESSI_COMPITI
    if getattr(config, "TEAMS_POSTA_SCUOLA", False):
        p += PERMESSI_POSTA
    return p


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


def nuovi_messaggi(massimo_chat=20, includi_visti=False):
    """Messaggi non ancora riferiti, filtrati per professori (TEAMS_PROFESSORI)."""
    token = _token()
    io = _get("/me?$select=id,displayName", token)
    visti = _visti()
    trovati, avvisi = [], []

    def aggiungi(m, dove):
        mittente = ((m.get("from") or {}).get("user") or {})
        if not mittente or mittente.get("id") == io["id"] or (m.get("id") in visti and not includi_visti):
            return
        if m.get("messageType") != "message" or not _da_professore(mittente.get("displayName")):
            return
        trovati.append({"id": m["id"], "da": mittente.get("displayName", "?"), "dove": dove,
                        "ora": m.get("createdDateTime"), "testo": _testo(m.get("body")), "chat_id": chat_corrente[0]})

    chat_corrente = [None]

    chat = _get(f"/me/chats?$top={massimo_chat}&$expand=members", token).get("value", [])
    for c in chat:
        nome = c.get("topic") or ", ".join(
            x.get("displayName", "") for x in c.get("members", []) if x.get("userId") != io["id"])
        chat_corrente[0] = c["id"]
        try:
            for m in _get(f"/me/chats/{c['id']}/messages?$top=10", token).get("value", []):
                aggiungi(m, "Chat: " + (nome or "chat"))
        except urllib.error.HTTPError:
            continue

    if getattr(config, "TEAMS_LEGGI_CANALI", False):
        try:
            chat_corrente[0] = None
            for team in _get("/me/joinedTeams", token).get("value", []):
                for canale in _get(f"/teams/{team['id']}/channels", token).get("value", []):
                    url = f"/teams/{team['id']}/channels/{canale['id']}/messages?$top=5"
                    for m in _get(url, token).get("value", []):
                        aggiungi(m, f"{team.get('displayName')} / {canale.get('displayName')}")
        except urllib.error.HTTPError as e:
            avvisi.append(f"Post dei canali non leggibili (errore {e.code}): la scuola non concede il permesso.")

    trovati.sort(key=lambda x: x["ora"] or "")
    return {"messaggi": trovati, "avvisi": avvisi}


def _post(percorso, dati, token):
    req = urllib.request.Request(GRAPH + percorso, data=json.dumps(dati).encode("utf-8"), method="POST",
                                 headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        corpo = r.read().decode("utf-8")
        return json.loads(corpo) if corpo else {}


def invia_in_chat(chat_id, testo):
    """Scrive un messaggio in una chat di Teams (permesso ChatMessage.Send)."""
    import html as _html

    contenuto = "<p>" + _html.escape(testo).replace("\n", "<br>") + "</p>"
    try:
        return _post(f"/chats/{chat_id}/messages", {"body": {"contentType": "html", "content": contenuto}}, _token())
    except urllib.error.HTTPError as e:
        raise ErroreTeams(f"Invio su Teams non riuscito (errore {e.code}).")


def compiti_assegnati():
    """Compiti di Teams (Assignments), se la scuola concede il permesso EduAssignments.ReadBasic."""
    if not getattr(config, "TEAMS_LEGGI_COMPITI", False):
        return {"compiti": [], "avvisi": []}
    token = _token()
    try:
        r = _get("/education/me/assignments?$top=30", token).get("value", [])
    except urllib.error.HTTPError as e:
        return {"compiti": [], "avvisi": [f"Compiti di Teams non leggibili (errore {e.code}): permesso non concesso dalla scuola."]}
    compiti = []
    for a in r:
        if a.get("status") not in (None, "assigned", "published"):
            continue
        compiti.append({"id": a["id"], "titolo": a.get("displayName", ""), "testo": _testo(a.get("instructions")),
                        "scadenza": a.get("dueDateTime"), "url": a.get("webUrl"), "classe": a.get("classId")})
    return {"compiti": compiti, "avvisi": []}


def posta_scuola(massimo=20):
    """Email non lette della casella della scuola (Outlook/Microsoft 365)."""
    if not getattr(config, "TEAMS_POSTA_SCUOLA", False):
        return []
    token = _token()
    url = (f"/me/mailFolders/inbox/messages?$top={massimo}&$filter=isRead eq false"
           "&$select=id,subject,from,receivedDateTime,body").replace(" ", "%20")
    r = _get(url, token).get("value", [])
    return [{"id": m["id"], "oggetto": m.get("subject", ""), "da": ((m.get("from") or {}).get("emailAddress") or {}).get("name", "?"),
             "indirizzo": ((m.get("from") or {}).get("emailAddress") or {}).get("address", ""),
             "ora": m.get("receivedDateTime"), "testo": _testo(m.get("body"))} for m in r]


def rispondi_mail_scuola(id_messaggio, testo):
    try:
        _post(f"/me/messages/{id_messaggio}/reply", {"comment": testo}, _token())
    except urllib.error.HTTPError as e:
        raise ErroreTeams(f"Risposta email non inviata (errore {e.code}).")


if __name__ == "__main__":
    try:
        accedi_interattivo()
    except ErroreTeams as e:
        print("Errore:", e)
    input("Premi Invio per chiudere...")
