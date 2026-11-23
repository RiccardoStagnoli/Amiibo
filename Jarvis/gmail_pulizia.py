"""
Jarvis - Pulizia Gmail: individua spam e pubblicita' nella Posta in arrivo.

Ogni email riceve un PUNTEGGIO da 0 a 1 calcolato con regole verificabili
(categoria Gmail "Promozioni", intestazione di disiscrizione, mittenti
"noreply/newsletter", parole tipiche delle pubblicita', ecc.).

- punteggio >= SOGLIA_CERTEZZA (0.90): proposta di eliminazione/archiviazione
- tra 0.60 e 0.90: "dubbia", Jarvis NON agisce
- sotto 0.60: considerata posta normale

Il punteggio e' una stima a regole, NON una probabilita' misurata.
Non viene mai toccata posta con stella, importante, o da mittenti a cui
hai scritto almeno una volta, o presenti in MITTENTI_PROTETTI (config.py).
"""

import re

import config
import gmail_reader
from personalita import SOGLIA_CERTEZZA

PAROLE_PUBBLICITA = re.compile(
    r"(offert|scont|promo|saldi|gratis|omaggio|coupon|codice sconto|black friday|"
    r"cyber monday|ultim[ie] ore|solo per te|hai vinto|vinci|newsletter|\d+\s?%|€\s?\d)",
    re.IGNORECASE,
)
MITTENTI_MASSA = re.compile(r"(no-?reply|newsletter|marketing|promo|offerte|news@|info@|mailer)", re.I)


def _intestazioni(hdr):
    return {h["name"].lower(): h.get("value", "") for h in hdr}


def _indirizzo(mittente):
    m = re.search(r"<([^>]+)>", mittente)
    return (m.group(1) if m else mittente).strip().lower()


def _protetto(indirizzo):
    protetti = [p.lower() for p in getattr(config, "MITTENTI_PROTETTI", [])]
    return any(p and (indirizzo == p or indirizzo.endswith("@" + p) or indirizzo.endswith("." + p))
               for p in protetti)


def punteggio(etichette, h, scritto_a_mittente):
    """Restituisce (punteggio 0..1, motivi)."""
    motivi, s = [], 0.0
    if "STARRED" in etichette or "IMPORTANT" in etichette:
        return 0.0, ["contrassegnata come importante o con stella"]
    if scritto_a_mittente:
        return 0.0, ["hai già scritto a questo mittente"]
    if "CATEGORY_PROMOTIONS" in etichette:
        s += 0.45; motivi.append("categoria Promozioni di Gmail")
    if "CATEGORY_SOCIAL" in etichette:
        s += 0.25; motivi.append("notifica social")
    if h.get("list-unsubscribe"):
        s += 0.25; motivi.append("invio di massa (link di disiscrizione)")
    if h.get("precedence", "").lower() in ("bulk", "list", "junk"):
        s += 0.10; motivi.append("precedenza bulk")
    if MITTENTI_MASSA.search(h.get("from", "")):
        s += 0.15; motivi.append("mittente automatico")
    parole = PAROLE_PUBBLICITA.findall(h.get("subject", ""))
    if parole:
        s += min(0.10 * len(parole), 0.20); motivi.append("parole pubblicitarie nell'oggetto")
    return round(min(s, 1.0), 2), motivi


def analizza(massimo=150):
    """Analizza la Posta in arrivo. Restituisce le email classificate."""
    srv = gmail_reader._servizio()
    lista = srv.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=massimo).execute()
    gia_scritti = {}
    risultati = []
    for m in lista.get("messages", []):
        d = srv.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date", "List-Unsubscribe", "Precedence"],
        ).execute()
        h = _intestazioni(d.get("payload", {}).get("headers", []))
        indirizzo = _indirizzo(h.get("from", ""))
        if _protetto(indirizzo):
            continue
        if indirizzo not in gia_scritti:
            r = srv.users().messages().list(userId="me", q=f"to:{indirizzo} in:sent", maxResults=1).execute()
            gia_scritti[indirizzo] = bool(r.get("messages"))
        p, motivi = punteggio(d.get("labelIds", []), h, gia_scritti[indirizzo])
        if p < 0.6:
            continue
        risultati.append({
            "id": m["id"],
            "mittente": h.get("from", ""),
            "oggetto": h.get("subject", "(senza oggetto)"),
            "data": h.get("date", ""),
            "dimensione_kb": round(d.get("sizeEstimate", 0) / 1024),
            "punteggio": p,
            "sicura": p >= SOGLIA_CERTEZZA,
            "motivi": motivi,
        })
    risultati.sort(key=lambda x: -x["punteggio"])
    return risultati


def email_pesanti(minimo_mb=5, massimo=50):
    """Email grandi (con allegati) più vecchie di un anno: candidate per liberare spazio."""
    srv = gmail_reader._servizio()
    r = srv.users().messages().list(
        userId="me", q=f"larger:{minimo_mb}M older_than:1y -is:starred", maxResults=massimo
    ).execute()
    risultati = []
    for m in r.get("messages", []):
        d = srv.users().messages().get(userId="me", id=m["id"], format="metadata",
                                       metadataHeaders=["From", "Subject", "Date"]).execute()
        h = _intestazioni(d.get("payload", {}).get("headers", []))
        risultati.append({"id": m["id"], "mittente": h.get("from", ""), "oggetto": h.get("subject", ""),
                          "data": h.get("date", ""), "dimensione_mb": round(d.get("sizeEstimate", 0) / 1048576, 1)})
    return sorted(risultati, key=lambda x: -x["dimensione_mb"])
