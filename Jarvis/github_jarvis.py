"""
Jarvis - Accesso a GitHub (API ufficiale, gratuita).

Serve un "Personal access token" creato da te su GitHub (GUIDA, Fase 22),
inserito una volta dal pannello (Impostazioni -> GitHub). Il token viene salvato
solo sul PC server, in dati/.github_token, e non viene mai mostrato.

Funzioni: profilo, repository, notifiche, issue e pull request, stato delle
build (Actions), ricerca, stelle, lettura e modifica di file, creazione di
repository e issue, commenti, chiusura issue, unione pull request.
"""

import base64
import difflib
import json
import os
import urllib.error
import urllib.parse
import urllib.request

import config

CARTELLA = os.path.dirname(os.path.abspath(__file__))
FILE_TOKEN = os.path.join(CARTELLA, "dati", ".github_token")
SOGLIA = 0.90


class ErroreGitHub(Exception):
    pass


def _api():
    return getattr(config, "GITHUB_API", "https://api.github.com").rstrip("/")


# ================================ TOKEN ================================
def token():
    try:
        with open(FILE_TOKEN, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def salva_token(valore):
    valore = (valore or "").strip()
    if not valore.startswith(("ghp_", "github_pat_")) or len(valore) < 30:
        raise ErroreGitHub("Token non valido: deve iniziare con 'github_pat_' o 'ghp_'.")
    os.makedirs(os.path.dirname(FILE_TOKEN), exist_ok=True)
    with open(FILE_TOKEN, "w", encoding="utf-8") as f:
        f.write(valore)
    try:
        return profilo()
    except ErroreGitHub:
        os.remove(FILE_TOKEN)
        raise


def elimina_token():
    if os.path.exists(FILE_TOKEN):
        os.remove(FILE_TOKEN)


def configurato():
    return bool(token())


# ================================ RICHIESTE ================================
def _chiama(metodo, percorso, dati=None, autenticato=True):
    url = percorso if percorso.startswith("http") else _api() + percorso
    intestazioni = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "Jarvis-assistente"}
    if autenticato:
        t = token()
        if not t:
            raise ErroreGitHub("GitHub non collegato: inserisci il token in Impostazioni → GitHub (GUIDA, Fase 22).")
        intestazioni["Authorization"] = "Bearer " + t
    corpo = None
    if dati is not None:
        corpo = json.dumps(dati).encode("utf-8")
        intestazioni["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=corpo, method=metodo, headers=intestazioni)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            testo = r.read().decode("utf-8")
            return json.loads(testo) if testo else {}
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8")).get("message", "")
        except ValueError:
            msg = ""
        spiegazioni = {401: "token non valido o scaduto", 403: "permesso negato (controlla i permessi del token)",
                       404: "non trovato, oppure il token non ha accesso", 409: "conflitto", 422: "dati non validi"}
        raise ErroreGitHub(f"GitHub: {spiegazioni.get(e.code, 'errore ' + str(e.code))}. {msg}".strip())
    except urllib.error.URLError as e:
        raise ErroreGitHub(f"GitHub non raggiungibile: {e.reason}")


# ================================ LETTURA ================================
def profilo():
    u = _chiama("GET", "/user")
    return {"utente": u.get("login"), "nome": u.get("name"), "repo_pubblici": u.get("public_repos"),
            "repo_privati": u.get("total_private_repos"), "url": u.get("html_url")}


def repository(n=50):
    r = _chiama("GET", f"/user/repos?sort=updated&per_page={n}&affiliation=owner,collaborator,organization_member")
    return [{"nome": x["full_name"], "privato": x["private"], "descrizione": x.get("description") or "",
             "stelle": x.get("stargazers_count", 0), "aggiornato": x.get("pushed_at"), "url": x["html_url"],
             "ramo": x.get("default_branch")} for x in r]


def trova_repo(nome):
    """Trova un tuo repository dal nome (anche senza proprietario), con la regola del 90%."""
    nome = nome.strip().strip("/").lower()
    lista = repository(100)
    for x in lista:
        if x["nome"].lower() == nome or x["nome"].split("/")[1].lower() == nome:
            return x["nome"]
    punteggi = sorted(((difflib.SequenceMatcher(None, nome, x["nome"].split("/")[1].lower()).ratio(), x["nome"])
                       for x in lista), reverse=True)
    if punteggi and punteggi[0][0] >= SOGLIA and (len(punteggi) == 1 or punteggi[1][0] < punteggi[0][0] - 0.05):
        return punteggi[0][1]
    if "/" in nome:  # repository di altri, scritto per intero
        return nome
    simili = ", ".join(p[1] for p in punteggi[:3])
    raise ErroreGitHub(f"Nessun tuo repository corrisponde al 90% a '{nome}'. Simili: {simili or 'nessuno'}.")


def notifiche(tutte=False):
    r = _chiama("GET", f"/notifications?all={'true' if tutte else 'false'}&per_page=50")
    return [{"id": x["id"], "repo": x["repository"]["full_name"], "tipo": x["subject"]["type"],
             "titolo": x["subject"]["title"], "motivo": x.get("reason"), "ora": x.get("updated_at"),
             "non_letta": x.get("unread", False)} for x in r]


def segna_notifiche_lette():
    _chiama("PUT", "/notifications", {"read": True})


def _cerca_issue(q, n=30):
    r = _chiama("GET", "/search/issues?per_page=%d&q=%s" % (n, urllib.parse.quote(q)))
    return [{"repo": x["repository_url"].split("/repos/")[1], "numero": x["number"], "titolo": x["title"],
             "pr": "pull_request" in x, "autore": x["user"]["login"], "ora": x.get("updated_at"),
             "url": x["html_url"]} for x in r.get("items", [])]


def issue_aperte():
    return _cerca_issue("is:open is:issue involves:@me archived:false")


def pr_aperte():
    return _cerca_issue("is:open is:pr involves:@me archived:false")


def stato_build(repo):
    r = _chiama("GET", f"/repos/{repo}/actions/runs?per_page=5")
    return [{"nome": x.get("name"), "ramo": x.get("head_branch"), "stato": x.get("status"),
             "esito": x.get("conclusion"), "ora": x.get("updated_at"), "url": x.get("html_url")}
            for x in r.get("workflow_runs", [])]


def cerca_repository(testo, n=10):
    r = _chiama("GET", "/search/repositories?per_page=%d&q=%s" % (n, urllib.parse.quote(testo)),
                autenticato=configurato())
    return [{"nome": x["full_name"], "stelle": x["stargazers_count"], "descrizione": x.get("description") or "",
             "url": x["html_url"]} for x in r.get("items", [])]


def leggi_file(repo, percorso, ramo=None):
    q = f"?ref={urllib.parse.quote(ramo)}" if ramo else ""
    r = _chiama("GET", f"/repos/{repo}/contents/{urllib.parse.quote(percorso.strip('/'))}{q}")
    if isinstance(r, list):
        return {"cartella": True, "voci": [x["name"] + ("/" if x["type"] == "dir" else "") for x in r]}
    if r.get("encoding") != "base64":
        raise ErroreGitHub("File non leggibile come testo.")
    testo = base64.b64decode(r["content"]).decode("utf-8", errors="replace")
    return {"cartella": False, "testo": testo, "sha": r["sha"], "dimensione": r.get("size")}


# ================================ SCRITTURA ================================
def crea_issue(repo, titolo, testo=""):
    r = _chiama("POST", f"/repos/{repo}/issues", {"title": titolo, "body": testo})
    return {"numero": r["number"], "url": r["html_url"]}


def commenta(repo, numero, testo):
    r = _chiama("POST", f"/repos/{repo}/issues/{int(numero)}/comments", {"body": testo})
    return {"url": r["html_url"]}


def chiudi_issue(repo, numero):
    _chiama("PATCH", f"/repos/{repo}/issues/{int(numero)}", {"state": "closed"})


def metti_stella(repo):
    _chiama("PUT", f"/user/starred/{repo}")


def crea_repository(nome, privato=True, descrizione=""):
    r = _chiama("POST", "/user/repos", {"name": nome, "private": privato, "description": descrizione,
                                         "auto_init": True})
    return {"nome": r["full_name"], "url": r["html_url"]}


def scrivi_file(repo, percorso, testo, messaggio, ramo=None):
    """Crea o aggiorna un file con un commit."""
    dati = {"message": messaggio or f"Aggiorna {percorso} (Jarvis)",
            "content": base64.b64encode(testo.encode("utf-8")).decode("ascii")}
    if ramo:
        dati["branch"] = ramo
    try:
        dati["sha"] = leggi_file(repo, percorso, ramo)["sha"]
    except ErroreGitHub:
        pass  # file nuovo
    r = _chiama("PUT", f"/repos/{repo}/contents/{urllib.parse.quote(percorso.strip('/'))}", dati)
    return {"commit": r["commit"]["sha"][:7], "url": r["content"]["html_url"]}


def unisci_pr(repo, numero, metodo="squash"):
    r = _chiama("PUT", f"/repos/{repo}/pulls/{int(numero)}/merge", {"merge_method": metodo})
    return {"unita": r.get("merged", False), "messaggio": r.get("message", "")}
