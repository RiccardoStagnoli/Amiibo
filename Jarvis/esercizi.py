"""
Jarvis - Risolutore di esercizi (matematica, meccanica, tecnologia/elettrotecnica).

Calcoli ESATTI con SymPy (libreria matematica open source), niente intelligenza
artificiale "a occhio": se il risultato c'e', e' giusto rispetto ai dati.

MATEMATICA
  risolvi x^2 - 5x + 6 = 0          (anche sistemi: risolvi x+y=5; x-y=1)
  deriva x^3*sin(x)                 integra x^2 da 0 a 3      limite di sin(x)/x per x che tende a 0
  semplifica / scomponi / espandi ...     calcola 3/4 + 2^5 * sqrt(2)

FISICA / MECCANICA / TECNOLOGIA (dati con unita' di misura)
  "Un'auto parte da ferma e accelera a 2 m/s² per 10 s. Che velocita' raggiunge?"
  "m=10 kg, a=3 m/s^2, F=?"      "resistenze da 10 ohm e 20 ohm in parallelo"
  converti 120 km/h in m/s

Regola del 90%: se un dato e' ambiguo (es. due lunghezze senza dire quale e'
quale) o l'esercizio non e' riconosciuto, Jarvis lo dice invece di tirare a indovinare.
"""

import re

# ============================================================================
#                                   MATEMATICA
# ============================================================================
FUNZIONI = {"sin", "cos", "tan", "asin", "acos", "atan", "log", "ln", "exp", "sqrt", "abs", "pi", "E",
            "sinh", "cosh", "tanh", "factorial", "oo", "cot", "sec", "csc", "floor", "ceiling"}
SINONIMI_FUNZ = {r"\bsen\b": "sin", r"\btg\b": "tan", r"\barcsen\b": "asin", r"\barcsin\b": "asin",
                 r"\barccos\b": "acos", r"\barctg\b": "atan", r"\barctan\b": "atan", r"\bradice di\b": "sqrt",
                 r"\bradice\b": "sqrt", r"\bpi greco\b": "pi", r"\binfinito\b": "oo", r"\bln\b": "log"}


class ErroreEsercizio(Exception):
    pass


def _prepara(testo):
    t = testo.strip().rstrip("?.!")
    t = t.replace("²", "^2").replace("³", "^3").replace("√", "sqrt").replace("π", "pi").replace("·", "*")
    t = t.replace("×", "*").replace(":", "/").replace("−", "-").replace("–", "-")
    for a, b in SINONIMI_FUNZ.items():
        t = re.sub(a, b, t, flags=re.I)
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)  # virgola decimale italiana
    if re.search(r"[^0-9a-zA-Z+\-*/^().=;\s<>!]", t):
        raise ErroreEsercizio("Simboli non riconosciuti nell'espressione.")
    for nome in re.findall(r"[A-Za-z_]{2,}", t):
        if nome not in FUNZIONI:
            raise ErroreEsercizio(f"Non conosco '{nome}'. Usa lettere singole per le variabili (x, y, t...).")
    return t


def _espr(t):
    from sympy.parsing.sympy_parser import (convert_xor, implicit_multiplication_application,
                                            parse_expr, standard_transformations)
    import sympy

    trasf = standard_transformations + (implicit_multiplication_application, convert_xor)
    locali = {n: getattr(sympy, n) for n in FUNZIONI if hasattr(sympy, n)}
    locali["E"] = sympy.E
    return parse_expr(t, local_dict=locali, transformations=trasf, evaluate=True)


def _eq(t):
    import sympy

    if "=" in t:
        sx, dx = t.split("=", 1)
        return sympy.Eq(_espr(sx), _espr(dx))
    return sympy.Eq(_espr(t), 0)


def _fmt(x):
    import sympy

    s = sympy.sstr(x).replace("**", "^").replace("sqrt", "√").replace("pi", "π").replace("*", "·")
    try:
        if not x.is_Integer and x.is_number and x.is_real:
            s += f" ≈ {float(x):.6g}"
    except (AttributeError, TypeError):
        pass
    return s


