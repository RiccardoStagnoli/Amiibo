"""
Jarvis - Ritratto e abitudini: cosa Jarvis ha capito di te dai dati che ha.

Usa SOLO dati locali: comandi dati a Jarvis (registro), gusti, agenda, compiti, musica.
- abitudini: cosa fai di solito a una certa ora (es. "alle 21 metti musica su Spotify");
- suggerimenti: quando arriva quell'ora te lo propone ("vuoi che lo faccia? di' 'sì, fallo'");
- ritratto: interessi principali, come cambiano, orari in cui sei piu' attivo, materie
  con piu' compiti/verifiche, ecc.
Sono statistiche sui tuoi dati: non opinioni ne' diagnosi.
"""

import json
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import config

CARTELLA = os.path.dirname(os.path.abspath(__file__))
FILE_SUGGERIMENTI = os.path.join(CARTELLA, "dati", "suggerimenti.json")
NON_ABITUDINI = re.compile(r"^(si fallo|sì fallo|si|no|aiuto|che ore sono|rapporto|ritratto|chi sono|cosa sai di me|"
                           r"passo successivo|passo precedente|ripeti|manda esercizio|mostra esercizio)", re.I)


def _comandi(giorni=45):
    import extra

    limite = datetime.now() - timedelta(days=giorni)
    risultato = []
    for r in extra.registro(5000):
        if r.get("tipo") != "comando":
            continue
        try:
            quando = datetime.fromisoformat(r["ora"])
        except (KeyError, ValueError):
            continue
        testo, _, esito = r.get("dettaglio", "").rpartition(" -> ")
        if quando >= limite and esito == "ok" and testo:
            risultato.append((quando, _normale(testo)))
    return risultato


def _normale(testo):
    from comandi import normalizza

    return re.sub(r"^(ehi |ok )?jarvis[,:]? ?", "", normalizza(testo))


def abitudini(minimo_giorni=3, giorni=45):
    """Comandi ripetuti nella stessa fascia oraria in almeno 'minimo_giorni' giorni diversi."""
    per_fascia = defaultdict(set)   # (comando, ora) -> giorni distinti
    for quando, testo in _comandi(giorni):
        if NON_ABITUDINI.match(testo):
            continue
        per_fascia[(testo, quando.hour)].add(quando.date())
    trovate = []
    for (testo, ora), giorni_set in per_fascia.items():
        if len(giorni_set) >= minimo_giorni:
            feriali = sum(1 for g in giorni_set if g.weekday() < 5)
            trovate.append({"comando": testo, "ora": ora, "volte": len(giorni_set),
                            "quando": "nei giorni feriali" if feriali == len(giorni_set) else
                            ("nel weekend" if feriali == 0 else "di solito")})
    trovate.sort(key=lambda x: (-x["volte"], x["ora"]))
    return trovate


def _stato_suggerimenti():
    try:
        with open(FILE_SUGGERIMENTI, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"ultimo": None, "fatti_oggi": {}, "rifiutati": {}}


def _salva_suggerimenti(s):
    os.makedirs(os.path.dirname(FILE_SUGGERIMENTI), exist_ok=True)
    with open(FILE_SUGGERIMENTI, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False)


def suggerimento_adesso():
    """Se adesso e' l'ora di un'abitudine non ancora fatta oggi, propone di farla (una sola volta al giorno)."""
    if not getattr(config, "SUGGERIMENTI_ABITUDINI", True):
        return None
    adesso = datetime.now()
    oggi = adesso.date().isoformat()
    s = _stato_suggerimenti()
    gia_proposti = set(s["fatti_oggi"].get(oggi, []))
    fatti_oggi = {t for q, t in _comandi(1) if q.date() == adesso.date()}
    for a in abitudini():
        if a["ora"] != adesso.hour or a["comando"] in gia_proposti or a["comando"] in fatti_oggi:
            continue
        if a["quando"] == "nei giorni feriali" and adesso.weekday() >= 5:
            continue
        if a["quando"] == "nel weekend" and adesso.weekday() < 5:
            continue
        if s["rifiutati"].get(a["comando"], 0) >= 3:  # rifiutato 3 volte: smetto di proporlo
            continue
        s["fatti_oggi"] = {oggi: list(gia_proposti | {a["comando"]})}
        s["ultimo"] = a["comando"]
        _salva_suggerimenti(s)
        return a
    return None


