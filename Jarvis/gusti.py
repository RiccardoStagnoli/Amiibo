"""
Jarvis - Profilo dei gusti: impara da quello che fai e da quello che gli dici.

Segnali (tutti locali, nella cartella dati):
  - espliciti: "mi piace X", "non mi piace Y", 👍/👎 sulle scoperte (pesano molto);
  - impliciti: musica che metti, ricerche su Google/YouTube, giochi Steam, domande,
    guide richieste, documenti caricati, descrizioni di foto (pesano meno);
  - ogni interesse perde peso col tempo se non torna (i gusti cambiano).
Puoi vedere, correggere o cancellare tutto dalla sezione "Per te".
"""

import json
import math
import os
import re
import threading
import time
import unicodedata

CARTELLA = os.path.dirname(os.path.abspath(__file__))
FILE_GUSTI = os.path.join(CARTELLA, "dati", "gusti.json")
DIMEZZAMENTO_GIORNI = 45  # dopo 45 giorni senza segnali un interesse vale la meta'
_blocco = threading.Lock()

VUOTE = set("""
a ad al allo alla ai agli alle all anche come con col coi da dal dallo dalla dai dagli dalle dall di del dello della dei
degli delle dell e ed il lo la i gli le l un uno una o in nel nello nella nei negli nelle nell su sul sullo sulla sui sugli
sulle sull per tra fra che chi cui non piu più ma se si sia sono era ho hai ha mi ti ci vi ne me te noi voi loro mio mia
miei mie tuo tua suo sua questo questa quello quella cosa come quando dove perche perché quale quali quanto molto poco
tanto tutto tutti ogni altro altra fare fa fatto essere avere dire detto apri cerca cercami metti mettimi riproduci suona
spotify youtube google chrome steam scarica installa amazon music musica canzone brano video jarvis alexa per favore
grazie ciao oggi domani ieri adesso ora vorrei voglio puoi potresti dimmi spiegami costruire costruisce costruisco fai
guida passo passi modo come si nuovo nuova nuovi nuove migliore migliori prezzo prezzi prova recensione recensioni
review test offerta offerte costo costi quanto quanti usato usata acquisto comprare compra vendita trailer tutorial
funziona funzionano serve servono significa vuol dire spiega fanno sono succede differenza calcola calcolare risolvi
""".split())
FONTE_CATEGORIA = {"musica": "musica", "giochi": "videogiochi", "guida": "fai da te"}

CATEGORIE = {
    "musica": r"spotify|amazon music|canzon|brano|album|playlist|rap|trap|rock|pop|jazz|metal|concerto|cantant|band|dj",
    "motori": r"moto|auto|motore|honda|yamaha|ducati|kawasaki|suzuki|bmw|ktm|aprilia|vespa|scooter|cilindr|carburat|"
              r"frizion|freni|pistone|olio motore|pneumatic|f1|motogp|tuning|officina",
    "videogiochi": r"steam|gioco|giochi|game|gaming|playstation|xbox|nintendo|switch|fortnite|minecraft|fifa|fc \d+|gta|"
                   r"valorant|league of legends|call of duty|twitch",
    "tecnologia": r"pc|computer|scheda video|gpu|cpu|processore|smartphone|iphone|android|arduino|raspberry|"
                  r"programm|python|codice|github|elettronic|drone|stampante 3d|rabbit|intelligenza artificiale|\bai\b",
    "sport": r"calcio|serie a|champions|juventus|inter|milan|roma|napoli|basket|nba|tennis|palestra|allenament|corsa|ciclismo",
    "scienza": r"fisica|chimica|astronom|spazio|nasa|pianet|biologia|matematica|scienz",
    "fai da te": r"costruir|fai da te|bricolage|legno|saldatur|attrezz|trapano|stampante 3d|modellismo|riparare|montare",
    "cinema e serie": r"film|serie tv|netflix|prime video|disney|anime|manga|cinema|attore|regista",
    "scuola": r"verifica|compit|esercizi|interrogazion|scuola|professor|classeviva|teams",
}