def risolvi(testo):
    import sympy

    parti = [p for p in re.split(r";|\be\b|\bsistema\b", _prepara(testo)) if p.strip()]
    equazioni = [_eq(p) for p in parti]
    incognite = sorted(set().union(*[e.free_symbols for e in equazioni]), key=str)
    if not incognite:
        raise ErroreEsercizio("Non c'è nessuna incognita.")
    passi = []
    if len(equazioni) == 1 and len(incognite) == 1:
        x = incognite[0]
        espr = sympy.expand(equazioni[0].lhs - equazioni[0].rhs)
        passi.append(f"Forma normale: {_fmt(espr)} = 0")
        poli = sympy.Poly(espr, x) if espr.is_polynomial(x) else None
        if poli is not None and poli.degree() == 2:
            a, b, c = poli.all_coeffs()
            delta = sympy.simplify(b ** 2 - 4 * a * c)
            passi.append(f"a = {_fmt(a)}, b = {_fmt(b)}, c = {_fmt(c)}")
            passi.append(f"Δ = b² - 4ac = {_fmt(delta)}")
            if delta.is_negative:
                passi.append("Δ < 0: nessuna soluzione reale.")
        elif poli is not None and poli.degree() == 1:
            a, b = poli.all_coeffs()
            passi.append(f"{_fmt(a)}·{x} = {_fmt(-b)}  →  {x} = {_fmt(-b)}/{_fmt(a)}")
        sol = sympy.solve(equazioni[0], x)
        reali = [s for s in sol if s.is_real is not False]
        if not sol:
            risultato = "Nessuna soluzione."
        else:
            risultato = "; ".join(f"{x} = {_fmt(s)}" for s in (reali or sol))
            if reali and len(reali) < len(sol):
                risultato += " (più soluzioni complesse)"
    else:
        sol = sympy.solve(equazioni, incognite, dict=True)
        risultato = " oppure ".join(", ".join(f"{k} = {_fmt(v)}" for k, v in s.items()) for s in sol) or "Nessuna soluzione (sistema impossibile)."
    return {"passi": passi, "risultato": risultato}


def deriva(testo):
    import sympy

    m = re.search(r"\s+rispetto a\s+([a-z])\s*$", testo, re.I)
    if m:
        testo = testo[:m.start()]
    f = _espr(_prepara(testo))
    var = sympy.Symbol(m.group(1)) if m else (sorted(f.free_symbols, key=str) or [sympy.Symbol("x")])[0]
    d = sympy.diff(f, var)
    return {"passi": [f"f({var}) = {_fmt(f)}", f"f'({var}) = {_fmt(d)}"], "risultato": f"f'({var}) = {_fmt(sympy.simplify(d))}"}


def integra(testo):
    import sympy

    m = re.search(r"\s+da\s+(\S+)\s+a\s+(\S+)\s*$", testo, re.I)
    corpo = testo[:m.start()] if m else testo
    corpo = re.sub(r"\s*d([a-z])\s*$", "", corpo)
    f = _espr(_prepara(corpo))
    var = (sorted(f.free_symbols, key=str) or [sympy.Symbol("x")])[0]
    if m:
        a, b = _espr(_prepara(m.group(1))), _espr(_prepara(m.group(2)))
        primitiva = sympy.integrate(f, var)
        valore = sympy.integrate(f, (var, a, b))
        return {"passi": [f"Primitiva: F({var}) = {_fmt(primitiva)}", f"F({_fmt(b)}) - F({_fmt(a)})"],
                "risultato": f"∫ = {_fmt(sympy.simplify(valore))}"}
    return {"passi": [], "risultato": f"∫ {_fmt(f)} d{var} = {_fmt(sympy.integrate(f, var))} + C"}


def limite(testo):
    import sympy

    m = re.match(r"(?:limite di\s+)?(.+?)\s+per\s+([a-z])\s+che tende a\s+(\S+?)(\+|-)?$", testo.strip(), re.I)
    if not m:
        raise ErroreEsercizio("Formato: 'limite di sin(x)/x per x che tende a 0'.")
    f, var = _espr(_prepara(m.group(1))), sympy.Symbol(m.group(2))
    punto = _espr(_prepara(m.group(3)))
    l = sympy.limit(f, var, punto, dir=m.group(4) or "+-") if m.group(4) else sympy.limit(f, var, punto)
    return {"passi": [], "risultato": f"lim {var}→{_fmt(punto)} {_fmt(f)} = {_fmt(l)}"}


def trasforma(tipo, testo):
    import sympy

    f = _espr(_prepara(testo))
    r = {"semplifica": sympy.simplify, "scomponi": sympy.factor, "espandi": sympy.expand}[tipo](f)
    return {"passi": [], "risultato": f"{_fmt(r)}"}


def calcola(testo):
    import sympy

    f = _espr(_prepara(testo))
    if f.free_symbols:
        raise ErroreEsercizio("Ci sono variabili: per risolvere usa 'risolvi ...'.")
    esatto = sympy.nsimplify(f) if f.is_Float else sympy.simplify(f)
    return {"passi": [], "risultato": f"{_fmt(esatto)}"}


