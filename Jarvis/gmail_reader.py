"""
Jarvis - Lettore Gmail (sola lettura).

Usa la Gmail API ufficiale di Google (gratuita).
Al primo avvio apre il browser per chiederti il permesso di LEGGERE la posta.
Jarvis non puo' inviare, cancellare o modificare email: il permesso richiesto
e' solo "gmail.readonly".
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

# Permesso richiesto: SOLO lettura.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

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


def _servizio():
    return build("gmail", "v1", credentials=_ottieni_credenziali(), cache_discovery=False)


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
