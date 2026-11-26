"""
Jarvis - Riconoscimento della scrittura a mano, lettera per lettera, che IMPARA.

Come funziona:
 1. L'immagine (disegno sul pannello o foto) viene divisa in righe, parole e lettere.
 2. Ogni lettera viene trasformata in un "modello" (forma + direzione dei tratti)
    e confrontata con gli esempi gia' imparati (i piu' simili votano).
 3. Ogni lettera e ogni parola hanno una CERTEZZA. Sotto il 90% Jarvis prova a
    correggere con le parole che conosce; se resta in dubbio, TE LO CHIEDE.
 4. Quando confermi o correggi una parola, Jarvis salva le lettere come nuovi
    esempi: piu' scrivi, piu' riconosce la TUA calligrafia (i pattern che si ripetono).

Partenza: esempi generati dai caratteri di Windows simili alla scrittura a mano
(Ink Free, Segoe Print, Comic Sans...) + la modalita' "Allenamento" del pannello.
Limite: lettere staccate (stampatello o corsivo poco legato) funzionano molto
meglio del corsivo tutto attaccato.
"""

import base64
import io
import json
import os
import re
import threading
import time
from collections import Counter, defaultdict

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

CARTELLA = os.path.dirname(os.path.abspath(__file__))
CARTELLA_DATI = os.path.join(CARTELLA, "dati", "scrittura")
FILE_CAMPIONI = os.path.join(CARTELLA_DATI, "campioni.npz")
FILE_PAROLE = os.path.join(CARTELLA_DATI, "parole.json")
LATO = 24
SOGLIA = 0.90
CARATTERI = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789àèéìòù"
# coppie che a mano hanno la stessa forma: si decide con l'altezza della lettera
STESSA_FORMA = {c: c.lower() for c in "cCoOsSuUvVwWxXzZpPkK"}
FONT_WINDOWS = ["Inkfree.ttf", "segoepr.ttf", "comic.ttf", "segoeprb.ttf", "arial.ttf", "calibri.ttf", "verdana.ttf",
                "tahoma.ttf", "georgia.ttf", "times.ttf"]
_blocco = threading.Lock()
_sessioni = {}  # id -> dati delle parole riconosciute (per imparare dalle correzioni)


# ============================== IMMAGINE ==============================
def _carica_immagine(dati):
    """Accetta byte di un file oppure una stringa data:image/...;base64."""
    if isinstance(dati, str):
        dati = base64.b64decode(dati.split(",", 1)[1] if "," in dati else dati)
    img = Image.open(io.BytesIO(dati))
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA"):
        sfondo = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(sfondo, img.convert("RGBA"))
    img = img.convert("L")
    if max(img.size) > 1600:
        img.thumbnail((1600, 1600))
    return img


def _binarizza(img):
    """Inchiostro = True. Soglia di Otsu; funziona anche con foto su carta."""
    a = np.asarray(img.filter(ImageFilter.MedianFilter(3)), dtype=np.uint8)
    istogramma = np.bincount(a.ravel(), minlength=256).astype(float)
    tot = a.size
    somma = np.dot(np.arange(256), istogramma)
    peso_b = somma_b = 0.0
    migliore, soglia = -1, 128
    for t in range(256):
        peso_b += istogramma[t]
        if peso_b == 0 or peso_b == tot:
            continue
        somma_b += t * istogramma[t]
        mb, mf = somma_b / peso_b, (somma - somma_b) / (tot - peso_b)
        var = peso_b * (tot - peso_b) * (mb - mf) ** 2
        if var > migliore:
            migliore, soglia = var, t
    inchiostro = a < soglia
    if inchiostro.mean() > 0.5:  # testo chiaro su sfondo scuro
        inchiostro = ~inchiostro
    return inchiostro


def _componenti(maschera):
    """Componenti connesse (8-vicini). Restituisce liste di (y0, y1, x0, x1, pixel)."""
    h, w = maschera.shape
    etichette = np.zeros((h, w), dtype=np.int32)
    risultato = []
    ys, xs = np.nonzero(maschera)
    n = 0
    for y, x in zip(ys, xs):
        if etichette[y, x]:
            continue
        n += 1
        pila = [(y, x)]
        etichette[y, x] = n
        pixel = []
        while pila:
            cy, cx = pila.pop()
            pixel.append((cy, cx))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and maschera[ny, nx] and not etichette[ny, nx]:
                        etichette[ny, nx] = n
                        pila.append((ny, nx))
        p = np.array(pixel)
        risultato.append({"y0": p[:, 0].min(), "y1": p[:, 0].max() + 1, "x0": p[:, 1].min(), "x1": p[:, 1].max() + 1,
                          "pixel": p})
    return risultato