def ultimo_suggerimento(consuma=True):
    s = _stato_suggerimenti()
    c = s.get("ultimo")
    if consuma and c:
        s["ultimo"] = None
        _salva_suggerimenti(s)
    return c


def rifiuta_suggerimento():
    s = _stato_suggerimenti()
    c = s.get("ultimo")
    if c:
        s["rifiutati"][c] = s["rifiutati"].get(c, 0) + 1
        s["ultimo"] = None
        _salva_suggerimenti(s)
    return c


def ritratto():
    """Testo e dati del ritratto."""
    import gusti

    parti, dati = [], {}
    interessi = gusti.interessi(15)
    per_cat = Counter()
    for i in interessi:
        per_cat[i["categoria"]] += i["peso"]
    if interessi:
        principali = [c for c, _ in per_cat.most_common(4) if c != "altro"]
        parti.append("Interessi principali: " + (", ".join(principali) if principali else "ancora pochi dati") + ". "
                     + "In particolare: " + ", ".join(i["termine"] for i in interessi[:8]) + ".")
    # interessi in crescita: segnali degli ultimi 7 giorni rispetto ai 30 precedenti
    storico = gusti.storico()
    adesso = time.time()
    recenti = Counter(x["categoria"] for x in storico if adesso - x["ora"] < 7 * 86400)
    prima = Counter(x["categoria"] for x in storico if 7 * 86400 <= adesso - x["ora"] < 37 * 86400)
    crescita = [c for c, n in recenti.items() if c != "altro" and n >= 3 and n > 1.5 * (prima.get(c, 0) / 4.3 + 0.5)]
    if crescita:
        parti.append("Ultimamente ti stai interessando di più a: " + ", ".join(crescita) + ".")
    # orari
    comandi = _comandi(45)
    if len(comandi) >= 10:
        ore = Counter(q.hour for q, _ in comandi)
        picco = max(range(24), key=lambda h: ore.get(h, 0) + ore.get((h + 1) % 24, 0))
        parti.append(f"Sei più attivo tra le {picco}:00 e le {(picco + 2) % 24}:00.")
        tipi = Counter(t.split()[0] for _, t in comandi if t)
        parti.append("Cosa chiedi più spesso: " + ", ".join(f"{p} ({n})" for p, n in tipi.most_common(4)) + ".")
        dati["ore"] = dict(ore)
    ab = abitudini()
    if ab:
        parti.append("Abitudini: " + "; ".join(f"{a['quando']} verso le {a['ora']} \"{a['comando']}\"" for a in ab[:5]) + ".")
    dati["abitudini"] = ab
    # scuola
    try:
        import agenda

        impegni, _ = agenda.prossimi(30)
        materie = Counter(i["titolo"].split(" ", 1)[1] for i in impegni if i.get("fonte") == "ClasseViva" and " " in i["titolo"])
        if materie:
            parti.append("Materie con più impegni nel prossimo mese: " + ", ".join(f"{m} ({n})" for m, n in materie.most_common(3)) + ".")
    except Exception:
        pass
    # musica
    try:
        import spotify_jarvis

        if spotify_jarvis.configurato():
            artisti = spotify_jarvis.artisti_preferiti()
            if artisti:
                parti.append("Su Spotify ascolti soprattutto: " + ", ".join(artisti[:5]) + ".")
    except Exception:
        pass
    if not parti:
        parti.append("Dati insufficienti per verificare: usami ancora un po' e dimmi cosa ti piace ('mi piace ...').")
    dati["interessi"] = interessi
    return " ".join(parti), dati
