"""
Jarvis - Memoria: cio' che impara dalle informazioni che gli dai.

  1. FATTI:      "ricorda che la mia moto e' una Honda CB500 del 2019"
                 -> poi "qual e' la mia moto?" risponde dalla memoria.
  2. DOCUMENTI:  PDF, Word (.docx), .txt, .md caricati dal pannello
                 -> diventano fonti per le risposte, come il manuale.
  3. COMANDI:    "quando dico buongiorno mamma intendi scrivi a Mamma: buongiorno"
                 -> la frase diventa un comando nuovo.
  4. NON CAPITI: i comandi che Jarvis non ha capito vengono annotati; dal
                 pannello puoi insegnargli cosa significano.

Non e' un "addestramento" del modello: Jarvis salva e ritrova le informazioni
(tutto in locale, nella cartella dati) e le usa con la regola del 90%.
"""

import json
import os
import re
import threading
import time
import zipfile
from datetime import datetime

CARTELLA = os.path.dirname(os.path.abspath(__file__))
CARTELLA_DATI = os.path.join(CARTELLA, "dati")
CARTELLA_DOCUMENTI = os.path.join(CARTELLA_DATI, "documenti")
FILE_FATTI = os.path.join(CARTELLA_DATI, "memoria_fatti.json")
FILE_ALIAS = os.path.join(CARTELLA_DATI, "memoria_comandi.json")
FILE_NON_CAPITI = os.path.join(CARTELLA_DATI, "memoria_non_capiti.json")
ESTENSIONI = (".txt", ".md", ".pdf", ".docx")
MAX_MB = 25
_blocco = threading.Lock()


def _leggi(percorso, predefinito):
    try:
        with open(percorso, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return predefinito


def _scrivi(percorso, dati):
    os.makedirs(CARTELLA_DATI, exist_ok=True)
    tmp = percorso + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=1)
    os.replace(tmp, percorso)


def _id():
    return f"{int(time.time() * 1000)}"


