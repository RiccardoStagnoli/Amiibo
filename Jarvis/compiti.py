"""
Jarvis - Compiti ed esercizi richiesti dai professori.

1. Controlla Teams (chat, compiti assegnati), la posta della scuola e Gmail.
2. Se trova una richiesta di esercizi, prepara una BOZZA:
   - risolve gli esercizi che sa risolvere (calcoli esatti, con passaggi);
   - per gli esercizi da fare SU FOGLIO spiega chiaramente cosa fare e prepara
     CONSIGLI (formule, metodo, errori da evitare) + la soluzione per controllo.
3. NON invia mai niente da solo: prima te la deve far vedere ("mostra esercizio 1")
   e poi tu devi dire chiaramente "manda esercizio 1".
"""

import json
import os
import re
import threading
import time
from datetime import datetime

import config

CARTELLA = os.path.dirname(os.path.abspath(__file__))
FILE_COMPITI = os.path.join(CARTELLA, "dati", "compiti.json")
_blocco = threading.Lock()

# ------------------------------ riconoscimento ------------------------------
RX_FORTE = re.compile(r"\b(eserciz[io]|compit[oi]|problem[ai]|verifica|interrogazion|consegn[ae]|homework)\w*", re.I)
RX_DEBOLE = re.compile(r"\b(svolg|risolv|fate|fare|calcol|entro|per domani|per luned|per marted|per mercoled|per gioved|"
                       r"per venerd|per sabato|pag\.?|pagina|n\.|numer[oi]|scadenza|da consegnare)\w*", re.I)
RX_FOGLIO = re.compile(r"(su|sul|nel) (foglio|quaderno|protocollo|libro)|a mano|fotograf|foto\b|scansion|cartace|"
                       r"in classe|disegn|da consegnare (in|a) (classe|mano)|sul libro", re.I)
RX_DIGITALE = re.compile(r"rispondete (qui|in chat|alla mail)|inviat[ei]|mandat[ei]|via (mail|email|teams)|"
                         r"in (questa )?chat|scrivete (qui|la risposta)|rispondi(te)? a questo", re.I)