# ============================================================================
#                      FISICA, MECCANICA, TECNOLOGIA (con unita')
# ============================================================================
# simbolo: (descrizione, unita' SI)
GRANDEZZE = {
    "s": ("spazio/distanza", "m"), "v": ("velocità", "m/s"), "v0": ("velocità iniziale", "m/s"),
    "vm": ("velocità media", "m/s"), "t": ("tempo", "s"), "a": ("accelerazione", "m/s²"),
    "F": ("forza", "N"), "m": ("massa", "kg"), "Fp": ("forza peso", "N"), "q": ("quantità di moto", "kg·m/s"),
    "L": ("lavoro", "J"), "Ec": ("energia cinetica", "J"), "Ep": ("energia potenziale", "J"), "h": ("altezza", "m"),
    "P": ("potenza", "W"), "eta": ("rendimento", ""), "Pu": ("potenza utile", "W"), "Pa": ("potenza assorbita", "W"),
    "omega": ("velocità angolare", "rad/s"), "r": ("raggio", "m"), "f": ("frequenza", "Hz"), "T": ("periodo", "s"),
    "ac": ("accelerazione centripeta", "m/s²"), "Fc": ("forza centripeta", "N"), "n": ("giri al minuto", "giri/min"),
    "M": ("momento/coppia", "N·m"), "b": ("braccio", "m"), "F1": ("forza motrice", "N"), "b1": ("braccio motrice", "m"),
    "F2": ("forza resistente", "N"), "b2": ("braccio resistente", "m"),
    "n1": ("giri ruota motrice", "giri/min"), "n2": ("giri ruota condotta", "giri/min"),
    "z1": ("denti ruota motrice", ""), "z2": ("denti ruota condotta", ""), "itr": ("rapporto di trasmissione", ""),
    "p": ("pressione", "Pa"), "A": ("area/superficie", "m²"), "rho": ("densità", "kg/m³"), "Vol": ("volume", "m³"),
    "V": ("tensione", "V"), "I": ("corrente", "A"), "R": ("resistenza", "Ω"), "Pel": ("potenza elettrica", "W"),
    "Eel": ("energia elettrica", "J"), "R1": ("resistenza 1", "Ω"), "R2": ("resistenza 2", "Ω"),
    "R3": ("resistenza 3", "Ω"), "Rt": ("resistenza equivalente", "Ω"),
    "Q": ("calore", "J"), "c": ("calore specifico", "J/(kg·K)"), "dT": ("variazione di temperatura", "K"),
    "g": ("accelerazione di gravità", "m/s²"),
}

# gruppo: [(equazione, descrizione)]
FORMULE = {
    "moto rettilineo uniforme": [("s = v*t", "s = v·t")],
    "moto uniformemente accelerato": [("v = v0 + a*t", "v = v0 + a·t"), ("s = v0*t + a*t**2/2", "s = v0·t + ½·a·t²"),
                                      ("v**2 = v0**2 + 2*a*s", "v² = v0² + 2·a·s"), ("vm = (v0 + v)/2", "vm = (v0+v)/2"),
                                      ("s = vm*t", "s = vm·t")],
    "dinamica": [("F = m*a", "F = m·a (2ª legge di Newton)"), ("Fp = m*g", "Fp = m·g"), ("q = m*v", "q = m·v")],
    "lavoro ed energia": [("L = F*s", "L = F·s"), ("Ec = m*v**2/2", "Ec = ½·m·v²"), ("Ep = m*g*h", "Ep = m·g·h"),
                          ("P = L/t", "P = L/t"), ("P = F*v", "P = F·v"), ("eta = Pu/Pa", "η = Pu/Pa")],
    "caduta libera": [("v = g*t", "v = g·t"), ("h = g*t**2/2", "h = ½·g·t²"), ("v**2 = 2*g*h", "v² = 2·g·h"),
                      ("Ep = m*g*h", "Ep = m·g·h"), ("Ec = m*v**2/2", "Ec = ½·m·v²")],
    "moto circolare": [("v = omega*r", "v = ω·r"), ("omega = 2*pi*f", "ω = 2π·f"), ("T = 1/f", "T = 1/f"),
                       ("ac = v**2/r", "ac = v²/r"), ("Fc = m*v**2/r", "Fc = m·v²/r"), ("n = 60*f", "n = 60·f"),
                       ("M = F*r", "M = F·r"), ("P = M*omega", "P = M·ω")],
    "leve e momenti": [("M = F*b", "M = F·b"), ("F1*b1 = F2*b2", "F1·b1 = F2·b2 (equilibrio della leva)")],
    "trasmissioni": [("itr = n1/n2", "i = n1/n2"), ("n1*z1 = n2*z2", "n1·z1 = n2·z2"), ("itr = z2/z1", "i = z2/z1")],
    "pressione e fluidi": [("p = F/A", "p = F/A"), ("p = rho*g*h", "p = ρ·g·h (Stevino)"), ("rho = m/Vol", "ρ = m/V")],
    "elettrotecnica": [("V = R*I", "V = R·I (legge di Ohm)"), ("Pel = V*I", "P = V·I"), ("Pel = R*I**2", "P = R·I²"),
                       ("Eel = Pel*t", "E = P·t")],
    "resistenze in serie": [("Rt = R1 + R2 + R3", "Rt = R1 + R2 + R3"), ("V = Rt*I", "V = Rt·I")],
    "resistenze in parallelo": [("1/Rt = 1/R1 + 1/R2 + 1/R3", "1/Rt = 1/R1 + 1/R2 + 1/R3"), ("V = Rt*I", "V = Rt·I")],
    "calorimetria": [("Q = m*c*dT", "Q = m·c·ΔT")],
}

