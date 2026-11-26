"""
Jarvis - Guide passo passo per costruire cose.

Fonti, in quest'ordine:
  1. i tuoi documenti e manuali (sezione Memoria) e il manuale di meccanica;
  2. Wikipedia in italiano (API libera e gratuita).
La guida (materiali, attrezzi, sicurezza, passi) viene scritta dall'intelligenza artificiale
locale Ollama (gratuita, GUIDA Fase 6) basandosi su quelle fonti; quello che non e' nelle
fonti viene marcato "(da verificare)". Senza Ollama Jarvis ti mostra le fonti trovate.

Dopo, la segui un passo alla volta: "passo successivo", "passo precedente", "ripeti il passo",
"materiali", anche a voce.
Non spiega come costruire armi, esplosivi o dispositivi pericolosi.
"""

import json
import os
import re
import time
import urllib.parse
import urllib.request

import config

CARTELLA = os.path.dirname(os.path.abspath(__file__))
CARTELLA_GUIDE = os.path.join(CARTELLA, "dati", "guide")
FILE_ATTUALE = os.path.join(CARTELLA_GUIDE, "_attuale.json")
VIETATI = re.compile(r"\b(arm[ai]\b|pistol|fucil|esplosiv|bomb[ae]|ordigno|molotov|munizion|silenziator|veleno|droga|"
                     r"metanfetamin|napalm|polvere da sparo|lanciafiamm|taser|granata)", re.I)
PERICOLOSI = re.compile(r"230 ?v|220 ?v|rete elettrica|quadro elettrico|presa di corrente|alta tensione|gas|caldaia|"
                        r"saldatur|smerigliatrice|motosega|batteri[ae] al litio|litio|tetto|impalcatur|freni|airbag", re.I)


class ErroreGuida(Exception):
    pass


def _wiki(percorso, tentativi=2):
    import urllib.error

    req = urllib.request.Request("https://it.wikipedia.org" + percorso, headers={"User-Agent": "Jarvis-assistente/1.0 (uso personale)"})
    for n in range(tentativi):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code != 429 or n == tentativi - 1:
                raise
            time.sleep(min(10, int(e.headers.get("Retry-After") or 3)))


def fonti_wikipedia(argomento, massimo=2):
    try:
        cerca = _wiki("/w/api.php?" + urllib.parse.urlencode(
            {"action": "query", "list": "search", "srsearch": argomento, "format": "json", "srlimit": massimo}))
        titoli = [x["title"] for x in cerca["query"]["search"]]
        if not titoli:
            return []
        risultato = []
        for titolo in titoli:  # Wikipedia restituisce il testo completo di una pagina per richiesta
            testi = _wiki("/w/api.php?" + urllib.parse.urlencode(
                {"action": "query", "prop": "extracts", "explaintext": 1, "titles": titolo, "format": "json"}))
            p = next(iter(testi["query"]["pages"].values()))
            if p.get("extract"):
                risultato.append({"fonte": "Wikipedia: " + p["title"],
                                  "url": "https://it.wikipedia.org/wiki/" + urllib.parse.quote(p["title"].replace(" ", "_")),
                                  "testo": _parte_utile(p["extract"])})
        return risultato
    except Exception:
        return []


def _parte_utile(testo, massimo=6000):
    """Preferisce le sezioni pratiche (costruzione, realizzazione, funzionamento) all'inizio della voce."""
    sezioni = re.split(r"\n(?===+ )", testo)
    pratiche = [x for x in sezioni if re.match(r"==+ ?(costruzion|realizzazion|fabbricazion|funzionament|struttura|"
                                                   r"material|tecnic|component|montaggi|descrizion)", x, re.I)]
    return (sezioni[0][:2000] + "\n" + "\n".join(pratiche))[:massimo]


def fonti_documenti(argomento, esperto):
    if esperto is None:
        return []
    brani = esperto.cerca(argomento, quanti=4)
    return [{"fonte": f"{b['manuale']} – {b['sezione']}", "url": "", "testo": b["testo"]} for b in brani
            if b.get("punteggio", 0) > 3 and b["manuale"] != "memoria"]


def _ollama(istruzioni, richiesta):
    corpo = {"model": getattr(config, "MODELLO_GUIDE", "") or config.MODELLO_OLLAMA, "stream": False,
             "format": "json", "options": {"temperature": 0.2},
             "messages": [{"role": "system", "content": istruzioni}, {"role": "user", "content": richiesta}]}
    req = urllib.request.Request(config.INDIRIZZO_OLLAMA.rstrip("/") + "/api/chat", data=json.dumps(corpo).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read().decode("utf-8")).get("message", {}).get("content")
    except Exception:
        return None


ISTRUZIONI = (
    "Sei Jarvis. Scrivi una guida pratica in italiano per costruire/realizzare quello che chiede l'utente. "
    "Basati sulle FONTI fornite; ogni informazione che NON trovi nelle fonti marcala con '(da verificare)'. "
    "Sii preciso e concreto, niente frasi inutili. Rispondi SOLO con JSON con queste chiavi: "
    '{"titolo": str, "difficolta": "facile|media|difficile", "tempo": str, "materiali": [str], "attrezzi": [str], '
    '"sicurezza": [str], "passi": [{"titolo": str, "dettaglio": str}], "consigli": [str]}. '
    "Ogni passo deve essere un'azione sola, eseguibile e verificabile."
)


