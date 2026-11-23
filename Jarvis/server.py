"""
JARVIS - Server del pannello web.

Avvia il pannello futuristico su http://localhost:8080 (porta in config.py).
Collega: Gmail, manuale di meccanica, servizio WhatsApp (whatsapp/servizio_whatsapp.js).
"""

import os
import secrets
import sys
import urllib.error
import urllib.request
from functools import wraps

from flask import Flask, abort, jsonify, redirect, request, send_from_directory, session

import config
import whatsapp_reader
from meccanica import EspertoMeccanica

CARTELLA = os.path.dirname(os.path.abspath(__file__))
CARTELLA_WEB = os.path.join(CARTELLA, "web")
CARTELLA_DATI = os.path.join(CARTELLA, "dati")
API_WHATSAPP = "http://127.0.0.1:3010"

os.makedirs(CARTELLA_DATI, exist_ok=True)


def _chiave_segreta():
    file_chiave = os.path.join(CARTELLA_DATI, ".chiave_sessione")
    if not os.path.exists(file_chiave):
        with open(file_chiave, "w", encoding="utf-8") as f:
            f.write(secrets.token_hex(32))
    with open(file_chiave, encoding="utf-8") as f:
        return f.read().strip()


app = Flask(__name__, static_folder=None)
app.secret_key = _chiave_segreta()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict")

esperto = EspertoMeccanica()


# ------------------------------- ACCESSO -------------------------------
def richiede_accesso(funzione):
    @wraps(funzione)
    def controllata(*args, **kwargs):
        if config.PASSWORD_PANNELLO and not session.get("autorizzato"):
            if request.path.startswith("/api/"):
                return jsonify(errore="Accesso richiesto"), 401
            return redirect("/accesso")
        return funzione(*args, **kwargs)

    return controllata


@app.route("/accesso", methods=["GET", "POST"])
def accesso():
    errore = ""
    if request.method == "POST":
        if config.PASSWORD_PANNELLO and secrets.compare_digest(
            request.form.get("password", ""), config.PASSWORD_PANNELLO
        ):
            session["autorizzato"] = True
            return redirect("/")
        errore = '<p class="errore">Password errata</p>'
    with open(os.path.join(CARTELLA_WEB, "accesso.html"), encoding="utf-8") as f:
        return f.read().replace("<!--ERRORE-->", errore), (401 if errore else 200)


# -------------------------------- PAGINE --------------------------------
@app.route("/")
@richiede_accesso
def pagina():
    return send_from_directory(CARTELLA_WEB, "index.html")


@app.route("/web/<path:nome>")
def risorse(nome):
    if nome not in ("style.css", "app.js"):
        abort(404)
    return send_from_directory(CARTELLA_WEB, nome)


@app.route("/vocali/<nome>")
@richiede_accesso
def vocale(nome):
    return send_from_directory(whatsapp_reader.CARTELLA_VOCALI, os.path.basename(nome))


# ------------------------------ API: GENERALE ------------------------------
@app.route("/api/profilo")
@richiede_accesso
def profilo():
    return jsonify(
        nome=config.NOME_UTENTE,
        stile_saggio=config.STILE_SAGGIO,
        manuali=esperto.manuali_caricati(),
    )


# ---------------------------- API: SEGRETERIA ----------------------------
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
        risultato.append(
            {
                "id": r.get("id"),
                "contatto": r.get("contatto"),
                "inizio": r.get("inizio"),
                "stato": r.get("stato"),
                "chiuso_con": r.get("chiuso_con"),
                "origine": r.get("origine"),
                "contenuti": contenuti,
                "nuovo": r.get("id") in id_nuovi,
            }
        )
    return jsonify(risultato)


@app.route("/api/segreteria/letti", methods=["POST"])
@richiede_accesso
def segreteria_letti():
    ids = set((request.get_json(silent=True) or {}).get("ids", []))
    whatsapp_reader.segna_letti([r for r in whatsapp_reader.tutti() if r.get("id") in ids])
    return jsonify(ok=True)


# ------------------------------ API: WHATSAPP ------------------------------
@app.route("/api/wa/<percorso>", methods=["GET", "POST"])
@richiede_accesso
def whatsapp(percorso):
    if percorso not in ("stato", "impostazioni", "chat", "messaggi", "invia", "inoltra", "vota", "letta"):
        abort(404)
    url = f"{API_WHATSAPP}/{percorso}"
    if request.query_string:
        url += "?" + request.query_string.decode()
    dati = request.get_data() if request.method == "POST" else None
    req = urllib.request.Request(
        url, data=dati, method=request.method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return app.response_class(r.read(), status=r.status, mimetype="application/json")
    except urllib.error.HTTPError as e:
        return app.response_class(e.read(), status=e.code, mimetype="application/json")
    except (urllib.error.URLError, OSError):
        return jsonify(errore="Servizio WhatsApp spento. Avvialo con avvia_server_jarvis.bat"), 503


# -------------------------------- API: GMAIL --------------------------------
@app.route("/api/gmail/lista")
@richiede_accesso
def gmail_lista():
    try:
        import gmail_reader

        q = request.args.get("q", "is:unread")
        tutta = request.args.get("tutta") == "1"
        return jsonify(gmail_reader.elenca_email(q, config.EMAIL_DA_MOSTRARE, not tutta))
    except Exception as e:  # credenziali mancanti, rete, ecc.
        return jsonify(errore=str(e)), 400


@app.route("/api/gmail/email/<id_messaggio>")
@richiede_accesso
def gmail_email(id_messaggio):
    try:
        import gmail_reader

        return jsonify(gmail_reader.leggi_email(id_messaggio))
    except Exception as e:
        return jsonify(errore=str(e)), 400


# ------------------------------ API: MECCANICA ------------------------------
@app.route("/api/meccanica", methods=["POST"])
@richiede_accesso
def meccanica():
    domanda = ((request.get_json(silent=True) or {}).get("domanda") or "").strip()
    if not domanda:
        return jsonify(errore="Domanda vuota"), 400
    risposta, brani = esperto.rispondi(domanda)
    return jsonify(
        risposta=risposta,
        fonti=[{"manuale": b["manuale"], "sezione": b["sezione"]} for b in brani],
    )


def avvia():
    host = config.HOST_PANNELLO
    if host not in ("127.0.0.1", "localhost") and not config.PASSWORD_PANNELLO:
        print(
            "ERRORE: per rendere Jarvis raggiungibile da altri dispositivi devi impostare\n"
            "PASSWORD_PANNELLO in config.py. Avvio annullato."
        )
        sys.exit(1)
    print(f"Pannello Jarvis attivo su http://localhost:{config.PORTA_PANNELLO}")
    try:
        from waitress import serve

        serve(app, host=host, port=config.PORTA_PANNELLO, threads=8)
    except ImportError:
        app.run(host=host, port=config.PORTA_PANNELLO, threaded=True)


if __name__ == "__main__":
    avvia()
