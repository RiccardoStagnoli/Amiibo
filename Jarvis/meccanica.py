"""
Jarvis - Esperto di meccanica basato SOLO sui manuali nella cartella "manuali".

Come funziona:
1. All'avvio legge tutti i file .txt nella cartella "manuali".
2. Divide il testo in brani e, per ogni domanda, trova i brani piu' pertinenti
   (ricerca BM25, tutta in locale, nessun costo).
3. Se sul computer e' attivo Ollama (intelligenza artificiale locale e gratuita),
   Jarvis scrive una risposta usando ESCLUSIVAMENTE quei brani.
   Se Ollama non c'e', Jarvis mostra i brani del manuale cosi' come sono.

Per aggiungere altri manuali basta copiare altri file .txt (UTF-8) in "manuali".
"""

import glob
import json
import math
import os
import re
import unicodedata
import urllib.error
import urllib.request
from collections import Counter

import config

CARTELLA = os.path.dirname(os.path.abspath(__file__))
CARTELLA_MANUALI = os.path.join(CARTELLA, "manuali")
# Documenti caricati dall'utente dal pannello (sezione Memoria), convertiti in .txt
CARTELLA_DOCUMENTI = os.path.join(CARTELLA, "dati", "documenti")
NOME_MEMORIA = "memoria"

PAROLE_VUOTE = set("""
a ad al allo alla ai agli alle all anche come con col coi da dal dallo dalla dai dagli dalle
dall di del dello della dei degli delle dell e ed è il lo la i gli le l un uno una un o od
in nel nello nella nei negli nelle nell su sul sullo sulla sui sugli sulle sull per tra fra
che chi cui non piu più ma se si sia sono era erano essere ha hanno ho hai questo questa
questi queste quello quella quelli quelle cosa cos come quale quali quando dove perche
perché mi ti ci vi ne me te lui lei noi voi loro suo sua suoi sue mio mia tuo tua molto
poi gia già ancora cosi così tanto ogni qualche qual funziona funzionano serve servono
""".split())

# Termini moderni -> termini usati nel manuale del 1907 (solo equivalenze di nome).
SINONIMI = {
    "frizione": ["innesto"],
    "innesto": ["frizione"],
    "batteria": ["accumulatori"],
    "telaio": ["chassis"],
    "chassis": ["telaio"],
}

# Parole tipiche delle domande, che non devono per forza comparire nella risposta.
PAROLE_DOMANDA = set("""
come cosa serve sai sapere ricordi ricorda dimmi dici spiega spiegami descrivi parlami
quanto quanta quanti quante qual quale quali chi dove quando perche perché funziona funzionano
""".split())

RX_TITOLO = re.compile(r"^[A-ZÀÈÉÌÒÙ][A-ZÀÈÉÌÒÙ .,'’—\-]{5,}$")
RX_SOTTOTITOLO = re.compile(r"^[A-ZÀ-Ù][^—\d]{2,60}\.$")


def _normalizza(parola):
    parola = unicodedata.normalize("NFKD", parola.lower())
    return "".join(c for c in parola if not unicodedata.combining(c))


def _radice(parola):
    # Radice approssimata: le prime 6 lettere (carburatore/carburazione -> "carbur").
    return parola[:6]


def _parole(testo, con_sinonimi=False):
    risultato = []
    for p in re.findall(r"[a-zA-ZÀ-ÿ]+", testo):
        p = _normalizza(p)
        if len(p) < 3 or p in PAROLE_VUOTE:
            continue
        risultato.append(_radice(p))
        if con_sinonimi:
            for s in SINONIMI.get(p, []):
                risultato.append(_radice(s))
    return risultato


