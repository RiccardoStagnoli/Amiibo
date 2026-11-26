"""
Jarvis - Spotify (Web API ufficiale, gratuita).

- Cosa sto ascoltando, cerca e riproduci, pausa, avanti, indietro, volume.
- ATTENZIONE: Spotify permette di COMANDARE la riproduzione solo con account Premium.
  Senza Premium Jarvis apre Spotify sul PC Msi con la ricerca (poi premi play).
- Accesso: una volta, dal browser del PC SERVER: http://127.0.0.1:8080/spotify/accedi
  (Spotify accetta come indirizzo di ritorno solo 127.0.0.1, non "localhost" ne' altri dispositivi).
"""

import base64
import hashlib
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

import config

CARTELLA = os.path.dirname(os.path.abspath(__file__))
FILE_TOKEN = os.path.join(CARTELLA, "dati", "spotify_token.json")
API = "https://api.spotify.com/v1"
CONTI = "https://accounts.spotify.com"
PERMESSI = ("user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private "
            "user-top-read user-read-recently-played")
_attesa = {}  # state -> code_verifier


class ErroreSpotify(Exception):
    pass


def indirizzo_ritorno():
    return f"http://127.0.0.1:{config.PORTA_PANNELLO}/spotify/callback"


def configurato():
    return bool(getattr(config, "SPOTIFY_CLIENT_ID", "")) and os.path.exists(FILE_TOKEN)


def url_accesso():
    if not getattr(config, "SPOTIFY_CLIENT_ID", ""):
        raise ErroreSpotify("Manca SPOTIFY_CLIENT_ID in config.py (GUIDA, Fase 27).")
    verifier = secrets.token_urlsafe(64)[:100]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    stato = secrets.token_urlsafe(16)
    _attesa[stato] = verifier
    q = urllib.parse.urlencode({"client_id": config.SPOTIFY_CLIENT_ID, "response_type": "code",
                                "redirect_uri": indirizzo_ritorno(), "code_challenge_method": "S256",
                                "code_challenge": challenge, "scope": PERMESSI, "state": stato})
    return f"{CONTI}/authorize?{q}"


def _token_richiesta(dati):
    req = urllib.request.Request(f"{CONTI}/api/token", data=urllib.parse.urlencode(dati).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            t = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise ErroreSpotify(f"Spotify ha rifiutato l'accesso (errore {e.code}).")
    t["scade"] = time.time() + t.get("expires_in", 3600) - 60
    vecchio = _leggi()
    if "refresh_token" not in t and vecchio:
        t["refresh_token"] = vecchio.get("refresh_token")
    os.makedirs(os.path.dirname(FILE_TOKEN), exist_ok=True)
    with open(FILE_TOKEN, "w", encoding="utf-8") as f:
        json.dump(t, f)
    return t


def completa_accesso(codice, stato):
    verifier = _attesa.pop(stato, None)
    if not verifier:
        raise ErroreSpotify("Richiesta di accesso scaduta: riprova da /spotify/accedi.")
    _token_richiesta({"grant_type": "authorization_code", "code": codice, "redirect_uri": indirizzo_ritorno(),
                      "client_id": config.SPOTIFY_CLIENT_ID, "code_verifier": verifier})


def _leggi():
    try:
        with open(FILE_TOKEN, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _token():
    t = _leggi()
    if not t:
        raise ErroreSpotify("Spotify non collegato: dal PC server apri http://127.0.0.1:8080/spotify/accedi (GUIDA, Fase 27).")
    if time.time() > t.get("scade", 0):
        t = _token_richiesta({"grant_type": "refresh_token", "refresh_token": t["refresh_token"],
                              "client_id": config.SPOTIFY_CLIENT_ID})
    return t["access_token"]


def _api(metodo, percorso, dati=None):
    corpo = json.dumps(dati).encode() if dati is not None else (b"" if metodo in ("PUT", "POST") else None)
    req = urllib.request.Request(API + percorso, data=corpo, method=metodo,
                                 headers={"Authorization": "Bearer " + _token(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            testo = r.read().decode()
            return json.loads(testo) if testo else {}
    except urllib.error.HTTPError as e:
        corpo = e.read().decode(errors="ignore")
        if e.code == 403 and "PREMIUM" in corpo.upper():
            raise ErroreSpotify("PREMIUM")
        if e.code == 404:
            raise ErroreSpotify("Nessun dispositivo Spotify attivo: apri Spotify su PC o telefono e riprova.")
        raise ErroreSpotify(f"Spotify: errore {e.code}.")


def in_ascolto():
    r = _api("GET", "/me/player/currently-playing")
    if not r or not r.get("item"):
        return None
    brano = r["item"]
    return {"titolo": brano.get("name"), "artisti": ", ".join(a["name"] for a in brano.get("artists", [])),
            "in_riproduzione": r.get("is_playing", False)}


def cerca(testo, tipo="track"):
    r = _api("GET", "/search?" + urllib.parse.urlencode({"q": testo, "type": tipo, "limit": 1, "market": "from_token"}))
    elementi = (r.get(tipo + "s") or {}).get("items") or []
    return elementi[0] if elementi else None


def riproduci(testo):
    """Cerca un brano (o una playlist se contiene 'playlist') e lo fa partire."""
    tipo = "playlist" if "playlist" in testo.lower() else "track"
    query = testo.lower().replace("playlist", "").strip()
    trovato = cerca(query, tipo)
    if not trovato:
        return f"Su Spotify non ho trovato '{testo}'."
    dati = {"context_uri": trovato["uri"]} if tipo == "playlist" else {"uris": [trovato["uri"]]}
    _api("PUT", "/me/player/play", dati)
    nome = trovato.get("name")
    artisti = ", ".join(a["name"] for a in trovato.get("artists", [])) if tipo == "track" else ""
    return f"Su Spotify: {nome}" + (f" di {artisti}" if artisti else "") + "."


def comando(azione, valore=None):
    if azione == "pausa":
        _api("PUT", "/me/player/pause")
        return "Spotify in pausa."
    if azione == "riprendi":
        _api("PUT", "/me/player/play")
        return "Spotify riprende."
    if azione == "avanti":
        _api("POST", "/me/player/next")
        return "Brano successivo."
    if azione == "indietro":
        _api("POST", "/me/player/previous")
        return "Brano precedente."
    if azione == "volume":
        _api("PUT", f"/me/player/volume?volume_percent={max(0, min(100, int(valore)))}")
        return f"Volume Spotify al {int(valore)}%."
    raise ErroreSpotify("Comando Spotify sconosciuto.")


def artisti_preferiti(quanti=10):
    """Artisti piu' ascoltati nelle ultime settimane (permesso user-top-read)."""
    r = _api("GET", f"/me/top/artists?time_range=short_term&limit={quanti}")
    return [a["name"] for a in r.get("items", [])]


def generi_preferiti(quanti=20):
    r = _api("GET", f"/me/top/artists?time_range=medium_term&limit={quanti}")
    from collections import Counter

    return [g for g, _ in Counter(g for a in r.get("items", []) for g in a.get("genres", [])).most_common(8)]
