"""
JARVIS - Server centrale.

Pannello web su http://localhost:8080 (porta in config.py), raggiungibile da
qualsiasi dispositivo autorizzato (telefono, Rabbit R1, altri PC) se configurato.
Collega: WhatsApp, Google (Gmail/Calendario/Drive), Teams, PC Msi, meccanica.
"""

import json
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from functools import wraps

from flask import Flask, abort, jsonify, redirect, request, send_from_directory, session

import config
import extra
import memoria
import whatsapp_reader
from comandi import Interprete
from meccanica import EspertoMeccanica
from personalita import errore_utente

CARTELLA = os.path.dirname(os.path.abspath(__file__))
CARTELLA_WEB = os.path.join(CARTELLA, "web")
CARTELLA_DATI = os.path.join(CARTELLA, "dati")
API_WHATSAPP = "http://127.0.0.1:3010"
FILE_WEB = ("style.css", "app.js", "manifest.json", "icona.svg", "icona-192.png", "icona-512.png")

os.makedirs(CARTELLA_DATI, exist_ok=True)


def _segreto(nome):
    percorso = os.path.join(CARTELLA_DATI, nome)
    if not os.path.exists(percorso):
        with open(percorso, "w", encoding="utf-8") as f:
            f.write(secrets.token_hex(32))
    with open(percorso, encoding="utf-8") as f:
        return f.read().strip()


app = Flask(__name__, static_folder=None)
app.secret_key = _segreto(".chiave_sessione")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30)
TOKEN_INTERNO = _segreto(".token_interno")  # usato da ascolto.py sullo stesso PC

esperto = EspertoMeccanica()


# =============================== ACCESSO ===============================
_tentativi = {}  # ip -> [timestamp falliti]


def _bloccato(ip):
    recenti = [t for t in _tentativi.get(ip, []) if time.time() - t < 600]
    _tentativi[ip] = recenti
    return len(recenti) >= 5


def _interno():
    return (request.remote_addr in ("127.0.0.1", "::1")
            and secrets.compare_digest(request.headers.get("X-Token-Interno", ""), TOKEN_INTERNO))


def richiede_accesso(funzione):
    @wraps(funzione)
    def controllata(*args, **kwargs):
        inoltrata = request.headers.get("X-Forwarded-For") or request.headers.get("Forwarded")
        if not config.PASSWORD_PANNELLO and (inoltrata or getattr(config, "ACCESSO_REMOTO", False)):
            # Richiesta arrivata da internet (es. Tailscale Funnel) senza password impostata: blocca.
            return jsonify(errore="Accesso remoto bloccato: imposta PASSWORD_PANNELLO in config.py."), 403
        if config.PASSWORD_PANNELLO and not session.get("autorizzato") and not _interno():
            if request.path.startswith("/api/"):
                return jsonify(errore="Accesso richiesto"), 401
            return redirect("/accesso")
        return funzione(*args, **kwargs)

    return controllata


@app.route("/accesso", methods=["GET", "POST"])
def accesso():
    messaggio = ""
    ip = request.remote_addr
    if request.method == "POST":
        if _bloccato(ip):
            messaggio = "Troppi tentativi sbagliati. Riprova tra 10 minuti."
        elif config.PASSWORD_PANNELLO and secrets.compare_digest(
                request.form.get("password", ""), config.PASSWORD_PANNELLO):
            session.permanent = True
            session["autorizzato"] = True
            extra.registra("accesso", "riuscito", ip)
            return redirect("/")
        else:
            _tentativi.setdefault(ip, []).append(time.time())
            extra.registra("accesso", "PASSWORD ERRATA", ip)
            messaggio = errore_utente("Password errata.")
    with open(os.path.join(CARTELLA_WEB, "accesso.html"), encoding="utf-8") as f:
        pagina = f.read()
    if messaggio:
        from html import escape

        pagina = pagina.replace("<!--ERRORE-->", f'<p class="errore">{escape(messaggio)}</p>')
    return pagina, (401 if messaggio else 200)


# ================================ PAGINE ================================
@app.route("/")
@richiede_accesso
def pagina():
    return send_from_directory(CARTELLA_WEB, "index.html")


@app.route("/web/<nome>")
def risorse(nome):
    if nome not in FILE_WEB:
        abort(404)
    return send_from_directory(CARTELLA_WEB, nome)


@app.route("/sw.js")
def service_worker():
    """Service worker dell'app per telefono: deve stare nella radice del sito."""
    r = send_from_directory(CARTELLA_WEB, "sw.js")
    r.headers["Cache-Control"] = "no-cache"
    r.headers["Service-Worker-Allowed"] = "/"
    return r