def _norm(t):
    import unicodedata

    t = unicodedata.normalize("NFKD", (t or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip(" .!?")


# ================================== FATTI ==================================
def fatti():
    return _leggi(FILE_FATTI, [])


def aggiungi_fatto(testo):
    testo = testo.strip()
    with _blocco:
        lista = fatti()
        if any(_norm(f["testo"]) == _norm(testo) for f in lista):
            return None  # gia' noto
        f = {"id": _id(), "testo": testo, "ora": datetime.now().isoformat(timespec="minutes")}
        lista.append(f)
        _scrivi(FILE_FATTI, lista)
    return f


def elimina_fatto(id_fatto):
    with _blocco:
        lista = fatti()
        nuova = [f for f in lista if f["id"] != id_fatto]
        _scrivi(FILE_FATTI, nuova)
    return len(lista) - len(nuova)


def dimentica(argomento):
    """Elimina i fatti che contengono TUTTE le parole dell'argomento."""
    parole = [p for p in _norm(argomento).split() if len(p) > 2]
    if not parole:
        return 0
    with _blocco:
        lista = fatti()
        nuova = [f for f in lista if not all(p in _norm(f["testo"]) for p in parole)]
        _scrivi(FILE_FATTI, nuova)
    return len(lista) - len(nuova)


# =========================== COMANDI INSEGNATI ===========================
def alias():
    return _leggi(FILE_ALIAS, [])


def aggiungi_alias(frase, comando):
    frase_n = _norm(frase)
    with _blocco:
        lista = [a for a in alias() if _norm(a["frase"]) != frase_n]
        a = {"id": _id(), "frase": frase.strip(), "comando": comando.strip()}
        lista.append(a)
        _scrivi(FILE_ALIAS, lista)
        # chi era tra i "non capiti" ora e' capito
        _scrivi(FILE_NON_CAPITI, [x for x in non_capiti() if _norm(x["frase"]) != frase_n])
    return a


def elimina_alias(id_o_frase):
    n = _norm(id_o_frase)
    with _blocco:
        lista = alias()
        nuova = [a for a in lista if a["id"] != id_o_frase and _norm(a["frase"]) != n]
        _scrivi(FILE_ALIAS, nuova)
    return len(lista) - len(nuova)


def comando_per(frase_normalizzata):
    for a in alias():
        if _norm(a["frase"]) == frase_normalizzata:
            return a["comando"]
    return None


# ============================== NON CAPITI ==============================
def non_capiti():
    return _leggi(FILE_NON_CAPITI, [])


def registra_non_capito(frase):
    with _blocco:
        lista = non_capiti()
        n = _norm(frase)
        esistente = next((x for x in lista if _norm(x["frase"]) == n), None)
        if esistente:
            esistente["volte"] += 1
            esistente["ora"] = datetime.now().isoformat(timespec="minutes")
        else:
            lista.append({"id": _id(), "frase": frase.strip(), "volte": 1,
                          "ora": datetime.now().isoformat(timespec="minutes")})
        _scrivi(FILE_NON_CAPITI, sorted(lista, key=lambda x: x["ora"])[-50:])


def elimina_non_capito(id_frase):
    with _blocco:
        _scrivi(FILE_NON_CAPITI, [x for x in non_capiti() if x["id"] != id_frase])


# ================================ DOCUMENTI ================================
def _testo_pdf(percorso):
    from pypdf import PdfReader

    pagine = []
    for i, pagina in enumerate(PdfReader(percorso).pages, 1):
        t = (pagina.extract_text() or "").strip()
        if t:
            pagine.append(f"PAGINA {i}\n\n{t}")
    return "\n\n".join(pagine)


def _testo_docx(percorso):
    with zipfile.ZipFile(percorso) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    xml = re.sub(r"</w:p>", "\n\n", xml)
    xml = re.sub(r"<w:tab/>", " ", xml)
    testo = re.sub(r"<[^>]+>", "", xml)
    import html

    return html.unescape(testo)


def nome_sicuro(nome):
    base, est = os.path.splitext(os.path.basename(nome))
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", base).strip("_")[:60] or "documento"
    return base, est.lower()


def aggiungi_documento(nome_file, dati_bytes):
    """Converte il file in testo e lo salva tra i documenti. Restituisce (nome, caratteri)."""
    base, est = nome_sicuro(nome_file)
    if est not in ESTENSIONI:
        raise ValueError(f"Formato non supportato ({est or 'nessuno'}). Usa: {', '.join(ESTENSIONI)}.")
    if len(dati_bytes) > MAX_MB * 1024 * 1024:
        raise ValueError(f"File troppo grande (massimo {MAX_MB} MB).")
    os.makedirs(CARTELLA_DOCUMENTI, exist_ok=True)
    tmp = os.path.join(CARTELLA_DOCUMENTI, f".caricamento{est}")
    with open(tmp, "wb") as f:
        f.write(dati_bytes)
    try:
        if est == ".pdf":
            testo = _testo_pdf(tmp)
        elif est == ".docx":
            testo = _testo_docx(tmp)
        else:
            testo = dati_bytes.decode("utf-8", errors="replace")
    finally:
        os.remove(tmp)
    testo = testo.replace("\r\n", "\n").strip()
    if len(testo) < 20:
        raise ValueError("Nel file non c'è testo leggibile (un PDF fatto di sole immagini/scansioni non si può leggere).")
    with open(os.path.join(CARTELLA_DOCUMENTI, base + ".txt"), "w", encoding="utf-8") as f:
        f.write(testo)
    return base, len(testo)


def documenti():
    os.makedirs(CARTELLA_DOCUMENTI, exist_ok=True)
    risultato = []
    for nome in sorted(os.listdir(CARTELLA_DOCUMENTI)):
        if nome.endswith(".txt"):
            p = os.path.join(CARTELLA_DOCUMENTI, nome)
            risultato.append({"nome": nome[:-4], "kb": round(os.path.getsize(p) / 1024),
                              "ora": datetime.fromtimestamp(os.path.getmtime(p)).isoformat(timespec="minutes")})
    return risultato


def elimina_documento(nome):
    base, _ = nome_sicuro(nome + ".txt")
    p = os.path.join(CARTELLA_DOCUMENTI, base + ".txt")
    if os.path.exists(p):
        os.remove(p)
        return 1
    return 0
