"""
JARVIS - Controllo completo di Google Chrome sul PC Msi.

Usa il Chrome DevTools Protocol (lo stesso degli strumenti di automazione):
schede, navigazione, lettura della pagina, clic, scrittura, scorrimento,
screenshot, video (pausa/riproduci).

Da Chrome 136 il controllo remoto NON e' permesso sul profilo normale di Chrome,
quindi Jarvis usa un PROFILO DEDICATO ("Chrome di Jarvis", cartella chrome_jarvis).
Al primo avvio accedi con il tuo account Google in quella finestra e attiva la
sincronizzazione: avrai segnalibri, password e cronologia.

Sicurezza: la porta di controllo (9222) e' aperta solo su 127.0.0.1 (questo PC).
"""

import difflib
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request

PORTA = 9222
CARTELLA = os.path.dirname(os.path.abspath(__file__))
PROFILO = os.path.join(CARTELLA, "chrome_jarvis")
SOGLIA = 0.90
PERCORSI_CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]


class ErroreChrome(Exception):
    pass


# ------------------------------- avvio -------------------------------
def _http(percorso, metodo="GET", timeout=5):
    req = urllib.request.Request(f"http://127.0.0.1:{PORTA}{percorso}", method=metodo)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        corpo = r.read().decode("utf-8")
    try:
        return json.loads(corpo)
    except ValueError:
        return corpo


def attivo():
    try:
        _http("/json/version", timeout=2)
        return True
    except OSError:
        return False


def avvia(eseguibile=None):
    """Apre il Chrome di Jarvis (se non e' gia' aperto)."""
    if attivo():
        return False
    exe = eseguibile or next((p for p in PERCORSI_CHROME if os.path.exists(p)), None)
    if not exe:
        raise ErroreChrome("Google Chrome non trovato sul PC Msi.")
    os.makedirs(PROFILO, exist_ok=True)
    subprocess.Popen([exe, f"--remote-debugging-port={PORTA}", "--remote-debugging-address=127.0.0.1",
                      f"--user-data-dir={PROFILO}", "--no-first-run", "--no-default-browser-check",
                      "--start-maximized"])
    for _ in range(40):
        time.sleep(0.25)
        if attivo():
            return True
    raise ErroreChrome("Chrome non risponde al controllo (porta 9222).")


def _assicura():
    if not attivo():
        avvia()


# ------------------------------- schede -------------------------------
def schede():
    _assicura()
    return [t for t in _http("/json/list") if t.get("type") == "page"]


def _scheda_attiva():
    lista = schede()
    if not lista:
        return nuova_scheda("about:blank")
    return lista[0]  # Chrome elenca per prima la scheda usata piu' di recente


def nuova_scheda(url):
    _assicura()
    t = _http("/json/new?" + urllib.parse.quote(url, safe=":/?&=%#+@,;~"), metodo="PUT")
    _http(f"/json/activate/{t['id']}")
    return t


def _trova_scheda(nome):
    lista = schede()
    n = nome.lower().strip()
    candidati = []
    for t in lista:
        titolo, url = t.get("title", "").lower(), t.get("url", "").lower()
        if n in titolo or n in url:
            candidati.append((1.0, t))
        else:
            candidati.append((difflib.SequenceMatcher(None, n, titolo).ratio(), t))
    candidati.sort(key=lambda x: -x[0])
    if not candidati or candidati[0][0] < SOGLIA:
        simili = ", ".join(t.get("title", "")[:40] for _, t in candidati[:3])
        raise ErroreChrome(f"Nessuna scheda corrisponde al 90% a '{nome}'. Aperte: {simili or 'nessuna'}.")
    return candidati[0][1]


def attiva_scheda(nome):
    t = _trova_scheda(nome)
    _http(f"/json/activate/{t['id']}")
    return t


def chiudi_scheda(nome=None):
    t = _trova_scheda(nome) if nome else _scheda_attiva()
    _http(f"/json/close/{t['id']}")
    return t


def chiudi_tutte():
    lista = schede()
    for t in lista[1:]:
        _http(f"/json/close/{t['id']}")
    if lista:
        _cdp(lista[0], "Page.navigate", {"url": "about:blank"})
    return len(lista)