def _righe(maschera):
    profilo = maschera.sum(axis=1)
    righe, dentro, inizio = [], False, 0
    soglia = max(1, profilo.max() * 0.02)
    for y, v in enumerate(profilo):
        if v >= soglia and not dentro:
            dentro, inizio = True, y
        elif v < soglia and dentro:
            dentro = False
            righe.append((inizio, y))
    if dentro:
        righe.append((inizio, len(profilo)))
    # unisce righe troppo vicine (puntini, accenti)
    unite = []
    for r in righe:
        if unite and r[0] - unite[-1][1] < max(4, (unite[-1][1] - unite[-1][0]) * 0.35):
            unite[-1] = (unite[-1][0], r[1])
        else:
            unite.append(r)
    return [r for r in unite if r[1] - r[0] >= 6]


def _dilata(m, passi=1):
    d = m.copy()
    for _ in range(passi):
        e = d.copy()
        e[1:, :] |= d[:-1, :]
        e[:-1, :] |= d[1:, :]
        e[:, 1:] |= d[:, :-1]
        e[:, :-1] |= d[:, 1:]
        d = e
    return d


def _glifi_della_riga(maschera, y0, y1):
    """Lettere di una riga, unendo i pezzi sovrapposti in verticale (i, j, accenti)."""
    parte = maschera[y0:y1]
    comp = []
    for c in _componenti(parte):
        p = c["pixel"][parte[c["pixel"][:, 0], c["pixel"][:, 1]]]
        if len(p) >= 6:
            comp.append({"y0": p[:, 0].min(), "y1": p[:, 0].max() + 1, "x0": p[:, 1].min(), "x1": p[:, 1].max() + 1, "pixel": p})
    comp.sort(key=lambda c: c["x0"])
    glifi = []
    for c in comp:
        if glifi:
            g = glifi[-1]
            sovrapp = min(g["x1"], c["x1"]) - max(g["x0"], c["x0"])
            if sovrapp > 0.5 * min(g["x1"] - g["x0"], c["x1"] - c["x0"]):
                g["pixel"] = np.vstack([g["pixel"], c["pixel"]])
                g["parti"] = g.get("parti", 1) + 1
                g.update(x0=min(g["x0"], c["x0"]), x1=max(g["x1"], c["x1"]), y0=min(g["y0"], c["y0"]), y1=max(g["y1"], c["y1"]))
                continue
        glifi.append(dict(c))
    if not glifi:
        return [], 0
    altezza_tipica = float(np.percentile([g["y1"] - g["y0"] for g in glifi], 40))
    divisi = glifi
    for g in divisi:
        g["y0"] += y0
        g["y1"] += y0
        g["pixel"] = g["pixel"] + np.array([y0, 0])
    return divisi, altezza_tipica


def _parole(glifi, xh=None):
    if not glifi:
        return []
    spazi = [b["x0"] - a["x1"] for a, b in zip(glifi, glifi[1:])]
    if not spazi:
        return [glifi]
    xh = xh or float(np.percentile([g["y1"] - g["y0"] for g in glifi], 40))
    # spazio tra parole: si dividono gli spazi in due gruppi ("tra lettere" e "tra parole")
    soglia = max(0.42 * xh, min(float(np.median(spazi)) * 2.2, 0.9 * xh))
    valori = np.array(sorted(spazi), float)
    if len(valori) >= 2:
        migliore, taglio = -1.0, None
        for k in range(1, len(valori)):
            a_, b_ = valori[:k], valori[k:]
            separazione = len(a_) * len(b_) * (b_.mean() - a_.mean()) ** 2
            if separazione > migliore:
                migliore, taglio = separazione, (a_.max() + b_.min()) / 2
        piccoli, grandi = valori[valori < taglio], valori[valori >= taglio]
        if len(piccoli) and grandi.mean() > max(2.0 * max(piccoli.mean(), 1.0), 0.22 * xh):
            soglia = min(soglia, taglio)
    parole, attuale = [], [glifi[0]]
    for s, g in zip(spazi, glifi[1:]):
        if s > soglia:
            parole.append(attuale)
            attuale = [g]
        else:
            attuale.append(g)
    parole.append(attuale)
    return parole