CONSIGLI = {
    "moto uniformemente accelerato": [
        "Scrivi i dati: v0, a, t, s, v. 'Parte da fermo' significa v0 = 0; 'si ferma' significa v = 0.",
        "Formule: v = v0 + a·t ; s = v0·t + ½·a·t² ; v² = v0² + 2·a·s.",
        "Converti i km/h in m/s dividendo per 3,6.",
        "In una frenata l'accelerazione viene negativa: non è un errore."],
    "moto rettilineo uniforme": ["Formula: s = v·t (velocità costante).", "Unità coerenti: m, s, m/s (km/h ÷ 3,6)."],
    "dinamica": ["Seconda legge di Newton: F = m·a (N = kg·m/s²).", "Peso: P = m·g con g = 9,81 m/s².",
                 "Se le forze sono più di una, prima trova la forza risultante."],
    "lavoro ed energia": ["L = F·s ; Ec = ½·m·v² ; Ep = m·g·h ; P = L/t.", "Rendimento η = Pu/Pa (sempre minore di 1, cioè 100%).",
                          "Se non ci sono attriti l'energia si conserva: Ep iniziale = Ec finale."],
    "caduta libera": ["v0 = 0 e a = g = 9,81 m/s².", "h = ½·g·t² ; v = g·t ; v = √(2·g·h)."],
    "moto circolare": ["v = ω·r ; ω = 2π·f ; T = 1/f ; giri/min ÷ 60 = giri al secondo (f).",
                       "Potenza di un albero: P = M·ω (M in N·m, ω in rad/s)."],
    "leve e momenti": ["Momento M = F·b (forza × braccio).", "Equilibrio della leva: F1·b1 = F2·b2.",
                       "Leva vantaggiosa se il braccio della forza motrice è più lungo."],
    "trasmissioni": ["Rapporto i = n1/n2 = z2/z1.", "La ruota con più denti gira più lenta.",
                     "Con gli ingranaggi la coppia aumenta quando i giri diminuiscono (a meno del rendimento)."],
    "pressione e fluidi": ["p = F/A (Pa = N/m²) ; Stevino p = ρ·g·h.", "Converti cm² in m² dividendo per 10 000."],
    "elettrotecnica": ["Ohm: V = R·I ; potenza P = V·I = R·I².", "Energia: E = P·t (in kWh se P in kW e t in ore)."],
    "resistenze in serie": ["Serie: Rt = R1 + R2 + ... ; la corrente è la stessa in tutte.", "La tensione si divide: Vi = Ri·I."],
    "resistenze in parallelo": ["Parallelo: 1/Rt = 1/R1 + 1/R2 + ... ; con due: Rt = R1·R2/(R1+R2).",
                                "Rt è sempre più piccola della resistenza più piccola."],
    "calorimetria": ["Q = m·c·ΔT ; acqua c = 4186 J/(kg·K).", "ΔT è la differenza tra temperatura finale e iniziale."],
    "equazione": ["Porta tutto a sinistra e ordina per grado.", "2° grado: Δ = b² − 4ac ; x = (−b ± √Δ)/(2a).",
                  "Verifica sostituendo le soluzioni nell'equazione iniziale."],
    "sistema": ["Metodo di sostituzione: ricava una variabile e sostituiscila.", "Oppure riduzione: somma/sottrai le equazioni."],
    "derivata": ["Regole: (xⁿ)' = n·xⁿ⁻¹ ; prodotto (f·g)' = f'·g + f·g' ; quoziente (f/g)' = (f'g − fg')/g².",
                 "Funzioni composte: deriva quella esterna e moltiplica per la derivata di quella interna."],
    "integrale": ["∫xⁿ dx = xⁿ⁺¹/(n+1) + C (n ≠ −1) ; ∫1/x dx = ln|x| + C.", "Integrale definito: F(b) − F(a)."],
    "limite": ["Prova prima a sostituire il valore.", "Forme 0/0: scomponi e semplifica, oppure limiti notevoli (sin x / x → 1)."],
    "generale": ["Leggi il testo due volte e sottolinea i dati con le unità di misura.",
                 "Scrivi in ordine: Dati → Incognita → Formula → Calcoli → Risultato con unità.",
                 "Controlla che il risultato abbia senso (ordine di grandezza, segno, unità)."],
}
ARGOMENTI_PAROLE = [
    (r"accelera|frena|parte da ferm|velocità finale", "moto uniformemente accelerato"),
    (r"velocità costante|moto uniforme", "moto rettilineo uniforme"), (r"cade|caduta", "caduta libera"),
    (r"forza|newton|massa", "dinamica"), (r"lavoro|energia|potenza|rendimento", "lavoro ed energia"),
    (r"giri|ruota|angolare|circolare", "moto circolare"), (r"leva|braccio|momento|coppia", "leve e momenti"),
    (r"ingranagg|denti|trasmission|pulegg", "trasmissioni"), (r"pression|fluid|stevino|densità", "pressione e fluidi"),
    (r"parallelo", "resistenze in parallelo"), (r"\bserie\b", "resistenze in serie"),
    (r"resistenz|corrente|tensione|ohm|volt|ampere", "elettrotecnica"), (r"calore|temperatura", "calorimetria"),
    (r"sistema", "sistema"), (r"equazion|risolvi", "equazione"), (r"deriv", "derivata"), (r"integr", "integrale"),
    (r"limite", "limite"),
]


def e_richiesta_esercizi(testo):
    t = testo or ""
    punti = 2 * len(RX_FORTE.findall(t)) + len(RX_DEBOLE.findall(t))
    return punti >= 3 or (bool(RX_FORTE.search(t)) and punti >= 2)