# ------------------------------- comandi CDP -------------------------------
def _cdp(scheda, metodo, parametri=None, timeout=20):
    import websocket  # pacchetto "websocket-client"

    ws = websocket.create_connection(scheda["webSocketDebuggerUrl"], timeout=timeout, suppress_origin=True)
    try:
        ws.send(json.dumps({"id": 1, "method": metodo, "params": parametri or {}}))
        while True:
            r = json.loads(ws.recv())
            if r.get("id") == 1:
                if "error" in r:
                    raise ErroreChrome(r["error"].get("message", "errore CDP"))
                return r.get("result", {})
    finally:
        ws.close()


def _js(codice, scheda=None):
    r = _cdp(scheda or _scheda_attiva(), "Runtime.evaluate",
             {"expression": codice, "returnByValue": True, "awaitPromise": True})
    if r.get("exceptionDetails"):
        raise ErroreChrome("Errore nella pagina: " + r["exceptionDetails"].get("text", ""))
    return r.get("result", {}).get("value")


def vai(url, nuova=False):
    if not url.startswith(("http://", "https://", "about:", "chrome:")):
        url = "https://" + url
    if nuova:
        return nuova_scheda(url)
    t = _scheda_attiva()
    _cdp(t, "Page.navigate", {"url": url})
    _http(f"/json/activate/{t['id']}")
    return t


def cerca(testo, motore="google", nuova=True):
    q = urllib.parse.quote_plus(testo)
    url = (f"https://www.youtube.com/results?search_query={q}" if motore == "youtube"
           else f"https://www.google.com/search?q={q}")
    return vai(url, nuova=nuova)


def indietro():
    _js("history.back()")


def avanti():
    _js("history.forward()")


def ricarica():
    _cdp(_scheda_attiva(), "Page.reload")


def scorri(direzione="giu"):
    passo = {"giu": "innerHeight*0.8", "su": "-innerHeight*0.8", "inizio": "-1e9", "fine": "1e9"}[direzione]
    _js(f"window.scrollBy({{top: {passo}, behavior: 'smooth'}})")


def leggi_pagina(massimo=4000):
    t = _scheda_attiva()
    testo = _js("document.body ? document.body.innerText : ''", t) or ""
    testo = "\n".join(r.strip() for r in testo.splitlines() if r.strip())
    return {"titolo": t.get("title", ""), "url": t.get("url", ""), "testo": testo[:massimo]}


_JS_TROVA = r"""
(() => {
  const cercato = %s.toLowerCase().trim();
  const sel = 'a, button, input[type=submit], input[type=button], [role=button], [role=link], summary, label, [onclick]';
  const visibili = [...document.querySelectorAll(sel)].filter(e => {
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  });
  const testo = e => (e.innerText || e.value || e.getAttribute('aria-label') || e.title || '').replace(/\s+/g, ' ').trim();
  const sim = (a, b) => { // somiglianza semplice (Dice su bigrammi)
    if (a === b) return 1; if (a.length < 2 || b.length < 2) return 0;
    const bg = s => { const m = new Map(); for (let i = 0; i < s.length - 1; i++) { const k = s.slice(i, i + 2); m.set(k, (m.get(k) || 0) + 1); } return m; };
    const A = bg(a), B = bg(b); let c = 0;
    for (const [k, v] of A) c += Math.min(v, B.get(k) || 0);
    return 2 * c / (a.length + b.length - 2);
  };
  const punteggi = visibili.map(e => {
    const t = testo(e).toLowerCase();
    const p = t === cercato ? 1 : (t.startsWith(cercato) || (t.includes(cercato) && cercato.length >= 4) ? 0.95 : sim(t.slice(0, 80), cercato));
    return { e, t, p };
  }).filter(x => x.t).sort((a, b) => b.p - a.p);
  const migliore = punteggi[0];
  if (!migliore || migliore.p < %s) return { ok: false, simili: punteggi.slice(0, 4).map(x => x.t.slice(0, 40)) };
  migliore.e.scrollIntoView({ block: 'center' });
  const r = migliore.e.getBoundingClientRect();
  return { ok: true, testo: migliore.t.slice(0, 60), x: r.left + r.width / 2, y: r.top + r.height / 2 };
})()
"""