# unita' -> (fattore verso SI, tipo)
UNITA = {
    "km/h": (1 / 3.6, "vel"), "m/s^2": (1, "acc"), "m/s2": (1, "acc"), "m/s²": (1, "acc"), "m/s": (1, "vel"),
    "rad/s": (1, "omega"), "giri/min": (1, "rpm"), "rpm": (1, "rpm"), "kg/m^3": (1, "dens"), "kg/m3": (1, "dens"),
    "kg/m³": (1, "dens"), "g/cm^3": (1000, "dens"), "g/cm3": (1000, "dens"), "j/kgk": (1, "csp"), "j/(kgk)": (1, "csp"),
    "j/kg°c": (1, "csp"), "j/(kg°c)": (1, "csp"), "kwh": (3.6e6, "energia"), "nm": (1, "momento"), "n·m": (1, "momento"),
    "km": (1000, "lung"), "cm": (0.01, "lung"), "mm": (0.001, "lung"), "m^2": (1, "area"), "m2": (1, "area"),
    "m²": (1, "area"), "cm^2": (1e-4, "area"), "cm2": (1e-4, "area"), "cm²": (1e-4, "area"), "mm^2": (1e-6, "area"),
    "mm2": (1e-6, "area"), "mm²": (1e-6, "area"), "m^3": (1, "vol"), "m3": (1, "vol"), "m³": (1, "vol"),
    "litri": (0.001, "vol"), "l": (0.001, "vol"), "dm^3": (0.001, "vol"), "dm3": (0.001, "vol"), "cm^3": (1e-6, "vol"),
    "cm3": (1e-6, "vol"), "m": (1, "lung"), "metri": (1, "lung"), "kg": (1, "massa"), "g": (0.001, "massa"),
    "grammi": (0.001, "massa"), "tonnellate": (1000, "massa"), "kn": (1000, "forza"), "n": (1, "forza"),
    "newton": (1, "forza"), "kj": (1000, "energia"), "mj": (1e6, "energia"), "j": (1, "energia"), "joule": (1, "energia"),
    "kw": (1000, "potenza"), "cv": (735.5, "potenza"), "w": (1, "potenza"), "watt": (1, "potenza"),
    "kpa": (1000, "press"), "mpa": (1e6, "press"), "bar": (1e5, "press"), "atm": (101325, "press"), "pa": (1, "press"),
    "kv": (1000, "tens"), "mv": (0.001, "tens"), "v": (1, "tens"), "volt": (1, "tens"), "ma": (0.001, "corr"),
    "a": (1, "corr"), "ampere": (1, "corr"), "kω": (1000, "res"), "kohm": (1000, "res"), "ω": (1, "res"),
    "ohm": (1, "res"), "hz": (1, "freq"), "khz": (1000, "freq"), "ore": (3600, "tempo"), "ora": (3600, "tempo"),
    "h": (3600, "tempo"), "minuti": (60, "tempo"), "min": (60, "tempo"), "secondi": (1, "tempo"), "s": (1, "tempo"),
    "ms": (0.001, "tempo"), "°c": (1, "temp"), "k": (1, "temp"), "%": (0.01, "perc"), "denti": (1, "denti"),
}