def argomenti(testo, risultato=None):
    trovati = []
    if risultato:
        for p in risultato.get("passi", []):
            if p.startswith("Argomento: "):
                trovati += [a.strip() for a in p[11:].split(",")]
    for schema, arg in ARGOMENTI_PAROLE:
        if re.search(schema, testo, re.I) and arg not in trovati:
            trovati.append(arg)
    return [a for a in trovati if a in CONSIGLI][:3] or ["generale"]


def dividi_esercizi(testo):
    """Separa gli esercizi numerati ('1)', 'Es. 2:', 'n. 3 -'); altrimenti le frasi con una richiesta."""
    pezzi = re.split(r"(?:^|\n|\s)(?:es(?:ercizio)?\.?\s*|n\.\s*)?(\d{1,2})\s*[\)\.:\-]\s+(?=\S)", testo)
    esercizi = []
    if len(pezzi) >= 3:
        for i in range(1, len(pezzi) - 1, 2):
            corpo = pezzi[i + 1].strip()
            if len(corpo) > 3:
                esercizi.append(corpo)
    if not esercizi:
        frasi = re.split(r"(?<=[.?!])\s+|\n+", testo)
        esercizi = [f.strip() for f in frasi if re.search(r"\?|calcola|risolvi|determina|trova|deriva|integra|=", f, re.I)
                    and len(f.strip()) > 5]
    return esercizi[:15]


def riferimenti_libro(testo):
    return [m.group(0).strip(" ,") for m in re.finditer(
        r"pag(?:ina|\.)?\s*\d+(?:\s*(?:,|\s)\s*(?:n\.?|nn\.?|nr\.?|es\.?|esercizi?|numer[oi])\s*\d+(?:\s*(?:,|e|-)\s*\d+)*)?",
        testo, re.I)]


def prepara(testo):
    """Analizza la richiesta e prepara soluzioni e consigli per ogni esercizio."""
    import esercizi as es

    elenco = []
    for e in dividi_esercizi(testo):
        voce = {"testo": e, "risolto": False, "risultato": None, "passi": [], "consigli": []}
        tentativi = [e]
        if "=" in e and not re.search(r"\d\s*(m|kg|s|n|j|w|v|a)\b", e, re.I):
            tentativi.append("risolvi " + re.sub(r"^.*?:\s*", "", e))
        for t in tentativi:
            try:
                r = es.risolvi_esercizio(t)
                voce.update(risolto=True, risultato=r["risultato"], passi=r["passi"])
                break
            except Exception:
                continue
        for arg in argomenti(e, {"passi": voce["passi"]}):
            voce["consigli"] += CONSIGLI[arg]
        elenco.append(voce)
    return elenco


def _testo_risposta(bozza):
    righe = []
    for i, e in enumerate(bozza["esercizi"], 1):
        righe.append(f"Esercizio {i}: {e['testo']}")
        if e["risolto"]:
            righe += [f"  {p}" for p in e["passi"] if not p.startswith(("Argomento", "Dati (in"))]
            righe.append(f"  Risultato: {e['risultato']}")
        else:
            righe.append("  (da completare)")
        righe.append("")
    return "\n".join(righe).strip()


# --------------------------------- archivio ---------------------------------
def _leggi():
    try:
        with open(FILE_COMPITI, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"bozze": [], "visti": []}


def _scrivi(d):
    os.makedirs(os.path.dirname(FILE_COMPITI), exist_ok=True)
    tmp = FILE_COMPITI + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, FILE_COMPITI)


def bozze(tutte=False):
    b = _leggi()["bozze"]
    return b if tutte else [x for x in b if x["stato"] == "da_rivedere"]


def trova(numero_o_id):
    lista = bozze()
    if isinstance(numero_o_id, int) or (str(numero_o_id).isdigit() and len(str(numero_o_id)) <= 3):
        n = int(numero_o_id)  # numero nell'elenco (1, 2, 3...)
        return lista[n - 1] if 1 <= n <= len(lista) else None
    return next((x for x in _leggi()["bozze"] if x["id"] == numero_o_id), None)