def clicca(testo):
    t = _scheda_attiva()
    r = _js(_JS_TROVA % (json.dumps(testo), SOGLIA), t)
    if not r or not r.get("ok"):
        simili = ", ".join((r or {}).get("simili", [])) or "nessuno"
        raise ErroreChrome(f"Nessun pulsante o link corrisponde al 90% a '{testo}'. Simili: {simili}.")
    for tipo in ("mousePressed", "mouseReleased"):
        _cdp(t, "Input.dispatchMouseEvent", {"type": tipo, "x": r["x"], "y": r["y"], "button": "left", "clickCount": 1})
    return r["testo"]


def digita(testo, invio=False):
    t = _scheda_attiva()
    # se nessun campo e' selezionato, usa il primo campo di testo visibile
    _js("""(() => { const a = document.activeElement;
      const ok = a && (a.isContentEditable || ['INPUT','TEXTAREA'].includes(a.tagName));
      if (!ok) { const c = [...document.querySelectorAll('input[type=text],input[type=search],input:not([type]),textarea,[contenteditable=true]')]
        .find(e => e.getBoundingClientRect().width > 0); if (c) c.focus(); } })()""", t)
    _cdp(t, "Input.insertText", {"text": testo})
    if invio:
        premi_invio(t)


def premi_invio(scheda=None):
    t = scheda or _scheda_attiva()
    for tipo in ("keyDown", "keyUp"):
        _cdp(t, "Input.dispatchKeyEvent", {"type": tipo, "key": "Enter", "code": "Enter",
                                           "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13,
                                           **({"text": "\r"} if tipo == "keyDown" else {})})


def video(azione):
    codice = {"pausa": "v.pause()", "riproduci": "v.play()", "muto": "v.muted = !v.muted",
              "schermo intero": "v.requestFullscreen()"}[azione]
    r = _js(f"(() => {{ const v = document.querySelector('video'); if (!v) return false; {codice}; return true; }})()")
    if not r:
        raise ErroreChrome("Nella pagina non c'è nessun video.")


def screenshot():
    t = _scheda_attiva()
    r = _cdp(t, "Page.captureScreenshot", {"format": "jpeg", "quality": 70})
    return "data:image/jpeg;base64," + r["data"]


# ------------------------------- ingresso unico -------------------------------
def esegui(op, p):
    """Esegue un'operazione su Chrome. Restituisce testo (o dict con immagine)."""
    try:
        if op == "apri":
            return "Chrome di Jarvis aperto." if avvia() else "Chrome di Jarvis è già aperto."
        if op == "vai":
            vai(p["url"], nuova=p.get("nuova", False))
            return f"Aperto {p['url']}."
        if op == "cerca":
            cerca(p["testo"], p.get("motore", "google"))
            return f"Cerco '{p['testo']}' su {'YouTube' if p.get('motore') == 'youtube' else 'Google'}."
        if op == "schede":
            lista = schede()
            return f"{len(lista)} schede aperte: " + "; ".join(t.get("title", "")[:50] or t.get("url", "") for t in lista[:10]) + "."
        if op == "passa":
            return "Passato a: " + attiva_scheda(p["nome"]).get("title", "")
        if op == "chiudi":
            return "Chiusa: " + chiudi_scheda(p.get("nome")).get("title", "")
        if op == "chiudi_tutte":
            return f"Chiuse {chiudi_tutte()} schede."
        if op == "indietro":
            indietro(); return "Indietro."
        if op == "avanti":
            avanti(); return "Avanti."
        if op == "ricarica":
            ricarica(); return "Pagina ricaricata."
        if op == "scorri":
            scorri(p.get("direzione", "giu")); return "Fatto."
        if op == "leggi":
            pag = leggi_pagina()
            return f"{pag['titolo']}. {pag['testo']}"
        if op == "clicca":
            return f"Cliccato: {clicca(p['testo'])}."
        if op == "digita":
            digita(p["testo"], p.get("invio", False)); return "Scritto."
        if op == "invio":
            premi_invio(); return "Invio."
        if op == "video":
            video(p["azione"]); return "Fatto."
        if op == "screenshot":
            return {"testo": "Schermata di Chrome.", "immagine": screenshot()}
        return f"Operazione Chrome sconosciuta: {op}"
    except ErroreChrome as e:
        return {"testo": str(e), "esito": "incerto"}
    except OSError as e:
        return {"testo": f"Chrome non raggiungibile: {e}", "esito": "errore"}