@app.route("/vocali/<nome>")
@richiede_accesso
def vocale(nome):
    return send_from_directory(whatsapp_reader.CARTELLA_VOCALI, os.path.basename(nome))


# =============================== ANNUNCI ===============================
# Frasi che il pannello deve dire ad alta voce (es. esiti di comandi vocali).
_annunci, _blocco_annunci = [], threading.Lock()


def annuncia(testo, **extra):
    with _blocco_annunci:
        _annunci.append({"id": len(_annunci) + 1, "testo": testo, "ora": time.time(), **extra})
        del _annunci[:-100]


@app.route("/api/annunci")
@richiede_accesso
def annunci():
    dopo = int(request.args.get("dopo", 0))
    with _blocco_annunci:
        ultimo = _annunci[-1]["id"] if _annunci else 0
        return jsonify(ultimo=ultimo, annunci=[a for a in _annunci if a["id"] > dopo])


# ============================== AGENTE MSI ==============================
class AgenteMsi:
    def __init__(self):
        self.coda = []
        self.esiti = {}
        self.cond = threading.Condition()
        self.ultimo_contatto = 0
        self.stato = {}

    def online(self):
        return time.time() - self.ultimo_contatto < 60

    def invia(self, azione, parametri, attesa=25):
        if not getattr(config, "TOKEN_AGENTE_MSI", ""):
            return {"testo": "PC Msi non configurato (TOKEN_AGENTE_MSI in config.py).", "esito": "errore"}
        if not self.online():
            return {"testo": "Msi spento, fuori rete o agente non avviato.", "esito": "errore"}
        cid = secrets.token_hex(6)
        with self.cond:
            self.coda.append({"id": cid, "azione": azione, "parametri": parametri})
            self.cond.notify_all()
            fine = time.time() + attesa
            while cid not in self.esiti and time.time() < fine:
                self.cond.wait(timeout=fine - time.time())
            esito = self.esiti.pop(cid, None)
        if esito is None:
            return {"testo": "Comando inviato a Msi, nessuna conferma entro 25 secondi.", "esito": "incerto"}
        return {"esito": "ok", **esito}

    def attendi_comando(self, stato):
        with self.cond:
            self.ultimo_contatto = time.time()
            self.stato = stato or {}
            fine = time.time() + 25
            while not self.coda and time.time() < fine:
                self.cond.wait(timeout=fine - time.time())
                self.ultimo_contatto = time.time()
            return self.coda.pop(0) if self.coda else None

    def registra_esito(self, dati):
        with self.cond:
            self.esiti[dati.get("id")] = {k: v for k, v in dati.items() if k != "id"}
            self.cond.notify_all()


msi = AgenteMsi()


def _token_agente_valido():
    atteso = getattr(config, "TOKEN_AGENTE_MSI", "")
    return bool(atteso) and secrets.compare_digest(request.headers.get("X-Token-Agente", ""), atteso)


@app.route("/api/agente/attesa", methods=["POST"])
def agente_attesa():
    if not _token_agente_valido():
        abort(403)
    return jsonify(comando=msi.attendi_comando(request.get_json(silent=True)))


@app.route("/api/agente/esito", methods=["POST"])
def agente_esito():
    if not _token_agente_valido():
        abort(403)
    msi.registra_esito(request.get_json(silent=True) or {})
    return jsonify(ok=True)