def _aggiorna(id_bozza, **campi):
    with _blocco:
        d = _leggi()
        for x in d["bozze"]:
            if x["id"] == id_bozza:
                x.update(campi)
        _scrivi(d)


def crea_bozza(fonte, origine_id, da, titolo, testo, scadenza=None, destinazione=None, url=None):
    esercizi = prepara(testo)
    tipo = "digitale" if RX_DIGITALE.search(testo) and not RX_FOGLIO.search(testo) else "foglio"
    if fonte == "classeviva":
        tipo = "foglio"  # da ClasseViva non si consegna niente: Jarvis prepara spiegazione e consigli
    bozza = {
        "id": f"{int(time.time() * 1000)}", "fonte": fonte, "origine_id": origine_id, "da": da, "titolo": titolo,
        "testo": testo, "scadenza": scadenza, "destinazione": destinazione, "url": url, "tipo": tipo,
        "esercizi": esercizi, "libro": riferimenti_libro(testo), "stato": "da_rivedere", "mostrato": False,
        "creata": datetime.now().isoformat(timespec="minutes"),
        "cosa_fare": cosa_fare(testo, esercizi, tipo),
    }
    bozza["risposta"] = _testo_risposta(bozza)
    with _blocco:
        d = _leggi()
        d["bozze"].append(bozza)
        d["visti"] = (d["visti"] + [origine_id])[-2000:]
        _scrivi(d)
    return bozza


def cosa_fare(testo, esercizi, tipo):
    passi = []
    scad = re.search(r"\b(entro|per)\s+(domani|dopodomani|(?:il |lo )?luned[iì]|(?:il |lo )?marted[iì]|(?:il |lo )?mercoled[iì]|"
                     r"(?:il |lo )?gioved[iì]|(?:il |lo )?venerd[iì]|sabato|domenica|la prossima lezione|il \d{1,2}(?:/\d{1,2})?|\d{1,2}/\d{1,2})",
                     testo, re.I)
    if scad:
        passi.append(f"Scadenza indicata: {scad.group(0).strip()}.")
    libro = riferimenti_libro(testo)
    if libro:
        passi.append("Dal libro: " + "; ".join(x.strip() for x in libro) + ". Se mi scrivi il testo dell'esercizio, lo preparo.")
    if esercizi:
        passi.append(f"Esercizi da svolgere: {len(esercizi)}.")
    if tipo == "foglio":
        passi.append("Da fare su foglio/quaderno: scrivi Dati, Formula, Calcoli e Risultato con le unità per ogni esercizio.")
        if re.search(r"fotograf|foto|scansion", testo, re.I):
            passi.append("Poi va fotografato e consegnato come chiesto dal professore.")
    else:
        passi.append("Da consegnare in digitale: la bozza di risposta è pronta. Controllala prima di dire 'manda esercizio'.")
    return passi