# tipo di unita' -> simbolo predefinito e parole che scelgono un altro simbolo
TIPI = {
    "vel": ("v", [("inizial", "v0"), ("partenza", "v0"), ("media", "vm")]),
    "acc": ("a", [("gravit", "g"), ("centripet", "ac")]),
    "lung": ("s", [("alt", "h"), ("raggio", "r"), ("diametro", "_diam"), ("braccio motore", "b1"), ("braccio della forza motrice", "b1"),
                   ("braccio resistente", "b2"), ("braccio della forza resistente", "b2"), ("braccio", "b"),
                   ("profondit", "h"), ("quota", "h")]),
    "massa": ("m", []), "tempo": ("t", [("period", "T")]), "forza": ("F", [("peso", "Fp"), ("motrice", "F1"), ("potenza della leva", "F1"),
                                                                       ("resistent", "F2"), ("centripet", "Fc")]),
    "energia": ("L", [("cinetic", "Ec"), ("potenzial", "Ep"), ("calore", "Q"), ("elettric", "Eel"), ("consum", "Eel")]),
    "potenza": ("P", [("utile", "Pu"), ("assorb", "Pa"), ("elettric", "Pel"), ("lampad", "Pel"), ("resa", "Pu")]),
    "press": ("p", []), "area": ("A", []), "vol": ("Vol", []), "dens": ("rho", []), "tens": ("V", []), "corr": ("I", []),
    "res": ("R", []), "freq": ("f", []), "rpm": ("n", [("motric", "n1"), ("condott", "n2"), ("uscita", "n2"), ("ingresso", "n1")]),
    "omega": ("omega", []), "momento": ("M", []), "temp": ("dT", []), "csp": ("c", []), "perc": ("eta", []),
    "denti": ("z", [("motric", "z1"), ("pignone", "z1"), ("condott", "z2"), ("corona", "z2")]),
}

DOMANDE = [  # parole nella domanda -> grandezza cercata (le piu' specifiche prima)
    ("velocita angolare", "omega"), ("velocita media", "vm"), ("velocita iniziale", "v0"), ("velocita finale", "v"),
    ("velocita", "v"), ("accelerazione centripeta", "ac"), ("accelerazione", "a"), ("forza centripeta", "Fc"),
    ("forza peso", "Fp"), ("peso", "Fp"), ("forza motrice", "F1"), ("forza resistente", "F2"), ("forza", "F"),
    ("quantita di moto", "q"), ("energia cinetica", "Ec"), ("energia potenziale", "Ep"), ("energia elettrica", "Eel"),
    ("energia consumata", "Eel"), ("consuma", "Eel"), ("lavoro", "L"), ("potenza utile", "Pu"), ("potenza assorbita", "Pa"),
    ("potenza", "P"), ("rendimento", "eta"), ("frequenza", "f"), ("periodo", "T"), ("giri", "n"), ("momento", "M"),
    ("coppia", "M"), ("braccio", "b"), ("rapporto di trasmissione", "itr"), ("pressione", "p"), ("densita", "rho"),
    ("volume", "Vol"), ("superficie", "A"), ("area", "A"), ("corrente", "I"), ("intensita", "I"), ("tensione", "V"),
    ("differenza di potenziale", "V"), ("resistenza equivalente", "Rt"), ("resistenza totale", "Rt"), ("resistenza", "R"),
    ("calore specifico", "c"), ("calore", "Q"), ("temperatura", "dT"), ("massa", "m"), ("altezza", "h"), ("quota", "h"),
    ("tempo", "t"), ("quanto tempo", "t"), ("quanti secondi", "t"), ("distanza", "s"), ("spazio", "s"), ("percorre", "s"),
    ("raggio", "r"), ("denti", "z2"),
]

RX_NUMERO_UNITA = re.compile(
    r"(?<![\w.])(-?\d+(?:[.,]\d+)?(?:\s*[·x*]\s*10\^?\s*-?\d+)?)\s*"
    r"(km/h|m/s\^2|m/s2|m/s²|m/s|rad/s|giri/min|rpm|kg/m\^3|kg/m3|kg/m³|g/cm\^3|g/cm3|j/\(kg°c\)|j/kg°c|j/\(kgk\)|j/kgk|kwh|n·m|nm|"
    r"km|cm\^2|cm2|cm²|mm\^2|mm2|mm²|cm\^3|cm3|dm\^3|dm3|cm|mm|m\^2|m2|m²|m\^3|m3|m³|metri|m|"
    r"kg|grammi|g|tonnellate|kn|newton|n|kj|mj|joule|j|kw|cv|watt|w|kpa|mpa|bar|atm|pa|kv|mv|volt|v|ma|ampere|a|"
    r"kω|kohm|ω|ohm|khz|hz|ore|ora|h|minuti|min|ms|secondi|s|°c|k|%|denti|litri|l)(?![\w])", re.I)


def _norm(t):
    import unicodedata

    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(ch for ch in t if not unicodedata.combining(ch) or ch in "²³")


def _numero(txt):
    txt = txt.replace(",", ".").replace(" ", "")
    m = re.match(r"(-?\d+(?:\.\d+)?)(?:[·x*]10\^?(-?\d+))?$", txt)
    return float(m.group(1)) * (10 ** int(m.group(2)) if m.group(2) else 1)


