"""
Jarvis - Interprete dei comandi in italiano (scritti o detti a voce).

Ogni comando riconosciuto con regole precise. Se Jarvis non e' sicuro almeno
al 90% (es. nome di una chat simile ma non uguale), NON agisce e lo dice.
Insulta solo se l'errore e' dell'utente.
"""

import difflib
import re
import unicodedata
from datetime import datetime

import config
import extra
import memoria
from personalita import SOGLIA_CERTEZZA, errore_utente, incerto, saggio


def normalizza(t):
    t = unicodedata.normalize("NFKD", (t or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t.replace("’", "'")).strip(" .!?")


def risposta(testo, esito="ok", **extra):
    return {"testo": testo, "esito": esito, **extra}


AIUTO = (
    "Comandi: 'apri chrome e cerca ...', 'cerca su youtube ...', 'apri steam e scarica ...', "
    "'apri <programma>', 'screenshot msi', 'blocca msi', 'spegni msi', 'leggi messaggi', "
    "'scrivi a <nome>: <testo>', 'leggi la posta', 'pulisci la posta', 'spazio account', "
    "'agenda', 'aggiungi al calendario: ...', 'cerca su drive ...', 'leggi teams', 'meteo', "
    "'che ore sono', 'meccanica: <domanda>', 'rapporto', 'ricordami tra 20 minuti di ...', "
    "'ricordami alle 18 di ...', 'promemoria', 'annota ...', 'leggi le note', 'accendi msi', "
    "'non disturbare per 2 ore', 'fine non disturbare', 'riepilogo', e le tue macro (config.py). "
    "Memoria: 'ricorda che ...', 'cosa sai di ...', 'dimentica ...', 'quando dico ... intendi ...', "
    "'cosa hai imparato'. Le domande (che finiscono con ?) vengono cercate in manuali, documenti e memoria."
)


PAROLE_DOMANDA = r"^(come|cosa|che cos|quale|qual|quali|quanto|quanti|quanta|quante|chi|dove|quando|perche|spiegami|dimmi)\b"


class Interprete:
    def __init__(self, servizi):
        # servizi: dizionario di funzioni fornite dal server (vedi server.py)
        self.s = servizi

    # ------------------------------------------------------------------
    def esegui(self, frase, _profondita=0):
        originale = (frase or "").strip()
        t = normalizza(originale)
        t = re.sub(r"^(ehi |ok |hey )?jarvis[,:]? ?", "", t)
        # Testo originale (maiuscole e accenti intatti) per i parametri liberi, es. il messaggio.
        orig = re.sub(r"\s+", " ", originale).strip()
        orig = re.sub(r"^(ehi |ok |hey )?jarvis[,:]? ?", "", orig, flags=re.IGNORECASE)
        if not t:
            return risposta(errore_utente("Non hai detto niente."), "errore_utente")

        if _profondita > 5:
            return risposta("Comandi insegnati che si richiamano in cerchio: controlla la sezione Memoria.", "errore")

        # Comandi che mi hai insegnato ("quando dico X intendi Y")
        insegnato = memoria.comando_per(t)
        if insegnato:
            return self.esegui(insegnato, _profondita + 1)

        # Macro personali definite in config.py (es. "modalita gioco")
        macro = {normalizza(k): v for k, v in getattr(config, "MACRO", {}).items()}
        if t in macro:
            esiti = [self.esegui(c, _profondita + 1) for c in macro[t]]
            return risposta(" ".join(e["testo"] for e in esiti),
                            "ok" if all(e["esito"] == "ok" for e in esiti) else "errore")

        for schema, azione in self._regole():
            m = re.match(schema, orig, re.IGNORECASE) or re.match(schema, t)
            if m:
                try:
                    return azione(m)
                except Exception as e:  # errore del sistema, NON dell'utente: niente insulti
                    return risposta(f"Errore del sistema: {e}", "errore")

        # Nessun comando: se e' una domanda, cerco nelle mie fonti (manuali, documenti, memoria).
        if originale.rstrip().endswith("?") or re.match(PAROLE_DOMANDA, t):
            testo, brani = self.s["chiedi"](t, solo=self._fonte(t))
            if brani:
                return risposta(testo, "ok", fonti=[{"manuale": b["manuale"], "sezione": b["sezione"]} for b in brani])
            memoria.registra_non_capito(orig)
            return risposta(testo + " Insegnamelo con 'ricorda che ...' o caricando un documento nella sezione Memoria.", "incerto")
        memoria.registra_non_capito(orig)
        return risposta("Comando non riconosciuto. Insegnamelo: 'quando dico ... intendi ...', "
                        "oppure scrivi 'aiuto'.", "sconosciuto")

    def riconosce(self, frase):
        """True se la frase corrisponde a un comando conosciuto (senza eseguirlo)."""
        t = re.sub(r"^(ehi |ok |hey )?jarvis[,:]? ?", "", normalizza(frase))
        if memoria.comando_per(t) or t in {normalizza(k) for k in getattr(config, "MACRO", {})}:
            return True
        return any(re.match(schema, frase.strip(), re.IGNORECASE) or re.match(schema, t)
                   for schema, _ in self._regole())

    def _regole(self):
        return [
            (r"^(aiuto|cosa sai fare|comandi)$", lambda m: risposta(AIUTO)),
            (r"^(che ore sono|che ora e|ora)$", self.ora),
            (r"^(meteo|che tempo fa( oggi)?)$", self.meteo),
            (r"^(apri|avvia|cerca|scrivi a|scarica)$", lambda m: risposta(errore_utente("Comando incompleto: manca cosa."), "errore_utente")),
            (r"^rapporto( completo)?$", lambda m: risposta("Rapporto in corso.", azione_pannello="rapporto")),
            # --- PC Msi ---
            (r"^(apri|avvia) (google )?chrome e cerca ?(?P<q>.*)$", lambda m: self.msi_cerca("google", m["q"])),
            (r"^(apri youtube e cerca|cerca su youtube|cerca in youtube) ?(?P<q>.*)$", lambda m: self.msi_cerca("youtube", m["q"])),
            (r"^cerca (?P<q>.+) su youtube$", lambda m: self.msi_cerca("youtube", m["q"])),
            (r"^(apri|avvia) steam e (scarica|installa) ?(il gioco )?(?P<g>.*)$", lambda m: self.msi_steam(m["g"])),
            (r"^(scarica|installa) (?P<g>.+) su steam$", lambda m: self.msi_steam(m["g"])),
            (r"^(fai uno )?screenshot( (di |del )?(msi|pc))?$", lambda m: self.msi("screenshot", {})),
            (r"^blocca (il )?(pc|msi|computer)$", lambda m: self.msi("blocca", {})),
            (r"^spegni (il )?(pc|msi|computer)$", lambda m: self.msi("spegni", {})),
            (r"^riavvia (il )?(pc|msi|computer)$", lambda m: self.msi("riavvia", {})),
            (r"^annulla (lo )?spegnimento$", lambda m: self.msi("annulla_spegnimento", {})),
            (r"^(apri|vai su) (il sito )?(?P<u>[a-z0-9.-]+\.[a-z]{2,}(/\S*)?)$", lambda m: self.msi("apri_url", {"url": "https://" + m["u"]})),
            (r"^(esegui|lancia) (il )?comando:? (?P<c>.+)$", lambda m: self.msi("comando", {"comando": m["c"]})),
            # --- Google ---
            (r"^cerca (su|in) drive ?(?P<q>.*)$", self.drive),
            (r"^(leggi|controlla) (la )?(posta|email|mail|gmail)$", self.posta),
            (r"^(pulisci|analizza|controlla) (la )?(posta|gmail|spam|casella)$", self.pulizia),
            (r"^(spazio|quanto spazio)( (account|google|gmail|drive|ho))*$", self.spazio),
            (r"^(agenda|calendario|impegni)( (di )?oggi)?$", self.agenda),
            (r"^(aggiungi (al calendario|un evento|evento)|crea (un )?evento):? ?(?P<t>.*)$", self.evento),
            # --- WhatsApp ---
            (r"^(leggi|controlla) (i )?(messaggi|whatsapp)( whatsapp)?$", self.wa_leggi),
            (r"^(scrivi|manda un messaggio|invia un messaggio) a (?P<n>[^:,]+)[:,] ?(?P<t>.*)$", self.wa_scrivi),
            # --- Teams ---
            (r"^(leggi |controlla )?(teams|messaggi (dei|dei miei) prof(essori)?)$", self.teams),
            # --- Promemoria, note, modalita' ---
            (r"^(ricordami|promemoria|ricorda(mi)? di) (?P<q>(tra|fra|alle|domani) .*)$", self.ricorda),
            (r"^(quali |leggi i |i miei )?promemoria$", self.lista_promemoria),
            (r"^ricordami$", lambda m: risposta(errore_utente("Ricordarti cosa e quando? Es. 'ricordami tra 20 minuti di studiare'."), "errore_utente")),
            (r"^(cancella|elimina) (tutti )?(i )?promemoria$", lambda m: (extra.cancella_promemoria(), risposta("Promemoria cancellati."))[1]),
            (r"^(annota|prendi nota|nota|scrivi una nota)[:,]? ?(?P<t>.*)$", self.annota),
            (r"^(leggi |mostra )?(le )?(mie )?note$", self.leggi_note),
            (r"^(cancella|elimina) (tutte )?(le )?note$", lambda m: (extra.cancella_note(), risposta("Note cancellate."))[1]),
            (r"^accendi (il )?(pc|msi|computer)$", lambda m: self.s["accendi_msi"]()),
            (r"^(non disturbare|modalita non disturbare)( per (?P<n>\S+) (?P<u>or[ae]|minuti))?$", self.non_disturbare),
            (r"^(fine|basta|disattiva) (non disturbare|modalita non disturbare)$", lambda m: self.s["fine_non_disturbare"]()),
            (r"^(riepilogo|briefing)( (di oggi|giornaliero))?$", lambda m: risposta(self.s["riepilogo"]())),
            # --- Memoria: cose che mi insegni ---
            (r"^quando (dico|scrivo) (?P<a>.+?),? (intendi|fai|significa|vuol dire|esegui) (?P<b>.+)$", self.insegna_comando),
            (r"^(dimentica|cancella) il comando (?P<a>.+)$", self.dimentica_comando),
            (r"^(ricorda|impara|sappi|memorizza|tieni a mente)( che)?[:,]? (?P<f>(?!di ).+)$", self.impara),
            (r"^ricorda(mi)? di (?P<t>.+)$", lambda m: (extra.aggiungi_nota(m["t"].strip()), risposta(
                f"Annotato: {m['t'].strip()}. Per un promemoria a tempo: 'ricordami tra 20 minuti di ...'."))[1]),
            (r"^(dimentica|cancella dalla memoria)( che)? (?P<f>.+)$", self.dimentica),
            (r"^cosa (hai imparato|ricordi|sai di me)$", self.cosa_hai_imparato),
            (r"^(cosa sai|cosa ricordi|dimmi cosa sai)( (di|su|del|della|dello|dei|delle|sul|sulla|sugli|sulle|riguardo a?))? (?P<q>.+)$", lambda m: self.chiedi(m["q"])),
            (r"^(domanda|chiedi|cerca nei documenti)[:,]? (?P<q>.+)$", lambda m: self.chiedi(m["q"])),
            # --- Meccanica ---
            (r"^meccanica[:,]? ?(?P<q>.*)$", self.meccanica),
            # --- apri programma (va per ultimo tra le regole "apri") ---
            (r"^(apri|avvia) (?P<a>.+?)( su (msi|pc))?$", lambda m: self.msi_app(m["a"])),
        ]

    # ------------------------------ generali ------------------------------
    def ora(self, _m):
        n = datetime.now()
        return risposta(saggio(f"Sono le {n:%H:%M}.", f"Le {n:%H:%M}, sono."))

    def meteo(self, _m):
        d = self.s["meteo"]()
        return risposta(f"{d['citta']}: {d['descrizione']}, {d['temperatura']}°C, "
                        f"min {d['minima']}°C, max {d['massima']}°C.")

    # ------------------------------ PC Msi ------------------------------
    def msi(self, azione, parametri):
        return self.s["msi"](azione, parametri)

    def msi_cerca(self, motore, q):
        if not q.strip():
            return risposta(errore_utente("Cerca cosa? Non hai detto cosa cercare."), "errore_utente")
        return self.msi("cerca", {"motore": motore, "testo": q.strip()})

    def msi_steam(self, gioco):
        if not gioco.strip():
            return risposta(errore_utente("Quale gioco? Non l'hai detto."), "errore_utente")
        return self.msi("steam_scarica", {"gioco": gioco.strip()})

    def msi_app(self, nome):
        nome = nome.strip()
        if nome in ("", "il", "la", "lo"):
            return risposta(errore_utente("Apri cosa?"), "errore_utente")
        return self.msi("apri_app", {"nome": nome})

    # ------------------------------ Google ------------------------------
    def posta(self, _m):
        lista = self.s["gmail_lista"]("is:unread")
        if not lista:
            return risposta("Nessuna email non letta.")
        oggetti = "; ".join(f"{e['mittente'].split('<')[0].strip()}: {e['oggetto']}" for e in lista[:5])
        return risposta(f"{len(lista)} email non lette. {oggetti}.")

    def pulizia(self, _m):
        r = self.s["gmail_analizza"]()
        sicure = [x for x in r if x["sicura"]]
        dubbie = len(r) - len(sicure)
        return risposta(
            f"Analisi completata: {len(sicure)} email di spam o pubblicità sopra la soglia del 90%, "
            f"{dubbie} dubbie che non tocco. Conferma l'azione nella sezione Gmail del pannello.",
            azione_pannello="pulizia")

    def spazio(self, _m):
        q = self.s["spazio"]()
        gb = lambda b: f"{b / 1073741824:.1f} GB"
        usato, limite = q.get("usage", 0), q.get("limit")
        testo = f"Spazio usato: {gb(usato)}"
        if limite:
            testo += f" su {gb(limite)} ({usato * 100 / limite:.0f}%)"
        if "usageInGmail" in q:
            testo += f". Gmail: {gb(q['usageInGmail'])}, Drive: {gb(q.get('usageInDrive', 0))}"
        return risposta(testo + ".")

    def agenda(self, _m):
        ev = self.s["eventi_oggi"]()
        if not ev:
            return risposta("Nessun impegno oggi.")
        parti = []
        for e in ev:
            ora = e["inizio"][11:16] if "T" in (e["inizio"] or "") else "tutto il giorno"
            parti.append(f"{ora} {e['titolo']}")
        return risposta(f"Oggi: {'; '.join(parti)}.")

    def evento(self, m):
        if not m["t"].strip():
            return risposta(errore_utente("Quale evento? Esempio: 'aggiungi al calendario: dentista domani alle 15'."), "errore_utente")
        e = self.s["evento"](m["t"].strip())
        return risposta(f"Evento creato: {e['titolo']}, {e['inizio']}. Controlla data e ora: le interpreta Google.")

    def drive(self, m):
        q = m["q"].strip()
        if not q:
            return risposta(errore_utente("Cerca cosa su Drive?"), "errore_utente")
        f = self.s["drive_cerca"](q)
        if not f:
            return risposta(f"Nessun file su Drive contiene '{q}' nel nome.")
        return risposta(f"{len(f)} file trovati: " + "; ".join(x["name"] for x in f[:5]) + ".", file=f)

    # ------------------------------ WhatsApp ------------------------------
    def wa_leggi(self, _m):
        chat = [c for c in self.s["wa"]("chat") if c["non_letti"] > 0]
        if not chat:
            return risposta("Nessun messaggio WhatsApp non letto.")
        return risposta("Non letti: " + "; ".join(f"{c['nome']} {c['non_letti']}" for c in chat[:8]) + ".",
                        azione_pannello="rapporto")

    def wa_scrivi(self, m):
        nome, testo = normalizza(m["n"]), m["t"].strip()
        if not testo:
            return risposta(errore_utente(f"Cosa devo scrivere a {nome}? Il messaggio è vuoto."), "errore_utente")
        chat = self.s["wa"]("chat?n=300")
        punteggi = sorted(((difflib.SequenceMatcher(None, nome, normalizza(c["nome"])).ratio(), c) for c in chat),
                          key=lambda x: -x[0])
        if not punteggi or punteggi[0][0] < 0.5:
            return risposta(errore_utente(f"Nessuna chat si chiama '{nome}'."), "errore_utente")
        migliore, c = punteggi[0]
        secondo = punteggi[1][0] if len(punteggi) > 1 else 0
        if migliore < SOGLIA_CERTEZZA or secondo > migliore - 0.05:
            nomi = ", ".join(x[1]["nome"] for x in punteggi[:3])
            return risposta(incerto(f"Non sono sicuro al 90% del destinatario. Simili: {nomi}. Usa il nome esatto."), "incerto")
        self.s["wa"]("invia", {"chat": c["id"], "testo": testo})
        return risposta(f"Inviato a {c['nome']}.")

    # ------------------------------ Teams ------------------------------
    def teams(self, _m):
        r = self.s["teams"]()
        msgs = r["messaggi"]
        testo = "Nessun nuovo messaggio dei professori su Teams." if not msgs else (
            f"{len(msgs)} nuovi messaggi su Teams. " + " ".join(f"{x['da']}, {x['dove']}: {x['testo'][:300]}." for x in msgs[:6]))
        if r.get("avvisi"):
            testo += " " + " ".join(r["avvisi"])
        return risposta(testo, messaggi_teams=msgs)

    # ------------------------------ Meccanica ------------------------------
    def meccanica(self, m):
        q = m["q"].strip()
        if not q:
            return risposta(errore_utente("Quale domanda di meccanica?"), "errore_utente")
        testo, brani = self.s["meccanica"](q)
        esito = "ok" if brani else "incerto"
        return risposta(testo, esito, fonti=[{"manuale": b["manuale"], "sezione": b["sezione"]} for b in brani])

    # ------------------------------ Promemoria / note ------------------------------
    def ricorda(self, m):
        quando, cosa = extra.interpreta_quando(m["q"])
        if quando is None:
            return risposta(errore_utente("Orario non valido. Es. 'tra 20 minuti', 'alle 18:30', 'domani alle 8'."), "errore_utente")
        if not cosa:
            return risposta(errore_utente("Ricordarti cosa? Non l'hai detto."), "errore_utente")
        extra.aggiungi_promemoria(quando, cosa)
        giorno = "oggi" if quando.date() == datetime.now().date() else "domani" if (quando.date() - datetime.now().date()).days == 1 else quando.strftime("%d/%m")
        return risposta(f"Promemoria: {giorno} alle {quando:%H:%M}, {cosa}.")

    def lista_promemoria(self, _m):
        lista = extra.promemoria()
        if not lista:
            return risposta("Nessun promemoria.")
        return risposta("; ".join(f"{datetime.fromisoformat(p['quando']):%d/%m %H:%M} {p['testo']}" for p in lista) + ".")

    def annota(self, m):
        testo = m["t"].strip()
        if not testo:
            return risposta(errore_utente("Annotare cosa? Nota vuota."), "errore_utente")
        n = extra.aggiungi_nota(testo)
        return risposta(f"Annotato. Note salvate: {n}.")

    def leggi_note(self, _m):
        n = extra.note()
        if not n:
            return risposta("Nessuna nota.")
        return risposta(" ".join(f"{i}. {x['testo']}." for i, x in enumerate(n, 1)))

    def non_disturbare(self, m):
        ore = 1.0
        if m["n"]:
            n = extra._numero(m["n"])
            if n is None or n <= 0:
                return risposta(errore_utente("Durata non valida. Es. 'non disturbare per 2 ore'."), "errore_utente")
            ore = n if m["u"].startswith("or") else n / 60
        return self.s["non_disturbare"](ore)

    # ------------------------------ Memoria ------------------------------
    def impara(self, m):
        fatto = m["f"].strip()
        if len(fatto.split()) < 2:
            return risposta(errore_utente("Ricordare cosa? Scrivi un fatto intero, es. 'ricorda che la mia moto è una Honda'."), "errore_utente")
        f = memoria.aggiungi_fatto(fatto[0].upper() + fatto[1:])
        if f is None:
            return risposta("Lo sapevo già.")
        self.s["ricarica"]()
        return risposta(f"Memorizzato: {f['testo']}")

    def dimentica(self, m):
        n = memoria.dimentica(m["f"])
        if not n:
            return risposta(errore_utente(f"Non ho nessun fatto che contenga '{m['f'].strip()}'."), "errore_utente")
        self.s["ricarica"]()
        return risposta(f"Dimenticati {n} fatti.")

    def insegna_comando(self, m):
        frase, comando = m["a"].strip(" '\""), m["b"].strip(" '\"")
        if not frase or not comando:
            return risposta(errore_utente("Formato: 'quando dico <frase> intendi <comando>'."), "errore_utente")
        if normalizza(frase) == normalizza(comando):
            return risposta(errore_utente("Frase e comando sono uguali. Geniale."), "errore_utente")
        if not self.riconosce(comando):
            return risposta(errore_utente(f"Il comando '{comando}' non lo conosco. Insegnami solo comandi che esistono (scrivi 'aiuto')."), "errore_utente")
        memoria.aggiungi_alias(frase, comando)
        return risposta(f"Imparato: quando dici '{frase}' eseguo '{comando}'.")

    def dimentica_comando(self, m):
        n = memoria.elimina_alias(m["a"].strip(" '\""))
        if not n:
            return risposta(errore_utente(f"Non conosco nessun comando '{m['a'].strip()}'."), "errore_utente")
        return risposta("Comando dimenticato.")

    def cosa_hai_imparato(self, _m):
        f, a, d = memoria.fatti(), memoria.alias(), memoria.documenti()
        testo = f"Ho imparato {len(f)} fatti, {len(a)} comandi e {len(d)} documenti."
        if f:
            testo += " Ultimi fatti: " + " ".join(x["testo"].rstrip(".") + "." for x in f[-5:])
        return risposta(testo)

    @staticmethod
    def _fonte(t):
        """Domande personali ('la mia moto', 'il mio prof') solo dalla memoria, mai dai manuali."""
        return "memoria" if re.search(r"\b(mio|mia|miei|mie|me|io|mi|ho|sono)\b", t) else None

    def chiedi(self, domanda):
        if not domanda.strip():
            return risposta(errore_utente("Quale domanda?"), "errore_utente")
        testo, brani = self.s["chiedi"](domanda, solo=self._fonte(normalizza(domanda)))
        return risposta(testo, "ok" if brani else "incerto",
                        fonti=[{"manuale": b["manuale"], "sezione": b["sezione"]} for b in brani])