# --------------------------------- scansione ---------------------------------
def scansiona():
    """Cerca nuove richieste di esercizi. Restituisce (nuove_bozze, avvisi)."""
    d = _leggi()
    visti = set(d["visti"])
    nuove, avvisi = [], []
    import teams_reader

    if teams_reader.configurato():
        try:
            for m in teams_reader.nuovi_messaggi(includi_visti=True)["messaggi"]:
                if m["id"] not in visti and e_richiesta_esercizi(m["testo"]):
                    nuove.append(crea_bozza("teams_chat", m["id"], m["da"], m["dove"], m["testo"], destinazione=m.get("chat_id")))
            r = teams_reader.compiti_assegnati()
            avvisi += r["avvisi"]
            for c in r["compiti"]:
                if c["id"] not in visti:
                    nuove.append(crea_bozza("teams_compito", c["id"], "Teams (compito)", c["titolo"], c["titolo"] + ". " + c["testo"],
                                            scadenza=c["scadenza"], url=c["url"]))
            for m in teams_reader.posta_scuola():
                testo = f"{m['oggetto']}. {m['testo']}"
                if m["id"] not in visti and e_richiesta_esercizi(testo):
                    nuove.append(crea_bozza("posta_scuola", m["id"], m["da"], m["oggetto"], testo, destinazione=m["id"]))
        except Exception as e:
            avvisi.append(f"Teams: {e}")
    try:
        import classeviva

        if classeviva.configurato():
            for e in classeviva.compiti(14):
                if e["id"] in visti or not e["testo"]:
                    continue
                b = crea_bozza("classeviva", e["id"], e["docente"] or "ClasseViva", f"{e['materia']} (ClasseViva)",
                               e["testo"], scadenza=e["inizio"])
                nuove.append(b)
    except Exception as e:
        avvisi.append(f"ClasseViva: {e}")
    try:
        import gmail_reader

        domini = [x.lower() for x in getattr(config, "COMPITI_MITTENTI", [])]
        for m in gmail_reader.elenca_email("is:unread newer_than:14d", 25):
            if m["id"] in visti:
                continue
            mittente = m["mittente"].lower()
            dal_prof = any(x in mittente for x in domini)
            testo = f"{m['oggetto']}. {m['anteprima']}"
            if (dal_prof and e_richiesta_esercizi(testo)) or (not domini and e_richiesta_esercizi(testo) and RX_FORTE.search(m["oggetto"])):
                completo = gmail_reader.leggi_email(m["id"])
                nuove.append(crea_bozza("gmail", m["id"], m["mittente"], m["oggetto"], f"{m['oggetto']}. {completo['corpo'][:4000]}",
                                        destinazione=m["id"]))
    except Exception as e:
        avvisi.append(f"Gmail: {e}")
    return nuove, avvisi


# ----------------------------------- invio -----------------------------------
def segna_mostrata(id_bozza):
    _aggiorna(id_bozza, mostrato=True)


def modifica_risposta(id_bozza, testo):
    _aggiorna(id_bozza, risposta=testo, mostrato=True)


def scarta(id_bozza):
    _aggiorna(id_bozza, stato="scartata")


def invia(id_bozza):
    """Invia la bozza. Va chiamata SOLO dopo il comando esplicito 'manda esercizio'."""
    b = trova(id_bozza)
    if not b or b["stato"] != "da_rivedere":
        raise ValueError("Bozza non trovata o già inviata.")
    if not b["mostrato"]:
        raise ValueError("Prima te la devo far vedere: 'mostra esercizio' oppure aprila nella sezione Compiti.")
    testo = b["risposta"].strip()
    if not testo:
        raise ValueError("La risposta è vuota.")
    if b["fonte"] == "teams_chat" and b["destinazione"]:
        import teams_reader

        teams_reader.invia_in_chat(b["destinazione"], testo)
        dove = f"chat Teams ({b['titolo']})"
    elif b["fonte"] == "posta_scuola":
        import teams_reader

        teams_reader.rispondi_mail_scuola(b["destinazione"], testo)
        dove = f"email della scuola a {b['da']}"
    elif b["fonte"] == "gmail":
        import gmail_reader

        dove = "email a " + gmail_reader.invia_risposta(b["destinazione"], testo)
    elif b["fonte"] == "classeviva":
        raise ValueError("Da ClasseViva non si può inviare niente: è un compito da fare e consegnare come chiede il professore.")
    else:
        raise ValueError("I compiti di Teams (Assignments) si consegnano dall'app Teams: apri il link del compito, "
                         "incolla la risposta o carica la foto del foglio.")
    _aggiorna(b["id"], stato="inviata", inviata=datetime.now().isoformat(timespec="minutes"))
    return dove