# ============================== CARATTERISTICHE ==============================
def _metriche_riga(glifi):
    """Altezza della x (lettere piccole) e riga di base stimate dalla riga scritta."""
    altezze = np.array([g["y1"] - g["y0"] for g in glifi], float)
    xh = float(np.percentile(altezze, 40)) if len(altezze) else 1.0
    base = float(np.median([g["y1"] for g in glifi])) if glifi else 0.0
    return max(xh, 1.0), base


def _metrica_glifo(g, xh, base):
    return ((g["y1"] - g["y0"]) / xh, (base - g["y0"]) / xh, (g["y1"] - base) / xh)


def _immagine_glifo(g):
    h, w = g["y1"] - g["y0"], g["x1"] - g["x0"]
    m = np.zeros((h, w), np.uint8)
    m[g["pixel"][:, 0] - g["y0"], g["pixel"][:, 1] - g["x0"]] = 255
    return m


def caratteristiche(m, metrica=(1.0, 1.0, 0.0), parti=1):
    """Vettore che descrive la forma: pixel normalizzati + direzioni dei tratti +
    posizione rispetto alla riga (altezza, quanto sale sopra la base, quanto scende sotto):
    e' cio' che distingue l da i, d da a, p da o."""
    h, w = m.shape
    lato = max(h, w)
    quadrato = np.zeros((lato, lato), np.uint8)
    quadrato[(lato - h) // 2:(lato - h) // 2 + h, (lato - w) // 2:(lato - w) // 2 + w] = m
    img = Image.fromarray(quadrato).resize((LATO - 4, LATO - 4), Image.BILINEAR)
    a = np.zeros((LATO, LATO), np.float32)
    a[2:-2, 2:-2] = np.asarray(img, np.float32) / 255.0
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255.0
    gy, gx = np.gradient(a)
    modulo = np.hypot(gx, gy)
    angolo = (np.arctan2(gy, gx) % np.pi) / np.pi * 8
    hog = np.zeros((4, 4, 8), np.float32)
    cella = LATO // 4
    for i in range(4):
        for j in range(4):
            mm = modulo[i * cella:(i + 1) * cella, j * cella:(j + 1) * cella].ravel()
            aa = angolo[i * cella:(i + 1) * cella, j * cella:(j + 1) * cella].ravel().astype(int) % 8
            hog[i, j] = np.bincount(aa, weights=mm, minlength=8)
    pixel = a[::2, ::2].ravel()
    rapporto = np.array([min(w / max(h, 1), 3.0) / 3.0], np.float32)
    altezza, sopra, sotto = (min(max(x, -1.0), 3.0) for x in metrica)
    posizione = np.array([altezza / 2.5, sopra / 2.5, sotto / 1.5], np.float32) * 0.9
    staccati = np.array([0.8 if parti > 1 else 0.0], np.float32)  # puntino della i/j, accenti
    v = np.concatenate([pixel / (np.linalg.norm(pixel) + 1e-6), hog.ravel() / (np.linalg.norm(hog) + 1e-6) * 1.4,
                        rapporto, posizione, staccati])
    return v.astype(np.float32)


# ============================== MEMORIA DEGLI ESEMPI ==============================
class Modello:
    def __init__(self):
        self.X = np.zeros((0, 0), np.float32)
        self.y = []
        self.origine = []  # "font" oppure "utente"
        self.carica()

    def carica(self):
        if os.path.exists(FILE_CAMPIONI):
            d = np.load(FILE_CAMPIONI, allow_pickle=False)
            self.X, self.y, self.origine = d["X"], list(d["y"]), list(d["origine"])
        else:
            self.X, self.y, self.origine = np.zeros((0, 0), np.float32), [], []

    def salva(self):
        os.makedirs(CARTELLA_DATI, exist_ok=True)
        tmp = FILE_CAMPIONI + ".tmp.npz"
        np.savez_compressed(tmp, X=self.X, y=np.array(self.y, dtype="<U2"), origine=np.array(self.origine, dtype="<U8"))
        os.replace(tmp, FILE_CAMPIONI)

    def aggiungi(self, vettori, etichette, origine="utente"):
        vettori = np.asarray(vettori, np.float32)
        if not len(vettori):
            return
        self.X = vettori if self.X.size == 0 else np.vstack([self.X, vettori])
        self.y += list(etichette)
        self.origine += [origine] * len(etichette)

    def conteggi(self):
        tot = Counter(self.y)
        utente = Counter(e for e, o in zip(self.y, self.origine) if o == "utente")
        return {"totale": len(self.y), "tuoi": sum(utente.values()), "per_lettera_tuoi": dict(utente),
                "lettere_note": len(tot)}

    def classifica(self, v, k=7):
        """Restituisce [(carattere, certezza)] ordinati. Gli esempi dell'utente pesano di piu'."""
        if not len(self.y):
            return [("?", 0.0)]
        d = np.linalg.norm(self.X - v, axis=1)
        vicini = np.argsort(d)[:k]
        voti = defaultdict(float)
        for i in vicini:
            peso = 1.0 / (d[i] + 1e-3) * (2.0 if self.origine[i] == "utente" else 1.0)
            voti[STESSA_FORMA.get(self.y[i], self.y[i])] += peso
        totale = sum(voti.values())
        classifica = sorted(((c, p / totale) for c, p in voti.items()), key=lambda x: -x[1])
        # distanza assoluta: se la forma non somiglia a niente, certezza bassa
        vicinanza = float(np.exp(-max(0.0, d[vicini[0]] - 0.35) * 2.5))
        return [(c, round(p * vicinanza, 3)) for c, p in classifica]


_modello = None


def modello():
    global _modello
    if _modello is None:
        _modello = Modello()
        if not _modello.y:
            genera_campioni_da_font()
    return _modello


def _font_disponibili():
    cartelle = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"), "/usr/share/fonts"]
    trovati = []
    for nome in FONT_WINDOWS:
        p = os.path.join(cartelle[0], nome)
        if os.path.exists(p):
            trovati.append(p)
    if not trovati:  # fuori da Windows (prove): qualsiasi font TrueType
        for radice, _, file in os.walk(cartelle[1]):
            trovati += [os.path.join(radice, f) for f in file if f.lower().endswith(".ttf")]
    return trovati[:12]


def _disegna_carattere(car, font_path, rotazione, spessore):
    font = ImageFont.truetype(font_path, 64)
    img = Image.new("L", (140, 160), 255)
    base = 110
    ImageDraw.Draw(img).text((30, base), car, font=font, fill=0, anchor="ls")
    img = img.rotate(rotazione, fillcolor=255, resample=Image.BILINEAR, center=(60, base))
    if spessore:
        img = img.filter(ImageFilter.MinFilter(3))
    a = np.asarray(img) < 128
    ys, xs = np.nonzero(a)
    if not len(ys):
        return None, None
    x_box = font.getbbox("x", anchor="ls")
    xh = max(1.0, float(x_box[3] - x_box[1]))
    y0, y1 = ys.min(), ys.max() + 1
    metrica = ((y1 - y0) / xh, (base - y0) / xh, (y1 - base) / xh)
    ritaglio = a[y0:y1, xs.min():xs.max() + 1]
    parti = len([c for c in _componenti(ritaglio) if len(c["pixel"]) >= 6])
    return (ritaglio * 255).astype(np.uint8), (metrica, parti)


def genera_campioni_da_font(font=None):
    """Esempi di partenza dai caratteri installati (varianti ruotate e piu' spesse)."""
    m = _modello if _modello is not None else Modello()
    vettori, etichette = [], []
    for f in font or _font_disponibili():
        for car in CARATTERI:
            for rot in (-6, 0, 6):
                for spessore in (False, True):
                    try:
                        g, info = _disegna_carattere(car, f, rot, spessore)
                    except OSError:
                        g = None
                    if g is not None:
                        vettori.append(caratteristiche(g, info[0], info[1]))
                        etichette.append(car)
    m.aggiungi(vettori, etichette, "font")
    m.salva()
    return len(etichette)


# ============================== VOCABOLARIO ==============================
def parole_note():
    try:
        with open(FILE_PAROLE, encoding="utf-8") as f:
            return Counter(json.load(f))
    except (OSError, ValueError):
        return Counter()


def _vocabolario():
    voc = parole_note()
    if not hasattr(_vocabolario, "base"):
        base = Counter()
        cartelle = [os.path.join(CARTELLA, "manuali"), os.path.join(CARTELLA, "dati", "documenti")]
        for c in cartelle:
            if os.path.isdir(c):
                for nome in os.listdir(c):
                    if nome.endswith(".txt"):
                        with open(os.path.join(c, nome), encoding="utf-8", errors="ignore") as f:
                            base.update(w.lower() for w in re.findall(r"[a-zA-ZàèéìòùÀÈÉÌÒÙ]{2,}", f.read()))
        _vocabolario.base = base
    tot = Counter(_vocabolario.base)
    for p, n in voc.items():
        tot[p] += n * 50  # le parole confermate da te contano molto di piu'
    return tot


def impara_parola(parola):
    parola = parola.strip().lower()
    if not re.fullmatch(r"[a-zàèéìòù0-9'-]{1,40}", parola):
        return
    with _blocco:
        voc = parole_note()
        voc[parola] += 1
        os.makedirs(CARTELLA_DATI, exist_ok=True)
        with open(FILE_PAROLE, "w", encoding="utf-8") as f:
            json.dump(dict(voc), f, ensure_ascii=False)


def _correggi_con_vocabolario(lettere):
    """Prova le parole note della stessa lunghezza compatibili con le alternative di ogni lettera."""
    voc = _vocabolario()
    n = len(lettere)
    candidati = []
    for parola, freq in voc.items():
        if len(parola) != n:
            continue
        punteggio, ok = 1.0, True
        for car, alternative in zip(parola, lettere):
            prob = dict((c.lower(), p) for c, p in alternative[:4]).get(car)
            if prob is None:
                ok = False
                break
            punteggio *= max(prob, 0.05)
        if ok:
            candidati.append((punteggio * (1 + np.log1p(freq) * 0.15), parola))
    candidati.sort(reverse=True)
    return candidati[:3]


# ============================== LETTERE ATTACCATE ==============================
LARGHE = set("mwMW")


def _sotto_glifo(g, a, b):
    sel = (g["pixel"][:, 1] >= g["x0"] + a) & (g["pixel"][:, 1] < g["x0"] + b)
    p = g["pixel"][sel]
    if len(p) < 6:
        return None
    return {"y0": p[:, 0].min(), "y1": p[:, 0].max() + 1, "x0": p[:, 1].min(), "x1": p[:, 1].max() + 1, "pixel": p,
            "parti": 1, "diviso": True}


def _tagli(g, xh):
    """Possibili punti di taglio: colonne con poco inchiostro (dove due lettere si toccano)."""
    w = g["x1"] - g["x0"]
    if w <= 1.25 * xh:
        return [0, w]
    maschera = np.zeros((g["y1"] - g["y0"], w), bool)
    maschera[g["pixel"][:, 0] - g["y0"], g["pixel"][:, 1] - g["x0"]] = True
    profilo = maschera.sum(axis=0).astype(float)
    liscio = np.convolve(profilo, np.ones(3) / 3, mode="same")
    soglia = max(1.0, 0.5 * float(np.median(profilo[profilo > 0])))
    tagli = [0]
    for x in range(2, w - 2):
        if liscio[x] <= soglia and liscio[x] <= liscio[x - 1] and liscio[x] <= liscio[x + 1]:
            if x - tagli[-1] >= max(2, 0.15 * xh):
                tagli.append(x)
    tagli.append(w)
    if len(tagli) > 40:
        interni = sorted(tagli[1:-1], key=lambda x: liscio[x])[:38]
        tagli = [0] + sorted(interni) + [w]
    return tagli


class _Parola:
    """Una parola come sequenza di 'atomi' (pezzi tra due tagli possibili)."""

    def __init__(self, gruppo, xh, base, m):
        self.xh, self.base, self.m = xh, base, m
        self.atomi = []  # (indice componente, glifo, a, b)
        for k, g in enumerate(gruppo):
            t = _tagli(g, xh)
            for a, b in zip(t, t[1:]):
                self.atomi.append((k, g, a, b))
        self.cache = {}

    def pezzo(self, i, j):
        """Classifica gli atomi i..j-1 come una sola lettera (None se non ammesso)."""
        if (i, j) in self.cache:
            return self.cache[(i, j)]
        comp = {self.atomi[x][0] for x in range(i, j)}
        r = None
        if len(comp) == 1:
            k, g, a, _ = self.atomi[i]
            b = self.atomi[j - 1][3]
            intero = a == 0 and b == g["x1"] - g["x0"]
            larghezza = b - a
            if intero or 0.2 * self.xh <= larghezza <= 1.9 * self.xh:
                sg = g if intero else _sotto_glifo(g, a, b)
                if sg is not None:
                    v = caratteristiche(_immagine_glifo(sg), _metrica_glifo(sg, self.xh, self.base), sg.get("parti", 1))
                    r = (self.m.classifica(v, k=9), v, sg, larghezza)
        self.cache[(i, j)] = r
        return r

    def _penalita(self, carattere, larghezza):
        # una lettera piu' larga di ~1.15 x e' plausibile solo per m e w
        return 0.0 if carattere in LARGHE or larghezza <= 1.15 * self.xh else 1.5 * (larghezza / self.xh - 1.15) + 0.6

    def migliore(self):
        """Divisione piu' probabile (senza sapere la parola)."""
        n = len(self.atomi)
        dp = [(-1e18, None)] * (n + 1)
        dp[0] = (0.0, None)
        for j in range(1, n + 1):
            for i in range(max(0, j - 7), j):
                if dp[i][0] <= -1e17:
                    continue
                r = self.pezzo(i, j)
                if r is None:
                    continue
                c, p = r[0][0]
                punteggio = dp[i][0] + np.log(max(p, 0.01)) + 1.1 - self._penalita(c, r[3])
                if punteggio > dp[j][0]:
                    dp[j] = (punteggio, i)
        return self._ricostruisci(dp, n)

    def allinea(self, lettere):
        """Divisione che corrisponde esattamente alle lettere date (per imparare dalle correzioni)."""
        n, k = len(self.atomi), len(lettere)
        if k == 0 or k > n:
            return None
        meno = -1e18
        dp = [[(meno, None)] * (k + 1) for _ in range(n + 1)]
        dp[0][0] = (0.0, None)
        for j in range(1, n + 1):
            for q in range(1, min(j, k) + 1):
                for i in range(max(0, j - 7), j):
                    if dp[i][q - 1][0] <= meno / 2:
                        continue
                    r = self.pezzo(i, j)
                    if r is None:
                        continue
                    voluta = STESSA_FORMA.get(lettere[q - 1], lettere[q - 1])
                    p = dict(r[0]).get(voluta, 0.005)
                    punteggio = dp[i][q - 1][0] + np.log(max(p, 0.005)) - self._penalita(lettere[q - 1], r[3])
                    if punteggio > dp[j][q][0]:
                        dp[j][q] = (punteggio, i)
        if dp[n][k][0] <= meno / 2:
            return None
        seq, j, q = [], n, k
        while j > 0:
            i = dp[j][q][1]
            seq.append(self.pezzo(i, j))
            j, q = i, q - 1
        return [r[1] for r in reversed(seq)]

    def _ricostruisci(self, dp, n):
        if dp[n][1] is None and n > 0:
            return []
        seq, j = [], n
        while j > 0:
            i = dp[j][1]
            seq.append(self.pezzo(i, j))
            j = i
        return list(reversed(seq))


# ============================== RICONOSCIMENTO ==============================
def riconosci(immagine):
    m = modello()
    img = _carica_immagine(immagine)
    maschera = _binarizza(img)
    if maschera.sum() < 20:
        raise ValueError("Non vedo nessuna scrittura nell'immagine.")
    risultato_righe, dati_parole = [], []
    for (y0, y1) in _righe(maschera):
        glifi, _ = _glifi_della_riga(maschera, y0, y1)
        xh, base = _metriche_riga(glifi)
        parole_riga = []
        for gruppo in _parole(glifi, xh):
            parola = _Parola(gruppo, xh, base, m)
            lettere = []
            for classi, v, g, _ in parola.migliore():
                c, p = classi[0]
                if c in STESSA_FORMA.values() and (g["y1"] - g["y0"]) > 1.3 * xh:
                    c = c.upper()  # stessa forma maiuscola/minuscola: decide l'altezza
                if g.get("diviso"):
                    p *= 0.9  # lettera separata da un blocco unico: un po' meno sicura
                lettere.append([(c, p)] + classi[1:4])
            testo = "".join(l[0][0] for l in lettere)
            certezza = min(l[0][1] for l in lettere) if lettere else 0.0
            alternative = []
            if certezza < SOGLIA:
                correzioni = _correggi_con_vocabolario(lettere)
                if correzioni:
                    migliore = correzioni[0]
                    staccata = len(correzioni) == 1 or migliore[0] > 3 * correzioni[1][0]
                    if staccata and migliore[0] > 0.02:
                        testo = migliore[1] if not testo[:1].isupper() else migliore[1].capitalize()
                        certezza = max(certezza, SOGLIA if migliore[0] > 0.1 else 0.75)
                    alternative = [p for _, p in correzioni]
            idp = f"p{len(dati_parole)}"
            dati_parole.append({"id": idp, "parola": parola})
            parole_riga.append({"id": idp, "testo": testo, "certezza": round(float(certezza), 2),
                                "dubbio": bool(certezza < SOGLIA), "alternative": alternative[:3],
                                "lettere": [[(c, round(float(p), 2)) for c, p in l[:3]] for l in lettere]})
        risultato_righe.append(parole_riga)
    sessione = f"{int(time.time() * 1000)}"
    with _blocco:
        _sessioni[sessione] = {"parole": dati_parole, "ora": time.time()}
        for k in [k for k, s in _sessioni.items() if time.time() - s["ora"] > 3600]:
            del _sessioni[k]
    testo = "\n".join(" ".join(p["testo"] for p in r) for r in risultato_righe)
    dubbi = [p for r in risultato_righe for p in r if p["dubbio"]]
    return {"sessione": sessione, "testo": testo, "righe": risultato_righe, "dubbi": len(dubbi)}


def correggi(sessione, correzioni):
    """
    correzioni: {id_parola: "parola giusta"} (anche per le parole confermate cosi' come sono).
    Le lettere delle parole con lo stesso numero di lettere diventano nuovi esempi.
    """
    s = _sessioni.get(sessione)
    if not s:
        raise ValueError("Sessione scaduta: riconosci di nuovo il testo.")
    m = modello()
    nuovi_v, nuove_e, imparate, solo_parola = [], [], 0, 0
    per_id = {p["id"]: p for p in s["parole"]}
    for idp, giusta in correzioni.items():
        giusta = (giusta or "").strip()
        p = per_id.get(idp)
        if not p or not giusta or " " in giusta:
            continue
        impara_parola(giusta)
        lettere = [c for c in giusta if c.isalnum()]
        vettori = p["parola"].allinea(lettere)  # trova i tagli che corrispondono alle lettere giuste
        if vettori:
            nuovi_v += vettori
            nuove_e += lettere
            imparate += 1
        else:
            solo_parola += 1
    with _blocco:
        m.aggiungi(nuovi_v, nuove_e, "utente")
        m.salva()
    return {"lettere_imparate": len(nuove_e), "parole_imparate": imparate, "solo_vocabolario": solo_parola}


def allena(immagine, lettera):
    """Modalita' allenamento: l'immagine contiene una o piu' volte la stessa lettera."""
    if len(lettera) != 1 or not lettera.isalnum():
        raise ValueError("Indica una sola lettera o cifra.")
    img = _carica_immagine(immagine)
    maschera = _binarizza(img)
    vettori = []
    for (y0, y1) in _righe(maschera):
        glifi, _ = _glifi_della_riga(maschera, y0, y1)
        # allenamento: lettere singole, metrica stimata come per una lettera "normale" della sua famiglia
        alte, basse = "bdfhklt" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", "gpqy"
        metrica = (1.6, 1.6, 0.0) if lettera in alte else (1.6, 1.0, 0.6) if lettera in basse else (1.0, 1.0, 0.0)
        vettori += [caratteristiche(_immagine_glifo(g), metrica, g.get("parti", 1)) for g in glifi if not g.get("diviso")]
    if not vettori:
        raise ValueError("Non vedo nessuna lettera.")
    m = modello()
    with _blocco:
        m.aggiungi(vettori, [lettera] * len(vettori), "utente")
        m.salva()
    return {"aggiunti": len(vettori)}


def stato():
    return {**modello().conteggi(), "parole_imparate": len(parole_note())}