def _carica_brani(lunghezza_massima=1100):
    brani = []
    percorsi = sorted(glob.glob(os.path.join(CARTELLA_MANUALI, "*.txt")))
    percorsi += sorted(glob.glob(os.path.join(CARTELLA_DOCUMENTI, "*.txt")))
    for percorso in percorsi:
        nome_manuale = os.path.splitext(os.path.basename(percorso))[0]
        with open(percorso, encoding="utf-8", errors="replace") as f:
            righe = f.read().replace("\r\n", "\n").split("\n")

        sezione = "Introduzione"
        paragrafo, correnti = [], []
        in_illustrazione = False

        def chiudi_brano():
            if correnti:
                brani.append({
                    "manuale": nome_manuale,
                    "sezione": sezione,
                    "testo": "\n\n".join(correnti),
                })
                correnti.clear()

        def chiudi_paragrafo():
            if paragrafo:
                nonlocal sezione
                testo = " ".join(r.strip() for r in paragrafo).strip()
                una_riga = len(paragrafo) == 1
                paragrafo.clear()
                if not testo:
                    return
                # Sottotitolo: riga isolata e breve, es. "Raffreddamento." o "Innesto."
                if una_riga and RX_SOTTOTITOLO.match(testo) and len(testo.split()) <= 4:
                    chiudi_brano()
                    sezione = testo.rstrip(".")
                    return
                if sum(len(c) for c in correnti) + len(testo) > lunghezza_massima:
                    chiudi_brano()
                correnti.append(testo)

        for riga in righe:
            pulita = riga.strip()
            # Le didascalie "[Illustrazione: ...]" (anche su piu' righe) vengono saltate.
            if pulita.startswith("[Illustrazione"):
                in_illustrazione = True
            if in_illustrazione:
                if pulita.endswith("]"):
                    in_illustrazione = False
                continue
            if not pulita:
                chiudi_paragrafo()
                continue
            if re.fullmatch(r"PAGINA \d+", pulita):  # segnaposto dei PDF caricati
                chiudi_paragrafo()
                chiudi_brano()
                sezione = pulita.capitalize()
                continue
            if RX_TITOLO.match(pulita) and not re.search(r"[a-z]", pulita):
                chiudi_paragrafo()
                chiudi_brano()
                sezione = pulita.capitalize()
                continue
            paragrafo.append(riga)
        chiudi_paragrafo()
        chiudi_brano()
    return brani