def estrai_dati(testo):
    """Trova i dati (numero + unita') e la grandezza richiesta. Restituisce (dati, incognita, avvisi)."""
    t = _norm(testo).replace("ω", "ω")
    dati, avvisi, usati = {}, [], set()
    # forma esplicita: F=? m=10 kg
    esplicita = dict(re.findall(r"\b([A-Za-z]\w{0,4})\s*=\s*(\?|-?[\d.,]+\s*[^\s,;]*)", testo))
    incognita = next((k for k, v in esplicita.items() if v == "?"), None)
    for k, v in esplicita.items():
        if v == "?" or k not in GRANDEZZE:
            continue
        m = RX_NUMERO_UNITA.match(v.strip())
        if m:
            dati[k] = _numero(m.group(1)) * UNITA[m.group(2).lower()][0]
        else:
            try:
                dati[k] = _numero(v.strip())
            except (AttributeError, ValueError):
                pass
    if dati or incognita:
        return dati, incognita, avvisi
    # linguaggio naturale
    frena = bool(re.search(r"si ferma|fino a fermarsi|frena|si arresta|decelera", t))
    da_a = re.search(r"da\s+(-?\d+(?:[.,]\d+)?)\s*(km/h|m/s)\s+a\s+(-?\d+(?:[.,]\d+)?)\s*(km/h|m/s)(?![\w/])", t)
    salta = set()
    if da_a:  # "passa da 10 m/s a 20 m/s": iniziale e finale
        dati["v0"] = _numero(da_a.group(1)) * UNITA[da_a.group(2)][0]
        dati["v"] = _numero(da_a.group(3)) * UNITA[da_a.group(4)][0]
        salta = {da_a.start(1), da_a.start(3)}
    for m in RX_NUMERO_UNITA.finditer(t):
        if m.start(1) in salta:
            continue
        valore = _numero(m.group(1))
        unita = m.group(2).lower()
        fattore, tipo = UNITA[unita]
        prima = t[max(0, m.start() - 45):m.start()]
        simbolo, alternative = TIPI[tipo]
        esplicito = False
        for parola, alt in alternative:
            if parola in prima[-35:]:
                simbolo, esplicito = alt, True
                break
        if tipo == "vel" and frena and not esplicito:
            simbolo = "v0"  # in una frenata la velocita' data e' quella iniziale
        if tipo == "res":  # piu' resistenze: R1, R2, R3
            simbolo = next(x for x in ("R1", "R2", "R3", "R") if x not in dati) if ("serie" in t or "parallelo" in t) else "R"
        if tipo == "denti":
            simbolo = next(x for x in ("z1", "z2") if x not in dati) if simbolo == "z" else simbolo
        if tipo == "rpm" and simbolo == "n" and ("trasmission" in t or "ruota" in t or "ingranagg" in t):
            simbolo = next(x for x in ("n1", "n2") if x not in dati)
        if tipo == "temp":
            continue  # temperature: gestite sotto come differenza
        valore *= fattore
        if simbolo == "_diam":
            simbolo, valore = "r", valore / 2
            avvisi.append("Diametro convertito in raggio (r = d/2).")
        if simbolo in dati:
            avvisi.append(f"Due valori per {GRANDEZZE.get(simbolo, (simbolo,))[0]}: specifica quale è quale (es. 'velocità iniziale').")
            continue
        dati[simbolo] = valore
        usati.add(simbolo)
    temps = [(_numero(x.group(1))) for x in re.finditer(r"(-?\d+(?:[.,]\d+)?)\s*(?:°c|gradi)", t)]
    if len(temps) == 2:
        dati["dT"] = abs(temps[1] - temps[0])
    elif len(temps) == 1 and ("aumenta di" in t or "variazione" in t or "di " in t):
        dati["dT"] = abs(temps[0])
    # condizioni implicite
    if re.search(r"(parte|partendo|parti) da fermo|da ferm[oa]|in quiete|inizialmente ferm", t):
        dati.setdefault("v0", 0.0)
    if frena and re.search(r"si ferma|fino a fermarsi|si arresta|fino all'arresto", t):
        dati.setdefault("v", 0.0)
    if re.search(r"caduta libera|lasciat[oa] cadere|cade da|cadere da", t):
        dati.setdefault("g", 9.81)
        dati.setdefault("v0", 0.0)
    if re.search(r"\bpeso\b|gravit|altezza|caduta|potenziale|stevino|profondit", t):
        dati.setdefault("g", 9.81)
    # domanda: ultima frase con verbo di richiesta
    frasi = re.split(r"(?<=[.?!])\s+", t)
    domanda = next((f for f in reversed(frasi) if re.search(r"\?|calcola|determina|trova|quanto|quale|qual e|che ", f)), t)
    for parole, simbolo in DOMANDE:
        if re.search(r"\b" + parole, domanda) and simbolo not in dati:
            incognita = simbolo
            break
    if incognita == "n" and re.search(r"ruot|ingranagg|trasmission|pulegg", t):
        incognita = "n2" if re.search(r"condott|uscita", domanda) or "n2" not in dati else "n1"
    if incognita == "z2" and "z2" in dati:
        incognita = "z1"
    return dati, incognita, avvisi