def _norm(t):
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def _leggi():
    try:
        with open(FILE_GUSTI, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d.setdefault("interessi", {})   # termine -> {"peso", "ultima", "categoria", "conteggio"}
    d.setdefault("piace", [])
    d.setdefault("non_piace", [])
    d.setdefault("feedback", {})    # link -> +1/-1
    d.setdefault("storico", [])     # ultimi segnali (per il ritratto)
    return d


def _scrivi(d):
    os.makedirs(os.path.dirname(FILE_GUSTI), exist_ok=True)
    d["storico"] = d["storico"][-3000:]
    tmp = FILE_GUSTI + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, FILE_GUSTI)


def categoria(testo):
    t = _norm(testo)
    for nome, schema in CATEGORIE.items():
        if re.search(schema, t):
            return nome
    return "altro"


def termini(testo):
    """Parole significative + l'intera frase breve (es. 'honda cb500') come argomento."""
    t = _norm(testo)
    t = re.sub(r"[^a-z0-9àèéìòù' ]+", " ", t)
    parole = [p for p in t.split() if len(p) >= 3 and p not in VUOTE and not p.isdigit()]
    risultato = list(dict.fromkeys(parole))
    if 2 <= len(parole) <= 4:
        risultato.insert(0, " ".join(parole))
    return risultato[:6]


def _peso_attuale(voce, adesso=None):
    giorni = ((adesso or time.time()) - voce["ultima"]) / 86400
    return voce["peso"] * math.pow(0.5, giorni / DIMEZZAMENTO_GIORNI)


def registra(testo, fonte, forza=1.0):
    """Registra un segnale di interesse."""
    if not testo or not testo.strip():
        return
    adesso = time.time()
    with _blocco:
        d = _leggi()
        bloccati = {_norm(x) for x in d["non_piace"]}
        cat = categoria(testo)
        if cat == "altro":
            cat = FONTE_CATEGORIA.get(fonte, "altro")
        for i, termine in enumerate(termini(testo)):
            if termine in bloccati or any(b in termine for b in bloccati if len(b) > 3):
                continue
            voce = d["interessi"].get(termine, {"peso": 0.0, "ultima": adesso, "categoria": cat, "conteggio": 0})
            voce["peso"] = _peso_attuale(voce, adesso) + forza * (1.0 if i == 0 else 0.6)
            voce["ultima"] = adesso
            voce["conteggio"] += 1
            if voce.get("categoria", "altro") == "altro":
                voce["categoria"] = cat
            d["interessi"][termine] = voce
        d["storico"].append({"ora": adesso, "fonte": fonte, "testo": testo[:200], "categoria": cat})
        if len(d["interessi"]) > 3000:  # tiene i 2000 interessi piu' forti
            migliori = sorted(d["interessi"].items(), key=lambda kv: -_peso_attuale(kv[1], adesso))[:2000]
            d["interessi"] = dict(migliori)
        _scrivi(d)


def mi_piace(cosa):
    cosa = cosa.strip()
    with _blocco:
        d = _leggi()
        if cosa.lower() not in [x.lower() for x in d["piace"]]:
            d["piace"].append(cosa)
        d["non_piace"] = [x for x in d["non_piace"] if x.lower() != cosa.lower()]
        _scrivi(d)
    registra(cosa, "detto da te", forza=6.0)


def non_mi_piace(cosa):
    cosa = cosa.strip()
    with _blocco:
        d = _leggi()
        if cosa.lower() not in [x.lower() for x in d["non_piace"]]:
            d["non_piace"].append(cosa)
        d["piace"] = [x for x in d["piace"] if x.lower() != cosa.lower()]
        n = _norm(cosa)
        d["interessi"] = {k: v for k, v in d["interessi"].items() if n not in k and k not in n}
        _scrivi(d)


def dimentica_interesse(termine):
    with _blocco:
        d = _leggi()
        d["interessi"].pop(_norm(termine), None)
        d["piace"] = [x for x in d["piace"] if _norm(x) != _norm(termine)]
        _scrivi(d)