class EspertoMeccanica:
    """Motore di ricerca su: manuali, documenti caricati dall'utente e fatti insegnati (memoria)."""

    def __init__(self):
        self.ricarica()

    def ricarica(self):
        """Rilegge manuali, documenti e fatti: da chiamare dopo ogni cosa nuova imparata."""
        import memoria

        brani = _carica_brani()
        for f in memoria.fatti():
            brani.append({"manuale": NOME_MEMORIA, "sezione": "Fatto insegnato", "testo": f["testo"], "id": f["id"]})
        if not brani:
            raise FileNotFoundError("Nessun manuale trovato nella cartella:\n  " + CARTELLA_MANUALI)
        self.brani = brani
        self._documenti = [
            Counter(_parole(b["sezione"] + " " + b["testo"])) for b in self.brani
        ]
        self._lunghezze = [sum(d.values()) for d in self._documenti]
        self._lunghezza_media = sum(self._lunghezze) / len(self._lunghezze)
        frequenze = Counter()
        for d in self._documenti:
            frequenze.update(d.keys())
        n = len(self._documenti)
        self._idf = {
            t: math.log(1 + (n - df + 0.5) / (df + 0.5)) for t, df in frequenze.items()
        }

    def manuali_caricati(self):
        return sorted({b["manuale"] for b in self.brani})

    def cerca(self, domanda, quanti=4, solo=None):
        """Ricerca BM25: restituisce i brani piu' pertinenti con il loro punteggio.
        solo: nome di una fonte (es. "memoria") per cercare solo li'."""
        termini = set(_parole(domanda, con_sinonimi=True))
        k1, b = 1.5, 0.75
        punteggi = []
        for i, doc in enumerate(self._documenti):
            if solo and self.brani[i]["manuale"] != solo:
                continue
            s = 0.0
            for t in termini:
                tf = doc.get(t, 0)
                if tf:
                    s += self._idf[t] * tf * (k1 + 1) / (
                        tf + k1 * (1 - b + b * self._lunghezze[i] / self._lunghezza_media)
                    )
            if s > 0:
                punteggi.append((s, i))
        punteggi.sort(reverse=True)
        return [dict(self.brani[i], punteggio=round(s, 2)) for s, i in punteggi[:quanti]]

    def copertura(self, domanda, brani):
        """Quota (0..1) dei termini della domanda presenti nei brani trovati."""
        gruppi = []
        for p in re.findall(r"[a-zA-ZÀ-ÿ]+", domanda):
            n = _normalizza(p)
            if len(n) < 3 or n in PAROLE_VUOTE or n in PAROLE_DOMANDA:
                continue
            gruppi.append({_radice(n)} | {_radice(s) for s in SINONIMI.get(n, [])})
        if not gruppi:
            return 0.0
        presenti = set()
        for b in brani:
            presenti.update(_parole(b["sezione"] + " " + b["testo"]))
        return sum(1 for g in gruppi if g & presenti) / len(gruppi)

    def rispondi(self, domanda, solo=None):
        """
        Restituisce (testo_risposta, brani_usati).
        La risposta si basa solo su manuali, documenti e fatti insegnati e viene
        data solo se almeno il 90% dei termini della domanda vi compare.
        """
        brani = self.cerca(domanda, quanti=config.BRANI_PER_RISPOSTA, solo=solo)
        if not brani:
            return ("Dati insufficienti per verificare: non ho informazioni su questo argomento.", [])
        soglia = getattr(config, "SOGLIA_CERTEZZA", 0.90)
        cop = self.copertura(domanda, brani)
        if cop < soglia:
            return (f"Dati insufficienti per verificare: le mie fonti coprono solo il {round(cop * 100)}% "
                    "dei termini della domanda. Non rispondo.", [])

        # Se la risposta sta tutta nei fatti che mi hai insegnato, li riporto cosi' come sono.
        fatti = [b for b in brani if b["manuale"] == NOME_MEMORIA]
        if fatti and self.copertura(domanda, fatti) >= soglia:
            return ("Dalla memoria: " + " ".join(f["testo"] for f in fatti[:3]), fatti[:3])

        risposta_ai = _chiedi_a_ollama(domanda, brani)
        if risposta_ai:
            return (risposta_ai, brani)

        testo = [
            "(Ollama non attivo o modello '" + config.MODELLO_OLLAMA + "' non scaricato: "
            "ecco i passaggi piu' pertinenti delle mie fonti)\n"
        ]
        for n, br in enumerate(brani, 1):
            testo.append(f"[{n}] Sezione: {br['sezione']}\n{br['testo']}\n")
        return ("\n".join(testo), brani)


def _chiedi_a_ollama(domanda, brani):
    estratti = "\n\n".join(
        f"[{n}] (Fonte: {b['manuale']}, sezione: {b['sezione']})\n{b['testo']}" for n, b in enumerate(brani, 1)
    )
    istruzioni = (
        "Sei Jarvis, assistente personale. Rispondi in italiano, in modo serio, preciso e conciso: "
        "niente complimenti, niente giri di parole, niente frasi di cortesia. "
        "Usa ESCLUSIVAMENTE le informazioni contenute negli ESTRATTI forniti (manuali, documenti dell'utente, fatti insegnati). "
        "Non aggiungere conoscenze esterne. Se gli estratti non contengono la risposta, "
        "rispondi esattamente: 'Dati insufficienti per verificare.' "
        "Indica tra parentesi quadre il numero dell'estratto usato, ad esempio [1]. "
        "Se usi il manuale 'la_vettura_automobile_1907', ricorda che e' del 1907."
    )
    corpo = {
        "model": config.MODELLO_OLLAMA,
        "stream": False,
        "options": {"temperature": 0.1},
        "messages": [
            {"role": "system", "content": istruzioni},
            {"role": "user", "content": f"ESTRATTI:\n{estratti}\n\nDOMANDA: {domanda}"},
        ],
    }
    richiesta = urllib.request.Request(
        config.INDIRIZZO_OLLAMA.rstrip("/") + "/api/chat",
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(richiesta, timeout=300) as r:
            dati = json.loads(r.read().decode("utf-8"))
        return (dati.get("message", {}).get("content") or "").strip() or None
    except (urllib.error.URLError, OSError, ValueError):
        return None