def _gruppi_per_contesto(t):
    ordine = list(FORMULE)
    preferiti, esclusi = [], set()
    if "parallelo" in t:
        preferiti.append("resistenze in parallelo")
        esclusi.add("resistenze in serie")
    if re.search(r"\bserie\b", t):
        preferiti.append("resistenze in serie")
        esclusi.add("resistenze in parallelo")
    if not re.search(r"parallelo|\bserie\b", t):
        esclusi |= {"resistenze in serie", "resistenze in parallelo"}
    if re.search(r"caduta libera|lasciat[oa] cadere|cade da|cadere da", t):
        preferiti.append("caduta libera")
    else:
        esclusi.add("caduta libera")
    accelera = re.search(r"accelera|frena|fermarsi|si ferma|da ferm|decelera|passa da", t)
    if accelera:
        esclusi.add("moto rettilineo uniforme")
    elif re.search(r"costante|uniforme", t):
        preferiti.append("moto rettilineo uniforme")
    return [g for g in preferiti + [g for g in ordine if g not in preferiti] if g not in esclusi]


def _risolvi_con(gruppi, dati, incognita):
    """Applica le formule dei gruppi una alla volta finche' trova l'incognita."""
    import sympy

    noti = dict(dati)
    passi = []
    usati = []
    formule = []
    tutti = {n: sympy.Symbol(n) for n in GRANDEZZE}  # evita nomi riservati di SymPy (es. Q)
    tutti["pi"] = sympy.pi
    for g in gruppi:
        formule += [(g, eq, desc) for eq, desc in FORMULE[g]]
    for _ in range(8):
        if incognita in noti:
            break
        progresso = False
        for gruppo, eq, desc in formule:
            sx, dx = eq.split("=")
            simboli = {str(x) for x in sympy.sympify(sx + "-(" + dx + ")", locals=tutti).free_symbols}
            # resistenze opzionali (R3) se non date
            if gruppo.startswith("resistenze") and "R3" not in noti and "R3" in simboli:
                eq_loc = eq.replace(" + R3", "").replace(" + 1/R3", "")
                sx, dx = eq_loc.split("=")
                simboli -= {"R3"}
            ignoti = [x for x in simboli if x not in noti]
            if len(ignoti) != 1 or ignoti[0] == "g":  # g e' una costante, non un'incognita
                continue
            x = ignoti[0]
            simb = {n: tutti[n] for n in simboli}
            espressione = sympy.sympify(sx, locals=tutti) - sympy.sympify(dx, locals=tutti)
            soluzioni = sympy.solve(espressione.subs({simb[k]: v for k, v in noti.items() if k in simb}), simb[x])
            reali = [float(s) for s in soluzioni if s.is_real]
            if not reali:
                continue
            positivi = [s for s in reali if s >= 0]
            valore = max(positivi) if positivi else reali[0]
            noti[x] = valore
            if gruppo not in usati:
                usati.append(gruppo)
            sostituiti = ", ".join(f"{k} = {_bello(noti[k])}" for k in sorted(simboli) if k != x)
            passi.append(f"{desc}  →  con {sostituiti}  →  {x} = {_bello(valore)} {GRANDEZZE.get(x, ('', ''))[1]}")
            progresso = True
            if x == incognita:
                break
        if not progresso:
            break
    return (noti.get(incognita), passi, usati)


def _bello(x):
    if abs(x) >= 1e6 or (0 < abs(x) < 1e-3):
        mantissa, esponente = f"{x:.4e}".split("e")
        return f"{float(mantissa):g}×10^{int(esponente)}"
    return f"{round(x, 4):g}"