def crea(argomento, esperto=None):
    argomento = argomento.strip(" ?.")
    if VIETATI.search(argomento):
        raise ErroreGuida("Non preparo guide per costruire armi, esplosivi o sostanze pericolose.")
    fonti = fonti_documenti(argomento, esperto) + fonti_wikipedia(argomento)
    testo_fonti = "\n\n".join(f"[{i + 1}] {f['fonte']}\n{f['testo'][:3500]}" for i, f in enumerate(fonti)) or "(nessuna fonte trovata)"
    grezzo = _ollama(ISTRUZIONI, f"FONTI:\n{testo_fonti}\n\nRICHIESTA: come costruire/realizzare {argomento}")
    guida = None
    if grezzo:
        try:
            guida = json.loads(grezzo)
        except ValueError:
            m = re.search(r"\{.*\}", grezzo, re.S)
            guida = json.loads(m.group(0)) if m else None
    if not guida or not guida.get("passi"):
        if not fonti:
            raise ErroreGuida(f"Dati insufficienti per verificare: non ho trovato fonti su '{argomento}' "
                              "e senza Ollama non posso scrivere una guida affidabile.")
        guida = {"titolo": argomento, "difficolta": "", "tempo": "", "materiali": [], "attrezzi": [], "consigli": [],
                 "sicurezza": [], "senza_ai": True,
                 "passi": [{"titolo": f"Leggi: {f['fonte']}", "dettaglio": f["testo"][:900]} for f in fonti[:3]]}
    guida.setdefault("sicurezza", [])
    if PERICOLOSI.search(argomento + " " + json.dumps(guida, ensure_ascii=False)):
        guida["sicurezza"].insert(0, "Lavoro potenzialmente pericoloso: se non sei sicuro fatti seguire da un adulto esperto "
                                     "o da un professionista. Con l'elettricità di casa (230 V) lavora solo a corrente staccata.")
    guida.update(id=f"{int(time.time() * 1000)}", argomento=argomento, creata=time.strftime("%Y-%m-%d %H:%M"),
                 fonti=[{"fonte": f["fonte"], "url": f["url"]} for f in fonti], passo=0)
    os.makedirs(CARTELLA_GUIDE, exist_ok=True)
    with open(os.path.join(CARTELLA_GUIDE, guida["id"] + ".json"), "w", encoding="utf-8") as f:
        json.dump(guida, f, ensure_ascii=False, indent=1)
    imposta_attuale(guida["id"])
    return guida


def elenco():
    os.makedirs(CARTELLA_GUIDE, exist_ok=True)
    guide = []
    for nome in sorted(os.listdir(CARTELLA_GUIDE), reverse=True):
        if nome.endswith(".json") and not nome.startswith("_"):
            with open(os.path.join(CARTELLA_GUIDE, nome), encoding="utf-8") as f:
                g = json.load(f)
            guide.append({"id": g["id"], "titolo": g.get("titolo"), "passi": len(g.get("passi", [])), "creata": g.get("creata")})
    return guide


def carica(id_guida):
    if not re.fullmatch(r"\d+", id_guida or ""):
        raise ErroreGuida("Guida non valida.")
    try:
        with open(os.path.join(CARTELLA_GUIDE, id_guida + ".json"), encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        raise ErroreGuida("Guida non trovata.")


def _salva(g):
    with open(os.path.join(CARTELLA_GUIDE, g["id"] + ".json"), "w", encoding="utf-8") as f:
        json.dump(g, f, ensure_ascii=False, indent=1)


def imposta_attuale(id_guida):
    os.makedirs(CARTELLA_GUIDE, exist_ok=True)
    with open(FILE_ATTUALE, "w", encoding="utf-8") as f:
        json.dump({"id": id_guida}, f)


def attuale():
    try:
        with open(FILE_ATTUALE, encoding="utf-8") as f:
            return carica(json.load(f)["id"])
    except (OSError, ValueError, KeyError, ErroreGuida):
        raise ErroreGuida("Nessuna guida aperta. Chiedimi per esempio: 'come si costruisce un aquilone'.")


def testo_passo(g):
    n = g["passo"]
    p = g["passi"][n]
    return f"Passo {n + 1} di {len(g['passi'])}: {p['titolo']}. {p['dettaglio']}"


def muovi(direzione):
    g = attuale()
    if direzione == "avanti":
        if g["passo"] >= len(g["passi"]) - 1:
            return g, "Ultimo passo già raggiunto. Lavoro finito: controlla tutto prima di usarlo."
        g["passo"] += 1
    elif direzione == "indietro":
        g["passo"] = max(0, g["passo"] - 1)
    elif direzione == "inizio":
        g["passo"] = 0
    _salva(g)
    return g, testo_passo(g)


def riassunto(g):
    righe = [f"{g.get('titolo', g['argomento'])}" + (f" – difficoltà {g['difficolta']}" if g.get("difficolta") else "")
             + (f", tempo {g['tempo']}" if g.get("tempo") else "") + "."]
    if g.get("sicurezza"):
        righe.append("Sicurezza: " + " ".join(g["sicurezza"][:3]))
    if g.get("materiali"):
        righe.append("Materiali: " + ", ".join(g["materiali"]) + ".")
    if g.get("attrezzi"):
        righe.append("Attrezzi: " + ", ".join(g["attrezzi"]) + ".")
    if g.get("senza_ai"):
        righe.append("Ollama non è attivo: ti mostro le fonti trovate invece di una guida scritta passo per passo.")
    righe.append(testo_passo(g) + " Di' 'passo successivo' per andare avanti.")
    return "\n".join(righe)
