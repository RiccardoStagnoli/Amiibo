"""
Jarvis - Discord tramite un BOT (API ufficiale, gratuita).

Un bot puo' leggere e scrivere SOLO nei server in cui lo aggiungi tu.
Leggere i tuoi messaggi privati o controllare il tuo account personale con un
programma ("self-bot") e' vietato dalle regole di Discord e puo' far chiudere l'account:
Jarvis non lo fa.

config.py:
  DISCORD_BOT_TOKEN = "..."                       (dal Developer Portal)
  DISCORD_CANALI = {"generale": "123456789012345678", "compiti": "..."}
"""

import json
import urllib.error
import urllib.request

import config

API = "https://discord.com/api/v10"


class ErroreDiscord(Exception):
    pass


def configurato():
    return bool(getattr(config, "DISCORD_BOT_TOKEN", "")) and bool(getattr(config, "DISCORD_CANALI", {}))


def _api(metodo, percorso, dati=None):
    if not getattr(config, "DISCORD_BOT_TOKEN", ""):
        raise ErroreDiscord("Discord non collegato: manca DISCORD_BOT_TOKEN in config.py (GUIDA, Fase 28).")
    req = urllib.request.Request(getattr(config, "DISCORD_API", API) + percorso, method=metodo,
                                 data=json.dumps(dati).encode() if dati is not None else None,
                                 headers={"Authorization": "Bot " + config.DISCORD_BOT_TOKEN,
                                          "Content-Type": "application/json",
                                          "User-Agent": "DiscordBot (jarvis, 1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            testo = r.read().decode()
            return json.loads(testo) if testo else {}
    except urllib.error.HTTPError as e:
        spiegazioni = {401: "token del bot non valido", 403: "il bot non ha il permesso in quel canale",
                       404: "canale non trovato"}
        raise ErroreDiscord(f"Discord: {spiegazioni.get(e.code, 'errore ' + str(e.code))}.")


def canale(nome):
    import difflib

    canali = {k.lower(): v for k, v in getattr(config, "DISCORD_CANALI", {}).items()}
    if not canali:
        raise ErroreDiscord("Nessun canale in DISCORD_CANALI (config.py).")
    n = (nome or "").lower().strip("# ")
    if not n:
        return next(iter(canali.items()))
    if n in canali:
        return n, canali[n]
    simili = difflib.get_close_matches(n, list(canali), n=1, cutoff=0.9)
    if simili:
        return simili[0], canali[simili[0]]
    raise ErroreDiscord(f"Nessun canale Discord '{nome}'. Canali: {', '.join(canali)}.")


def ultimi_messaggi(nome_canale=None, quanti=10):
    nome, cid = canale(nome_canale)
    r = _api("GET", f"/channels/{cid}/messages?limit={quanti}")
    return nome, [{"autore": m.get("author", {}).get("global_name") or m.get("author", {}).get("username", "?"),
                   "testo": m.get("content") or "[allegato o contenuto non visibile]", "ora": m.get("timestamp")}
                  for m in reversed(r)]


def scrivi(nome_canale, testo):
    nome, cid = canale(nome_canale)
    _api("POST", f"/channels/{cid}/messages", {"content": testo[:2000]})
    return nome