def fisica(testo):
    t = _norm(testo)
    dati, incognita, avvisi = estrai_dati(testo)
    if any("Due valori" in a for a in avvisi):
        raise ErroreEsercizio(" ".join(a for a in avvisi if "Due valori" in a))
    if not incognita:
        raise ErroreEsercizio("Non ho capito cosa devo calcolare. Scrivilo, es. 'Quale forza?' oppure 'F=?'.")
    if not dati:
        raise ErroreEsercizio("Non ho trovato dati con unità di misura (es. 10 kg, 2 m/s²).")
    risultati = []
    for g in _gruppi_per_contesto(t):
        valore, passi, usati = _risolvi_con([g] + ([] if g in ("dinamica",) else ["dinamica"]), dati, incognita)
        if valore is not None:
            risultati.append((", ".join(usati), valore, passi))
    if not risultati:  # prova combinando tutti i gruppi (esercizi a piu' passaggi)
        valore, passi, usati = _risolvi_con(_gruppi_per_contesto(t), dati, incognita)
        if valore is not None:
            risultati.append((", ".join(usati), valore, passi))
    if not risultati:
        mancano = ", ".join(GRANDEZZE[k][0] for k in GRANDEZZE if k not in dati)[:200]
        raise ErroreEsercizio(f"Con questi dati non riesco a ricavare {GRANDEZZE[incognita][0]}. Dati letti: "
                              + ", ".join(f"{k}={_bello(v)}" for k, v in dati.items()) + f". Potrebbe mancare uno tra: {mancano}…")
    valori = {round(r[1], 6) for r in risultati}
    if len(valori) > 1:
        dettagli = "; ".join(f"{g}: {_bello(v)}" for g, v, _ in risultati[:3])
        raise ErroreEsercizio(f"Il risultato dipende dal tipo di moto/argomento ({dettagli}). Specifica meglio l'esercizio.")
    gruppo, valore, passi = risultati[0]
    nome, unita = GRANDEZZE[incognita]
    if incognita == "eta":
        risultato = f"{nome} = {_bello(valore)} = {_bello(valore * 100)}%"
    else:
        risultato = f"{nome} = {_bello(valore)} {unita}".strip()
    dati_letti = ", ".join(f"{GRANDEZZE.get(k, (k,))[0]} {k} = {_bello(v)} {GRANDEZZE.get(k, ('', ''))[1]}".strip() for k, v in dati.items())
    return {"passi": [f"Argomento: {gruppo}", f"Dati (in unità SI): {dati_letti}"] + avvisi + passi, "risultato": risultato}


def converti(testo):
    m = re.match(r"(?:converti\s+)?(-?[\d.,]+)\s*(\S+)\s+(?:in|a)\s+(\S+)$", _norm(testo).strip())
    if not m:
        raise ErroreEsercizio("Formato: 'converti 120 km/h in m/s'.")
    valore, da, a = _numero(m.group(1)), m.group(2), m.group(3)
    if da not in UNITA or a not in UNITA:
        raise ErroreEsercizio("Unità non riconosciuta.")
    if UNITA[da][1] != UNITA[a][1]:
        raise ErroreEsercizio(f"Non si può convertire {da} in {a}: sono grandezze diverse.")
    r = valore * UNITA[da][0] / UNITA[a][0]
    return {"passi": [], "risultato": f"{_bello(valore)} {da} = {_bello(r)} {a}"}


# ============================================================================
#                                 INGRESSO UNICO
# ============================================================================
def risolvi_esercizio(testo):
    """Sceglie il tipo di esercizio. Restituisce {'passi': [...], 'risultato': str}."""
    t = testo.strip()
    tn = _norm(t)
    regole = [
        (r"^(converti|trasforma)\s+(.+)$", lambda m: converti(m.group(2))),
        (r"^(risolvi|equazione|sistema)[:\s]+(.+)$", lambda m: risolvi(m.group(2))),
        (r"^(deriva|derivata( di)?)[:\s]+(.+)$", lambda m: deriva(m.group(3))),
        (r"^(integra|integrale( di)?)[:\s]+(.+)$", lambda m: integra(m.group(3))),
        (r"^(limite( di)?)[:\s]+(.+)$", lambda m: limite("limite di " + m.group(3))),
        (r"^(semplifica|scomponi|espandi)[:\s]+(.+)$", lambda m: trasforma(m.group(1).lower(), m.group(2))),
        (r"^calcola[:\s]+([-0-9.,+*/^()\s√²³πa-z]+)$", lambda m: calcola(m.group(1))),
    ]
    for schema, f in regole:
        m = re.match(schema, t, re.I)
        if m and schema.startswith("^calcola"):
            parole = [w for w in re.findall(r"[a-z]{2,}", tn[7:]) if w not in FUNZIONI and w not in ("sen", "tg", "ln")]
            if parole or RX_NUMERO_UNITA.search(tn):
                continue  # e' un esercizio a parole: lo gestisce la parte di fisica
        if m:
            return f(m)
    if RX_NUMERO_UNITA.search(tn) or re.search(r"\b\w{1,5}\s*=\s*\?", t):
        return fisica(t)
    if re.fullmatch(r"[-0-9.,+*/^()\s√²³π]+", t):
        return calcola(t)
    raise ErroreEsercizio("Esercizio non riconosciuto. Esempi: 'risolvi x^2-5x+6=0', 'deriva x^3', "
                          "'m=10 kg, a=2 m/s², F=?', oppure il testo dell'esercizio con i dati e le unità di misura.")