def feedback(link, titolo, voto):
    """👍 (+1) o 👎 (-1) su una scoperta: rafforza o indebolisce le parole del titolo."""
    with _blocco:
        d = _leggi()
        d["feedback"][link] = voto
        _scrivi(d)
    if voto > 0:
        registra(titolo, "👍 scoperta", forza=2.0)
    else:
        adesso = time.time()
        with _blocco:
            d = _leggi()
            for t in termini(titolo):
                if t in d["interessi"]:
                    d["interessi"][t]["peso"] = max(0.0, _peso_attuale(d["interessi"][t], adesso) - 2.5)
                    d["interessi"][t]["ultima"] = adesso
            _scrivi(d)


def interessi(n=20, categoria_filtro=None):
    d = _leggi()
    adesso = time.time()
    lista = [{"termine": k, "peso": round(_peso_attuale(v, adesso), 2), "categoria": v.get("categoria", "altro"),
              "volte": v.get("conteggio", 0)} for k, v in d["interessi"].items()]
    lista = [x for x in lista if x["peso"] >= 0.5 and (not categoria_filtro or x["categoria"] == categoria_filtro)]
    lista.sort(key=lambda x: -x["peso"])
    # niente doppioni: "honda" non serve se c'e' gia' "honda cb500" piu' forte
    scelti = []
    for x in lista:
        if any(x["termine"] in s["termine"].split() for s in scelti):
            continue
        scelti.append(x)
        if len(scelti) >= n:
            break
    return scelti


def profilo():
    d = _leggi()
    return {"interessi": interessi(30), "piace": d["piace"], "non_piace": d["non_piace"],
            "segnali": len(d["storico"]), "feedback": d["feedback"]}


def storico():
    return _leggi()["storico"]


def cancella_tutto():
    with _blocco:
        _scrivi({"interessi": {}, "piace": [], "non_piace": [], "feedback": {}, "storico": []})


# ---------------------- segnali dai comandi di Jarvis ----------------------
OSSERVAZIONI = [
    (r"^(?:metti|riproduci|suona|fai partire) (?P<q>.+?) su (?:spotify|amazon music)$", "musica", 1.5),
    (r"^(?:apri (?:google )?chrome e cerca|cerca su google|cerca su youtube|apri youtube e cerca) (?P<q>.+)$", "ricerca", 1.2),
    (r"^cerca (?P<q>.+) su (?:youtube|google)$", "ricerca", 1.2),
    (r"^(?:apri steam e )?(?:scarica|installa) (?P<q>.+?)(?: su steam)?$", "giochi", 2.0),
    (r"^(?:come (?:si )?costruisc\w*|spiegami come (?:si )?(?:costruisce|fa|costruire|fare)|guida (?:per|a)|come si fa) (?P<q>.+)$", "guida", 1.5),
    (r"^(?:cosa sai (?:di|su|del|della)|domanda[:,]?|meccanica[:,]?) (?P<q>.+)$", "domanda", 0.8),
    (r"^(?:tienimi d'occhio|avvisami se esce|segui|cerca offerte (?:per|di|su)) (?P<q>.+)$", "oggetto", 2.5),
]


def osserva_comando(testo, esito):
    """Chiamata dopo ogni comando riuscito: impara cosa ti interessa."""
    if esito in ("errore_utente", "sconosciuto"):
        return  # comando sbagliato: non dice niente dei tuoi gusti
    t = _norm(testo).strip(" .!?")
    t = re.sub(r"^(ehi |ok )?jarvis[,:]? ?", "", t)
    for schema, fonte, forza in OSSERVAZIONI:
        m = re.match(schema, t)
        if m and m.group("q").strip():
            registra(m.group("q"), fonte, forza)
            return
    if t.endswith("?") or re.match(r"^(come|cosa|perche|quanto|quale|chi) ", t):
        registra(t, "domanda", 0.5)