# =============================== WHATSAPP ===============================
def wa(percorso, dati=None):
    corpo = json.dumps(dati).encode("utf-8") if dati is not None else None
    req = urllib.request.Request(f"{API_WHATSAPP}/{percorso}", data=corpo,
                                 method="POST" if dati is not None else "GET",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(json.loads(e.read().decode("utf-8") or "{}").get("errore", f"WhatsApp: errore {e.code}"))
    except (urllib.error.URLError, OSError):
        raise RuntimeError("Servizio WhatsApp spento.")


@app.route("/api/wa/<percorso>", methods=["GET", "POST"])
@richiede_accesso
def whatsapp(percorso):
    if percorso not in ("stato", "impostazioni", "chat", "messaggi", "invia", "inoltra", "vota", "letta"):
        abort(404)
    url = f"{API_WHATSAPP}/{percorso}"
    if request.query_string:
        url += "?" + request.query_string.decode()
    dati = request.get_data() if request.method == "POST" else None
    req = urllib.request.Request(url, data=dati, method=request.method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return app.response_class(r.read(), status=r.status, mimetype="application/json")
    except urllib.error.HTTPError as e:
        return app.response_class(e.read(), status=e.code, mimetype="application/json")
    except (urllib.error.URLError, OSError):
        return jsonify(errore="Servizio WhatsApp spento. Avvialo con avvia_server_jarvis.bat"), 503


# ============================== SEGRETERIA ==============================
@app.route("/api/segreteria")
@richiede_accesso
def segreteria():
    id_nuovi = {r.get("id") for r in whatsapp_reader.nuovi()}
    regs = whatsapp_reader.tutti()
    regs = [r for r in regs if r.get("id") in id_nuovi] if request.args.get("solo_nuovi") == "1" else regs[-50:]
    risultato = []
    for r in regs:
        contenuti = []
        for c in r.get("contenuti", []):
            v = c.get("contenuto")
            if isinstance(v, dict) and v.get("vocale"):
                contenuti.append({"vocale": "/vocali/" + v["vocale"]})
            else:
                contenuti.append({"testo": str(v)})
        risultato.append({"id": r.get("id"), "contatto": r.get("contatto"), "inizio": r.get("inizio"),
                          "stato": r.get("stato"), "chiuso_con": r.get("chiuso_con"),
                          "origine": r.get("origine"), "contenuti": contenuti, "nuovo": r.get("id") in id_nuovi})
    return jsonify(risultato)


@app.route("/api/segreteria/letti", methods=["POST"])
@richiede_accesso
def segreteria_letti():
    ids = set((request.get_json(silent=True) or {}).get("ids", []))
    whatsapp_reader.segna_letti([r for r in whatsapp_reader.tutti() if r.get("id") in ids])
    return jsonify(ok=True)


# ================================ GOOGLE ================================
def _google(funzione):
    """Esegue una funzione Google e trasforma gli errori in JSON."""
    try:
        return jsonify(funzione())
    except Exception as e:
        return jsonify(errore=str(e)), 400


@app.route("/api/gmail/lista")
@richiede_accesso
def gmail_lista():
    import gmail_reader

    q = request.args.get("q", "is:unread")
    return _google(lambda: gmail_reader.elenca_email(q, config.EMAIL_DA_MOSTRARE, request.args.get("tutta") != "1"))


@app.route("/api/gmail/email/<id_messaggio>")
@richiede_accesso
def gmail_email(id_messaggio):
    import gmail_reader

    return _google(lambda: gmail_reader.leggi_email(id_messaggio))


@app.route("/api/gmail/pulizia")
@richiede_accesso
def gmail_pulizia():
    import gmail_pulizia as gp

    return _google(gp.analizza)


@app.route("/api/gmail/pesanti")
@richiede_accesso
def gmail_pesanti():
    import gmail_pulizia as gp

    return _google(gp.email_pesanti)


@app.route("/api/gmail/azione", methods=["POST"])
@richiede_accesso
def gmail_azione():
    import gmail_reader

    d = request.get_json(silent=True) or {}
    ids = [str(i) for i in d.get("ids", [])][:500]
    azioni = {"archivia": gmail_reader.archivia, "spam": gmail_reader.segna_spam, "cestina": gmail_reader.cestina}
    if d.get("azione") == "svuota_cestino":
        if d.get("conferma") is not True:
            return jsonify(errore="Serve conferma esplicita."), 400
        return _google(lambda: {"eliminate": gmail_reader.svuota_cestino()})
    if d.get("azione") not in azioni:
        return jsonify(errore="Azione non valida"), 400
    if not ids:
        return jsonify(errore=errore_utente("Non hai selezionato nessuna email.")), 400
    return _google(lambda: {"fatte": azioni[d["azione"]](ids)})


@app.route("/api/google/spazio")
@richiede_accesso
def google_spazio():
    import gmail_reader

    return _google(gmail_reader.spazio_account)


@app.route("/api/calendario/oggi")
@richiede_accesso
def calendario_oggi():
    import gmail_reader

    return _google(gmail_reader.eventi_oggi)


# ================================ TEAMS ================================
@app.route("/api/teams/nuovi")
@richiede_accesso
def teams_nuovi():
    import teams_reader

    if not teams_reader.configurato():
        return jsonify(configurato=False, messaggi=[], avvisi=[])
    return _google(lambda: {"configurato": True, **teams_reader.nuovi_messaggi()})


@app.route("/api/teams/visti", methods=["POST"])
@richiede_accesso
def teams_visti():
    import teams_reader

    teams_reader.segna_visti((request.get_json(silent=True) or {}).get("ids", []))
    return jsonify(ok=True)


# ============================= METEO / SISTEMA =============================
_cache_meteo = {"ora": 0, "dati": None}
CODICI_METEO = {
    0: "sereno", 1: "quasi sereno", 2: "parzialmente nuvoloso", 3: "coperto", 45: "nebbia", 48: "nebbia",
    51: "pioviggine", 53: "pioviggine", 55: "pioviggine", 61: "pioggia debole", 63: "pioggia", 65: "pioggia forte",
    71: "neve debole", 73: "neve", 75: "neve forte", 80: "rovesci", 81: "rovesci", 82: "rovesci forti",
    95: "temporale", 96: "temporale con grandine", 99: "temporale con grandine",
}


def _json_url(url):
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def meteo():
    if _cache_meteo["dati"] and time.time() - _cache_meteo["ora"] < 900:
        return _cache_meteo["dati"]
    citta = getattr(config, "CITTA_METEO", "Milano")
    g = _json_url("https://geocoding-api.open-meteo.com/v1/search?count=1&language=it&name="
                  + urllib.parse.quote(citta))["results"][0]
    m = _json_url(
        "https://api.open-meteo.com/v1/forecast?timezone=auto&forecast_days=1"
        f"&latitude={g['latitude']}&longitude={g['longitude']}"
        "&current=temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m"
        "&daily=temperature_2m_max,temperature_2m_min")
    c = m["current"]
    dati = {"citta": g["name"], "temperatura": round(c["temperature_2m"]),
            "descrizione": CODICI_METEO.get(c["weather_code"], "n.d."), "codice": c["weather_code"],
            "vento": round(c["wind_speed_10m"]), "umidita": c["relative_humidity_2m"],
            "minima": round(m["daily"]["temperature_2m_min"][0]), "massima": round(m["daily"]["temperature_2m_max"][0])}
    _cache_meteo.update(ora=time.time(), dati=dati)
    return dati


@app.route("/api/meteo")
@richiede_accesso
def api_meteo():
    try:
        return jsonify(meteo())
    except Exception as e:
        return jsonify(errore=f"Meteo non disponibile: {e}"), 503


_avvio = time.time()


@app.route("/api/sistema")
@richiede_accesso
def sistema():
    dati = {"uptime_ore": round((time.time() - _avvio) / 3600, 1), "msi": {"online": msi.online(), **msi.stato}}
    try:
        import psutil

        disco = psutil.disk_usage(os.path.abspath(os.sep))
        dati.update(cpu=psutil.cpu_percent(interval=None), ram=psutil.virtual_memory().percent,
                    disco=round(disco.percent))
    except Exception:
        pass
    return jsonify(dati)


# ================================ COMANDI ================================
def _servizi():
    import gmail_pulizia
    import gmail_reader
    import teams_reader

    return {
        "msi": msi.invia, "wa": wa, "meccanica": esperto.rispondi, "chiedi": esperto.rispondi, "ricarica": esperto.ricarica, "meteo": meteo,
        "gmail_lista": lambda q: gmail_reader.elenca_email(q, config.EMAIL_DA_MOSTRARE),
        "gmail_analizza": gmail_pulizia.analizza, "spazio": gmail_reader.spazio_account,
        "eventi_oggi": gmail_reader.eventi_oggi, "evento": gmail_reader.aggiungi_evento_rapido,
        "drive_cerca": gmail_reader.cerca_drive, "teams": teams_reader.nuovi_messaggi,
        "accendi_msi": accendi_msi, "non_disturbare": non_disturbare,
        "fine_non_disturbare": fine_non_disturbare, "riepilogo": riepilogo,
    }


interprete = None


@app.route("/api/comando", methods=["POST"])
@richiede_accesso
def comando():
    global interprete
    if interprete is None:
        interprete = Interprete(_servizi())
    d = request.get_json(silent=True) or {}
    r = interprete.esegui(d.get("testo", ""))
    extra.registra("comando", f"{d.get('testo', '')} -> {r['esito']}",
                   "server (voce)" if _interno() else request.remote_addr)
    if d.get("annuncia"):
        annuncia(r["testo"], **{k: v for k, v in r.items() if k in ("azione_pannello", "immagine")})
    return jsonify(r)


# ============================ FUNZIONI EXTRA ============================
FILE_ND = os.path.join(CARTELLA_DATI, "non_disturbare.json")


def accendi_msi():
    mac = getattr(config, "MAC_MSI", "")
    if not mac:
        return {"testo": "Accensione Msi non configurata: manca MAC_MSI in config.py (GUIDA, Fase 16).", "esito": "errore"}
    if msi.online():
        return {"testo": "Msi è già acceso.", "esito": "ok"}
    extra.wake_on_lan(mac, getattr(config, "BROADCAST_RETE", "255.255.255.255"))
    return {"testo": "Segnale di accensione inviato a Msi. Serve circa un minuto.", "esito": "ok"}


def non_disturbare(ore):
    imp = wa("impostazioni")
    stato = {"fino": time.time() + ore * 3600, "modo_precedente": imp.get("risposta_automatica", "scelte")}
    if os.path.exists(FILE_ND):  # gia' attivo: conserva la modalita' originale
        with open(FILE_ND, encoding="utf-8") as f:
            stato["modo_precedente"] = json.load(f).get("modo_precedente", stato["modo_precedente"])
    wa("impostazioni", {"risposta_automatica": "tutti"})
    with open(FILE_ND, "w", encoding="utf-8") as f:
        json.dump(stato, f)
    fine = time.strftime("%H:%M", time.localtime(stato["fino"]))
    return {"testo": f"Non disturbare attivo fino alle {fine}: la segreteria risponde a tutte le chat private.", "esito": "ok"}


def fine_non_disturbare():
    if not os.path.exists(FILE_ND):
        return {"testo": "Non disturbare non era attivo.", "esito": "ok"}
    with open(FILE_ND, encoding="utf-8") as f:
        precedente = json.load(f).get("modo_precedente", "scelte")
    wa("impostazioni", {"risposta_automatica": precedente})
    os.remove(FILE_ND)
    return {"testo": "Non disturbare terminato. Segreteria ripristinata.", "esito": "ok"}


def riepilogo():
    """Riepilogo della giornata: data, meteo, agenda, posta, WhatsApp, Teams, promemoria."""
    import gmail_reader
    import teams_reader

    giorni = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
    mesi = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
            "settembre", "ottobre", "novembre", "dicembre"]
    oggi = time.localtime()
    parti = [f"Riepilogo di {giorni[oggi.tm_wday]} {oggi.tm_mday} {mesi[oggi.tm_mon - 1]}."]
    try:
        m = meteo()
        parti.append(f"Meteo {m['citta']}: {m['descrizione']}, da {m['minima']} a {m['massima']} gradi.")
    except Exception:
        pass
    try:
        ev = gmail_reader.eventi_oggi()
        parti.append("Agenda: " + ("; ".join(f"{(e['inizio'] or '')[11:16] or 'giornata'} {e['titolo']}" for e in ev)
                                   if ev else "nessun impegno") + ".")
    except Exception:
        pass
    try:
        parti.append(f"Email non lette: {gmail_reader.conta('is:unread in:inbox')}.")
    except Exception:
        pass
    try:
        chat = [c for c in wa("chat") if c["non_letti"] > 0]
        parti.append(f"WhatsApp: messaggi non letti in {len(chat)} chat.")
    except Exception:
        pass
    nuovi = [r for r in whatsapp_reader.nuovi() if r.get("stato") == "completato"]
    if nuovi:
        parti.append(f"Segreteria: {len(nuovi)} messaggi da " + ", ".join(sorted({r['contatto'] for r in nuovi})) + ".")
    if teams_reader.configurato():
        try:
            parti.append(f"Teams: {len(teams_reader.nuovi_messaggi()['messaggi'])} nuovi messaggi dei professori.")
        except Exception:
            pass
    try:
        import github_jarvis

        if github_jarvis.configurato():
            n = [x for x in github_jarvis.notifiche() if x["non_letta"]]
            parti.append(f"GitHub: {len(n)} notifiche non lette.")
    except Exception:
        pass
    oggi_iso = time.strftime("%Y-%m-%d")
    prom = [p for p in extra.promemoria() if p["quando"][:10] == oggi_iso]
    if prom:
        parti.append("Promemoria di oggi: " + "; ".join(f"{p['quando'][11:16]} {p['testo']}" for p in prom) + ".")
    return " ".join(parti)


def _a_me(testo):
    """Messaggio WhatsApp a se stessi (se il servizio e' attivo)."""
    try:
        wa("invia_a_me", {"testo": testo})
    except Exception:
        pass


def pianificatore():
    """Ogni 20 secondi: promemoria scaduti, fine non disturbare, riepilogo quotidiano."""
    ultimo_riepilogo = None
    while True:
        try:
            for p in extra.promemoria_scaduti():
                annuncia("Promemoria: " + p["testo"])
                extra.registra("promemoria", p["testo"])
                if getattr(config, "PROMEMORIA_SU_WHATSAPP", True):
                    _a_me("⏰ Promemoria Jarvis: " + p["testo"])
            if os.path.exists(FILE_ND):
                with open(FILE_ND, encoding="utf-8") as f:
                    fino = json.load(f).get("fino", 0)
                if time.time() >= fino:
                    annuncia(fine_non_disturbare()["testo"])
            ora_r = getattr(config, "ORA_RIEPILOGO", "")
            oggi = time.strftime("%Y-%m-%d")
            if ora_r and time.strftime("%H:%M") >= ora_r and ultimo_riepilogo != oggi:
                ultimo_riepilogo = oggi
                testo = riepilogo()
                annuncia(testo)
                if getattr(config, "RIEPILOGO_SU_WHATSAPP", True):
                    _a_me("📋 " + testo)
        except Exception as e:
            print("Pianificatore:", e)
        time.sleep(20)


# ================================ MEMORIA ================================
app.config["MAX_CONTENT_LENGTH"] = 210 * 1024 * 1024  # video fino a 200 MB


@app.route("/api/memoria")
@richiede_accesso
def api_memoria():
    return jsonify(fatti=memoria.fatti(), comandi=memoria.alias(), documenti=memoria.documenti(),
                   non_capiti=memoria.non_capiti())


@app.route("/api/memoria/fatto", methods=["POST"])
@richiede_accesso
def api_memoria_fatto():
    testo = ((request.get_json(silent=True) or {}).get("testo") or "").strip()
    if len(testo.split()) < 2:
        return jsonify(errore=errore_utente("Scrivi un fatto intero, non una parola.")), 400
    f = memoria.aggiungi_fatto(testo)
    esperto.ricarica()
    extra.registra("memoria", f"fatto: {testo}", request.remote_addr)
    return jsonify(ok=True, nuovo=f is not None)


@app.route("/api/memoria/comando", methods=["POST"])
@richiede_accesso
def api_memoria_comando():
    global interprete
    d = request.get_json(silent=True) or {}
    frase, comando = (d.get("frase") or "").strip(), (d.get("comando") or "").strip()
    if interprete is None:
        interprete = Interprete(_servizi())
    if not frase or not comando:
        return jsonify(errore=errore_utente("Servono sia la frase sia il comando.")), 400
    if not interprete.riconosce(comando):
        return jsonify(errore=errore_utente(f"Il comando '{comando}' non esiste. Scrivi 'aiuto' per l'elenco.")), 400
    memoria.aggiungi_alias(frase, comando)
    extra.registra("memoria", f"comando: {frase} -> {comando}", request.remote_addr)
    return jsonify(ok=True)


@app.route("/api/memoria/documento", methods=["POST"])
@richiede_accesso
def api_memoria_documento():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(errore=errore_utente("Non hai scelto nessun file.")), 400
    try:
        nome, caratteri = memoria.aggiungi_documento(f.filename, f.read())
    except ValueError as e:
        return jsonify(errore=str(e)), 400
    except Exception as e:
        return jsonify(errore=f"Impossibile leggere il file: {e}"), 400
    esperto.ricarica()
    extra.registra("memoria", f"documento: {nome}", request.remote_addr)
    return jsonify(ok=True, nome=nome, caratteri=caratteri)


@app.route("/api/memoria/elimina", methods=["POST"])
@richiede_accesso
def api_memoria_elimina():
    d = request.get_json(silent=True) or {}
    tipo, chiave = d.get("tipo"), str(d.get("id", ""))
    azioni = {"fatto": memoria.elimina_fatto, "comando": memoria.elimina_alias,
              "documento": memoria.elimina_documento, "non_capito": memoria.elimina_non_capito}
    if tipo not in azioni:
        return jsonify(errore="Tipo non valido"), 400
    azioni[tipo](chiave)
    if tipo in ("fatto", "documento"):
        esperto.ricarica()
    return jsonify(ok=True)


# ================================= VOCE =================================
@app.route("/api/voce", methods=["POST"])
@richiede_accesso
def api_voce():
    """Audio WAV con la voce di Jarvis (Piper), riprodotto dal browser di qualsiasi dispositivo."""
    import io

    import voce_jarvis

    testo = ((request.get_json(silent=True) or {}).get("testo") or "").strip()
    if not testo:
        return jsonify(errore="Testo vuoto"), 400
    try:
        dati = voce_jarvis.sintetizza(testo)
    except Exception as e:
        return jsonify(errore=f"Voce di Jarvis non disponibile: {e}"), 503
    from flask import send_file

    return send_file(io.BytesIO(dati), mimetype="audio/wav", max_age=86400)


# ============================== FOTO E VIDEO ==============================
@app.route("/media/<file>")
@richiede_accesso
def file_media(file):
    import media

    try:
        p = media.percorso(file)
    except ValueError:
        abort(404)
    return send_from_directory(os.path.dirname(p), os.path.basename(p), conditional=True)


@app.route("/api/media", methods=["GET", "POST"])
@richiede_accesso
def api_media():
    import media

    if request.method == "GET":
        return jsonify(media.elenco())
    f = request.files.get("file")
    descrizione = (request.form.get("descrizione") or "").strip()
    if not f or not f.filename:
        return jsonify(errore=errore_utente("Non hai scelto nessuna foto o video.")), 400
    if len(descrizione.split()) < 2:
        return jsonify(errore=errore_utente("Scrivi una descrizione di almeno due parole, o non la ritroverai mai.")), 400
    try:
        m = media.aggiungi(f.filename, f.stream, descrizione)
    except ValueError as e:
        return jsonify(errore=str(e)), 400
    extra.registra("media", f"{m['tipo']}: {descrizione}", request.remote_addr)
    return jsonify(m)


@app.route("/api/media/elimina", methods=["POST"])
@richiede_accesso
def api_media_elimina():
    import media

    m = media.elimina(str((request.get_json(silent=True) or {}).get("id", "")))
    return jsonify(ok=bool(m))


@app.route("/api/media/invia", methods=["POST"])
@richiede_accesso
def api_media_invia():
    import media

    d = request.get_json(silent=True) or {}
    m = media.trova(str(d.get("id", "")))
    if not m:
        return jsonify(errore="Foto o video non trovato."), 404
    if not d.get("chat"):
        return jsonify(errore=errore_utente("A chi lo mando? Non hai scelto la chat.")), 400
    try:
        r = wa("invia_media", {"chat": d["chat"], "file": m["file"], "didascalia": d.get("didascalia", "")})
    except RuntimeError as e:
        return jsonify(errore=str(e)), 503
    return jsonify(r)


# ============================ SCRITTURA A MANO ============================
def _immagine_richiesta():
    f = request.files.get("file")
    if f and f.filename:
        return f.read()
    return (request.get_json(silent=True) or {}).get("immagine") or ""


@app.route("/api/scrittura/riconosci", methods=["POST"])
@richiede_accesso
def api_scrittura_riconosci():
    import scrittura

    dati = _immagine_richiesta()
    if not dati:
        return jsonify(errore=errore_utente("Non hai scritto niente.")), 400
    try:
        return jsonify(scrittura.riconosci(dati))
    except ValueError as e:
        return jsonify(errore=str(e)), 400
    except Exception as e:
        return jsonify(errore=f"Immagine non leggibile: {e}"), 400


@app.route("/api/scrittura/correggi", methods=["POST"])
@richiede_accesso
def api_scrittura_correggi():
    import scrittura

    d = request.get_json(silent=True) or {}
    try:
        r = scrittura.correggi(str(d.get("sessione", "")), d.get("correzioni") or {})
    except ValueError as e:
        return jsonify(errore=str(e)), 400
    extra.registra("scrittura", f"imparate {r['lettere_imparate']} lettere", request.remote_addr)
    return jsonify(r)


@app.route("/api/scrittura/allena", methods=["POST"])
@richiede_accesso
def api_scrittura_allena():
    import scrittura

    d = request.get_json(silent=True) or {}
    try:
        return jsonify(scrittura.allena(d.get("immagine") or "", str(d.get("lettera", ""))))
    except ValueError as e:
        return jsonify(errore=str(e)), 400


@app.route("/api/scrittura/stato")
@richiede_accesso
def api_scrittura_stato():
    import scrittura

    return jsonify(scrittura.stato())


# ================================ GITHUB ================================
def _gh(funzione):
    import github_jarvis

    try:
        return jsonify(funzione(github_jarvis))
    except github_jarvis.ErroreGitHub as e:
        return jsonify(errore=str(e)), 400


@app.route("/api/github")
@richiede_accesso
def api_github():
    import github_jarvis as g

    if not g.configurato():
        return jsonify(configurato=False)
    dati = {"configurato": True}
    for chiave, funzione in (("profilo", g.profilo), ("notifiche", g.notifiche), ("pr", g.pr_aperte),
                             ("issue", g.issue_aperte), ("repository", lambda: g.repository(30))):
        try:
            dati[chiave] = funzione()
        except g.ErroreGitHub as e:
            dati.setdefault("errori", []).append(str(e))
    return jsonify(dati)


@app.route("/api/github/token", methods=["POST"])
@richiede_accesso
def api_github_token():
    valore = (request.get_json(silent=True) or {}).get("token", "")
    r = _gh(lambda g: g.salva_token(valore))
    rifiutato = isinstance(r, tuple)  # (risposta, 400) in caso di errore
    extra.registra("github", "token rifiutato" if rifiutato else "token collegato", request.remote_addr)
    return r


@app.route("/api/github/scollega", methods=["POST"])
@richiede_accesso
def api_github_scollega():
    import github_jarvis

    github_jarvis.elimina_token()
    extra.registra("github", "scollegato", request.remote_addr)
    return jsonify(ok=True)


@app.route("/api/github/file", methods=["POST"])
@richiede_accesso
def api_github_file():
    d = request.get_json(silent=True) or {}
    return _gh(lambda g: g.leggi_file(g.trova_repo(d.get("repo", "")), d.get("percorso", "")))


@app.route("/api/github/salva_file", methods=["POST"])
@richiede_accesso
def api_github_salva_file():
    d = request.get_json(silent=True) or {}
    if not d.get("percorso") or d.get("testo") is None:
        return jsonify(errore=errore_utente("Servono percorso e contenuto del file.")), 400
    r = _gh(lambda g: g.scrivi_file(g.trova_repo(d.get("repo", "")), d["percorso"], d["testo"], d.get("messaggio", "")))
    extra.registra("github", f"file {d.get('repo')}/{d['percorso']}", request.remote_addr)
    return r


@app.route("/api/github/build", methods=["POST"])
@richiede_accesso
def api_github_build():
    d = request.get_json(silent=True) or {}
    return _gh(lambda g: g.stato_build(g.trova_repo(d.get("repo", ""))))


@app.route("/api/github/unisci", methods=["POST"])
@richiede_accesso
def api_github_unisci():
    d = request.get_json(silent=True) or {}
    if d.get("conferma") is not True:
        return jsonify(errore="Serve conferma esplicita."), 400
    r = _gh(lambda g: g.unisci_pr(d.get("repo", ""), d.get("numero", 0)))
    extra.registra("github", f"unione PR {d.get('repo')}#{d.get('numero')}", request.remote_addr)
    return r


@app.route("/api/github/notifiche_lette", methods=["POST"])
@richiede_accesso
def api_github_lette():
    return _gh(lambda g: (g.segna_notifiche_lette(), {"ok": True})[1])


# ============================ APP PER TELEFONO ============================
@app.route("/api/telefono")
@richiede_accesso
def api_telefono():
    """Indirizzi da aprire sul telefono e relativo codice QR."""
    import socket

    indirizzi = []
    if getattr(config, "INDIRIZZO_TELEFONO", ""):
        indirizzi.append(config.INDIRIZZO_TELEFONO)
    if config.HOST_PANNELLO not in ("127.0.0.1", "localhost"):
        try:
            s_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s_udp.connect(("10.255.255.255", 1))
            indirizzi.append(f"http://{s_udp.getsockname()[0]}:{config.PORTA_PANNELLO}")
            s_udp.close()
        except OSError:
            pass
    qr = None
    if indirizzi:
        try:
            import segno

            qr = segno.make(indirizzi[0], error="m").svg_data_uri(scale=6, dark="#00e0ff", light="#03080f", border=2)
        except ImportError:
            qr = None
    return jsonify(indirizzi=indirizzi, qr=qr, solo_locale=config.HOST_PANNELLO in ("127.0.0.1", "localhost"))


@app.route("/api/promemoria")
@richiede_accesso
def api_promemoria():
    return jsonify(promemoria=extra.promemoria(), note=extra.note())


@app.route("/api/registro")
@richiede_accesso
def api_registro():
    return jsonify(extra.registro(150))


@app.route("/api/profilo")
@richiede_accesso
def profilo():
    import voce_jarvis

    voce_server = getattr(config, "VOCE_MOTORE", "piper") == "piper" and voce_jarvis.disponibile()
    return jsonify(nome=config.NOME_UTENTE, stile_saggio=config.STILE_SAGGIO, voce_server=voce_server,
                   manuali=esperto.manuali_caricati(), insulti=getattr(config, "INSULTI_ATTIVI", True))


def avvia():
    host = config.HOST_PANNELLO
    remoto = host not in ("127.0.0.1", "localhost") or getattr(config, "ACCESSO_REMOTO", False)
    if remoto and not config.PASSWORD_PANNELLO:
        print("ERRORE: per rendere Jarvis raggiungibile da altri dispositivi devi impostare\n"
              "PASSWORD_PANNELLO in config.py. Avvio annullato.")
        sys.exit(1)
    if config.PASSWORD_PANNELLO and len(config.PASSWORD_PANNELLO) < 12:
        print("ERRORE: PASSWORD_PANNELLO troppo corta (minimo 12 caratteri). Avvio annullato.")
        sys.exit(1)
    print(f"Pannello Jarvis attivo su http://localhost:{config.PORTA_PANNELLO}")
    threading.Thread(target=pianificatore, daemon=True).start()
    try:
        from waitress import serve

        # clear_untrusted_proxy_headers=False: serve per riconoscere le richieste inoltrate da internet
        serve(app, host=host, port=config.PORTA_PANNELLO, threads=24, channel_timeout=60,
              clear_untrusted_proxy_headers=False)
    except ImportError:
        app.run(host=host, port=config.PORTA_PANNELLO, threaded=True)


if __name__ == "__main__":
    avvia()
