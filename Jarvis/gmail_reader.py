"""
Jarvis - Accesso all'account Google (Gmail, Calendario, Drive).

Usa le API ufficiali di Google (gratuite).
Permessi richiesti (accesso completo, come richiesto):
  - Gmail completo (leggere, archiviare, segnare come spam, cestinare, eliminare)
  - Google Calendar
  - Google Drive
Al primo avvio (e quando cambiano i permessi) apre il browser per il consenso.
"""

import base64
import html
import os
import re

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
]

CARTELLA = os.path.dirname(os.path.abspath(__file__))
FILE_CREDENZIALI = os.path.join(CARTELLA, "credentials.json")  # scaricato da Google Cloud
FILE_TOKEN = os.path.join(CARTELLA, "token.json")  # creato da Jarvis dopo il primo accesso


class ErroreGmail(Exception):
    pass


def _ottieni_credenziali():
    if not os.path.exists(FILE_CREDENZIALI):
        raise ErroreGmail(
            "File credentials.json non trovato in:\n  " + FILE_CREDENZIALI +
            "\nSegui la GUIDA, Fase 3, per scaricarlo da Google Cloud."
        )

    creds = None
    if os.path.exists(FILE_TOKEN):
        creds = Credentials.from_authorized_user_file(FILE_TOKEN, SCOPES)

    if creds and not creds.has_scopes(SCOPES):
        creds = None  # permessi cambiati: serve un nuovo consenso

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            # In modalita' "Test" Google fa scadere l'accesso dopo 7 giorni:
            # si rifa' il login dal browser.
            creds = None

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(FILE_CREDENZIALI, SCOPES)
        print("Jarvis: apro il browser per l'accesso a Gmail...")
        creds = flow.run_local_server(port=0)

    with open(FILE_TOKEN, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    return creds


def _servizio(nome="gmail", versione="v1"):
    return build(nome, versione, credentials=_ottieni_credenziali(), cache_discovery=False)


def _intestazione(headers, nome):
    for h in headers:
        if h.get("name", "").lower() == nome.lower():
            return h.get("value", "")
    return ""


def _decodifica(dati):
    if not dati:
        return ""
    return base64.urlsafe_b64decode(dati.encode("ascii")).decode("utf-8", errors="replace")


def _html_in_testo(testo_html):
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", testo_html)
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</li>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return t.strip()


def _estrai_corpo(payload):
    """Restituisce il testo dell'email (preferisce text/plain, altrimenti converte l'HTML)."""
    testi, htmls = [], []

    def visita(parte):
        tipo = parte.get("mimeType", "")
        dati = parte.get("body", {}).get("data")
        if parte.get("filename"):
            return  # allegato: ignorato
        if tipo == "text/plain" and dati:
            testi.append(_decodifica(dati))
        elif tipo == "text/html" and dati:
            htmls.append(_decodifica(dati))
        for sotto in parte.get("parts", []) or []:
            visita(sotto)

    visita(payload)
    if testi:
        return "\n".join(testi).strip()
    if htmls:
        return _html_in_testo("\n".join(htmls))
    return "(Email senza testo leggibile)"


def elenca_email(query="", massimo=10, solo_posta_in_arrivo=True):
    """
    Restituisce una lista di email (dizionari) che corrispondono alla ricerca Gmail.
    Esempi di query: "is:unread", "from:amazon", "subject:fattura", "" (tutte).
    """
    try:
        srv = _servizio()
        parametri = {"userId": "me", "q": query, "maxResults": massimo}
        if solo_posta_in_arrivo:
            parametri["labelIds"] = ["INBOX"]
        risposta = srv.users().messages().list(**parametri).execute()
        risultati = []
        for m in risposta.get("messages", []):
            dett = srv.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            hdr = dett.get("payload", {}).get("headers", [])
            risultati.append({
                "id": m["id"],
                "mittente": _intestazione(hdr, "From"),
                "oggetto": _intestazione(hdr, "Subject") or "(senza oggetto)",
                "data": _intestazione(hdr, "Date"),
                "anteprima": html.unescape(dett.get("snippet", "")),
                "non_letta": "UNREAD" in dett.get("labelIds", []),
            })
        return risultati
    except ErroreGmail:
        raise
    except Exception as e:  # rete assente, permesso revocato, ecc.
        raise ErroreGmail("Errore durante la lettura di Gmail: " + str(e)) from e


def leggi_email(id_messaggio):
    """Restituisce il contenuto completo di una email. Non la segna come letta."""
    try:
        msg = _servizio().users().messages().get(
            userId="me", id=id_messaggio, format="full"
        ).execute()
        payload = msg.get("payload", {})
        hdr = payload.get("headers", [])
        return {
            "mittente": _intestazione(hdr, "From"),
            "destinatario": _intestazione(hdr, "To"),
            "oggetto": _intestazione(hdr, "Subject") or "(senza oggetto)",
            "data": _intestazione(hdr, "Date"),
            "corpo": _estrai_corpo(payload),
        }
    except ErroreGmail:
        raise
    except Exception as e:
        raise ErroreGmail("Errore durante l'apertura dell'email: " + str(e)) from e


# ----------------------------- AZIONI SU GMAIL -----------------------------
def archivia(ids):
    """Toglie le email dalla Posta in arrivo (restano in "Tutti i messaggi")."""
    if ids:
        _servizio().users().messages().batchModify(
            userId="me", body={"ids": list(ids), "removeLabelIds": ["INBOX"]}
        ).execute()
    return len(ids)


def segna_spam(ids):
    srv = _servizio()
    for i in ids:
        srv.users().messages().modify(
            userId="me", id=i, body={"addLabelIds": ["SPAM"], "removeLabelIds": ["INBOX"]}
        ).execute()
    return len(ids)


def cestina(ids):
    """Sposta nel cestino (Gmail lo svuota da solo dopo 30 giorni)."""
    srv = _servizio()
    for i in ids:
        srv.users().messages().trash(userId="me", id=i).execute()
    return len(ids)


def svuota_cestino():
    """Elimina DEFINITIVAMENTE tutte le email nel cestino. Irreversibile."""
    srv = _servizio()
    totale = 0
    while True:
        r = srv.users().messages().list(userId="me", labelIds=["TRASH"], maxResults=500).execute()
        ids = [m["id"] for m in r.get("messages", [])]
        if not ids:
            return totale
        srv.users().messages().batchDelete(userId="me", body={"ids": ids}).execute()
        totale += len(ids)


def conta(query):
    r = _servizio().users().messages().list(userId="me", q=query, maxResults=500).execute()
    return r.get("resultSizeEstimate", 0)


# ------------------------------ DRIVE / SPAZIO ------------------------------
def spazio_account():
    """Spazio usato dall'account Google (Gmail + Drive + Foto), in byte."""
    q = _servizio("drive", "v3").about().get(fields="storageQuota").execute()["storageQuota"]
    return {k: int(v) for k, v in q.items() if str(v).isdigit()}


def cerca_drive(testo, massimo=10):
    sicuro = testo.replace("\\", "").replace("'", "\\'")
    r = _servizio("drive", "v3").files().list(
        q=f"name contains '{sicuro}' and trashed = false",
        pageSize=massimo,
        fields="files(id,name,mimeType,modifiedTime,webViewLink)",
        orderBy="modifiedTime desc",
    ).execute()
    return r.get("files", [])


# -------------------------------- CALENDARIO --------------------------------
def eventi_oggi():
    from datetime import datetime, time, timedelta

    adesso = datetime.now().astimezone()
    inizio = datetime.combine(adesso.date(), time.min, adesso.tzinfo)
    fine = inizio + timedelta(days=1)
    r = _servizio("calendar", "v3").events().list(
        calendarId="primary", timeMin=inizio.isoformat(), timeMax=fine.isoformat(),
        singleEvents=True, orderBy="startTime",
    ).execute()
    eventi = []
    for e in r.get("items", []):
        inizio_ev = e.get("start", {}).get("dateTime") or e.get("start", {}).get("date")
        eventi.append({"titolo": e.get("summary", "(senza titolo)"), "inizio": inizio_ev,
                       "luogo": e.get("location", "")})
    return eventi


def aggiungi_evento_rapido(testo):
    """Crea un evento dal testo libero (interpretato da Google, es. 'Dentista domani alle 15')."""
    e = _servizio("calendar", "v3").events().quickAdd(calendarId="primary", text=testo).execute()
    return {"titolo": e.get("summary"), "inizio": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
            "link": e.get("htmlLink")}


def invia_risposta(id_messaggio, testo):
    """Risponde a un'email (stessa conversazione) con un testo semplice."""
    from email.mime.text import MIMEText

    srv = _servizio()
    m = srv.users().messages().get(userId="me", id=id_messaggio, format="metadata",
                                   metadataHeaders=["From", "Reply-To", "Subject", "Message-ID", "References"]).execute()
    h = m.get("payload", {}).get("headers", [])
    destinatario = _intestazione(h, "Reply-To") or _intestazione(h, "From")
    oggetto = _intestazione(h, "Subject")
    if not oggetto.lower().startswith("re:"):
        oggetto = "Re: " + oggetto
    msg = MIMEText(testo, "plain", "utf-8")
    msg["To"] = destinatario
    msg["Subject"] = oggetto
    mid = _intestazione(h, "Message-ID")
    if mid:
        msg["In-Reply-To"] = mid
        msg["References"] = (_intestazione(h, "References") + " " + mid).strip()
    grezzo = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    srv.users().messages().send(userId="me", body={"raw": grezzo, "threadId": m.get("threadId")}).execute()
    return destinatario


def eventi_prossimi(giorni=7):
    """Eventi del calendario da adesso ai prossimi 'giorni' giorni."""
    from datetime import datetime, timedelta

    adesso = datetime.now().astimezone()
    r = _servizio("calendar", "v3").events().list(
        calendarId="primary", timeMin=adesso.isoformat(), timeMax=(adesso + timedelta(days=giorni)).isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=50,
    ).execute()
    return [{"id": e["id"], "titolo": e.get("summary", "(senza titolo)"),
             "inizio": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
             "luogo": e.get("location", "")} for e in r.get("items", [])]
