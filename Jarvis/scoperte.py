"""
Jarvis - Scoperte: notizie e oggetti che ti possono interessare.

- Fonte: Google News (feed RSS pubblici, gratuiti, senza chiave), cercando i tuoi
  interessi piu' forti (gusti.py) e gli oggetti che segui ("tienimi d'occhio X").
- Ogni scoperta dice PERCHE' te la propone. Con 👍/👎 Jarvis affina i gusti.
- Oggetti: Jarvis non ha accesso ai prezzi dei negozi (le loro API non sono gratuite):
  segnala notizie, uscite e recensioni, e prepara i link di ricerca su Amazon, eBay, Subito, Idealo.
"""

import email.utils
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import gusti

CARTELLA = os.path.dirname(os.path.abspath(__file__))
FILE_STATO = os.path.join(CARTELLA, "dati", "scoperte.json")
_blocco = threading.Lock()
_cache = {}  # query -> (ora, risultati)
_ultima_richiesta = [0.0]


def _stato():
    try:
        with open(FILE_STATO, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d.setdefault("oggetti", [])   # [{"nome", "dal"}]
    d.setdefault("visti", [])     # link gia' mostrati
    d.setdefault("avvisati", [])  # link gia' notificati per gli oggetti
    return d


def _salva(d):
    os.makedirs(os.path.dirname(FILE_STATO), exist_ok=True)
    d["visti"] = d["visti"][-3000:]
    d["avvisati"] = d["avvisati"][-3000:]
    with open(FILE_STATO, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


def notizie(query, giorni=7, massimo=8):
    """Notizie recenti da Google News per una ricerca."""
    chiave = (query, giorni)
    if chiave in _cache and time.time() - _cache[chiave][0] < 3 * 3600:
        return _cache[chiave][1]
    # Google News limita le richieste troppo ravvicinate: una ogni 1,5 secondi
    attesa = 1.5 - (time.time() - _ultima_richiesta[0])
    if attesa > 0:
        time.sleep(attesa)
    _ultima_richiesta[0] = time.time()
    url = ("https://news.google.com/rss/search?" +
           urllib.parse.urlencode({"q": f"{query} when:{giorni}d", "hl": "it", "gl": "IT", "ceid": "IT:it"}))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Jarvis assistente)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        radice = ET.fromstring(r.read())
    risultati = []
    for item in radice.findall(".//item")[:massimo]:
        titolo = item.findtext("title") or ""
        fonte = item.find("source")
        nome_fonte = fonte.text if fonte is not None else ""
        if nome_fonte and titolo.endswith(" - " + nome_fonte):
            titolo = titolo[: -len(nome_fonte) - 3]
        try:
            quando = email.utils.parsedate_to_datetime(item.findtext("pubDate")).timestamp()
        except (TypeError, ValueError):
            quando = time.time()
        risultati.append({"titolo": titolo, "link": item.findtext("link") or "", "fonte": nome_fonte, "quando": quando})
    _cache[chiave] = (time.time(), risultati)
    return risultati


def link_negozi(oggetto):
    q = urllib.parse.quote_plus(oggetto)
    return {"Amazon": f"https://www.amazon.it/s?k={q}", "eBay": f"https://www.ebay.it/sch/i.html?_nkw={q}",
            "Subito": f"https://www.subito.it/annunci-italia/vendita/usato/?q={q}",
            "Idealo": f"https://www.idealo.it/MainSearchProductCategory.html?q={q}"}


def per_te(quanti=15, segna=True):
    """Le scoperte migliori per i tuoi interessi (e gli oggetti che segui)."""
    s = _stato()
    bloccati = [gusti._norm(x) for x in gusti._leggi()["non_piace"]]
    feedback_neg = {k for k, v in gusti._leggi()["feedback"].items() if v < 0}
    visti = set(s["visti"])
    ricerche = [(o["nome"], 4.0, "segui") for o in s["oggetti"]]
    ricerche += [(i["termine"], i["peso"], i["categoria"]) for i in gusti.interessi(8)]
    trovate, avvisi = [], []
    for query, peso, perche in ricerche[:8]:
        try:
            for n in notizie(query):
                titolo_n = gusti._norm(n["titolo"])
                if n["link"] in feedback_neg or any(b in titolo_n for b in bloccati if b):
                    continue
                giorni = max(0.0, (time.time() - n["quando"]) / 86400)
                pertinenza = 1.0 if all(p in titolo_n for p in gusti._norm(query).split()) else 0.5
                punteggio = peso * pertinenza * (0.85 ** giorni) * (0.4 if n["link"] in visti else 1.0)
                trovate.append({**n, "punteggio": round(punteggio, 3), "perche": query,
                                "tipo": "oggetto seguito" if perche == "segui" else perche})
        except Exception as e:
            avvisi.append(f"{query}: {e}")
    # niente doppioni (stessa notizia da piu' ricerche)
    uniche = {}
    for x in sorted(trovate, key=lambda x: -x["punteggio"]):
        chiave = re.sub(r"\W+", "", x["titolo"].lower())[:60]
        uniche.setdefault(chiave, x)
    risultato = list(uniche.values())[:quanti]
    if segna and risultato:
        with _blocco:
            s = _stato()
            s["visti"] += [x["link"] for x in risultato]
            _salva(s)
    return risultato, avvisi


def segui(oggetto):
    with _blocco:
        s = _stato()
        if oggetto.lower() not in [o["nome"].lower() for o in s["oggetti"]]:
            s["oggetti"].append({"nome": oggetto, "dal": time.strftime("%Y-%m-%d")})
        _salva(s)
    gusti.registra(oggetto, "oggetto", 2.5)


def smetti_di_seguire(oggetto):
    with _blocco:
        s = _stato()
        s["oggetti"] = [o for o in s["oggetti"] if o["nome"].lower() != oggetto.lower().strip()]
        _salva(s)


def oggetti():
    return _stato()["oggetti"]


def novita_oggetti():
    """Per gli oggetti seguiti: notizie delle ultime 48 ore mai notificate."""
    s = _stato()
    gia = set(s["avvisati"])
    nuove = []
    for o in s["oggetti"]:
        try:
            for n in notizie(o["nome"], giorni=2, massimo=5):
                if n["link"] not in gia and all(p in gusti._norm(n["titolo"]) for p in gusti._norm(o["nome"]).split()[:2]):
                    nuove.append({**n, "oggetto": o["nome"]})
        except Exception:
            continue
    if nuove:
        with _blocco:
            s = _stato()
            s["avvisati"] += [n["link"] for n in nuove]
            _salva(s)
    return nuove
