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
    "Per te: 'mi piace ...', 'non mi piace ...', 'novità per me', 'tienimi d'occhio ...', 'cerca offerte per ...', "
    "'come si costruisce ...', 'passo successivo', 'chi sono'. "
    "Casa: 'alexa accendi la luce', 'accendi la luce del salotto', 'metti jazz su amazon music', 'dispositivi'. "
    "Musica: 'metti ... su spotify', 'pausa spotify', 'prossima canzone', 'cosa sto ascoltando'. "
    "Discord: 'messaggi discord', 'scrivi su discord generale: ...'. Agenda: 'agenda', 'verifiche'. "
    "Compiti: 'controlla i compiti', 'compiti', 'mostra esercizio 1', 'manda esercizio 1', 'consigli 1'. "
    "Esercizi: 'risolvi x^2-5x+6=0', 'deriva ...', 'integra ... da 0 a 3', 'converti 120 km/h in m/s', "
    "oppure il testo dell'esercizio con dati e unità (es. 'un'auto accelera a 2 m/s² per 10 s, che velocità raggiunge?'). "
    "GitHub: 'github', 'i miei repository', 'pull request', 'stato build <repo>', 'crea issue su <repo>: ...', "
    "'leggi il file <percorso> di <repo>', 'cerca su github ...'. "
    "Chrome: 'nuova scheda ...', 'schede', 'passa alla scheda ...', 'chiudi scheda', 'indietro', 'leggi la pagina', "
    "'clicca su ...', 'digita ...', 'premi invio', 'scorri giu', 'pausa', 'screenshot chrome', "
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

        # Esercizio scritto a parole con dati e unita' di misura (es. "un'auto accelera a 2 m/s²...")
        import esercizi

        if esercizi.RX_NUMERO_UNITA.search(esercizi._norm(orig)) and re.search(
                r"\?|calcola|determina|trova|quanto|quale|=\s*\?", orig.lower()):
            return self.esercizio(orig)

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
            (r"^(agenda|calendario|impegni|prossimi impegni|cosa ho in agenda|cosa devo fare)( (di )?oggi| della settimana)?$", self.agenda),
            (r"^(le )?(mie )?verifiche$|^(ho )?(delle )?verifiche( in arrivo)?$", lambda m: self.agenda_tipo("verifica")),
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
            # --- Alexa e casa (comandi come se parlassi ad Alexa) ---
            (r"^alexa[,:]? (?P<c>.+)$", lambda m: self.alexa(m["c"])),
            (r"^(dispositivi|i miei dispositivi)( alexa| di casa)?$", lambda m: self.alexa_dispositivi()),
            (r"^(annuncia|di|dì) (su|con) alexa[,:]? (?P<t>.+)$", lambda m: self.alexa_parla(m["t"])),
            (r"^(?P<c>(accendi|spegni|alza|abbassa|apri|chiudi|imposta|regola|attiva|disattiva) (la |il |lo |le |i |gli |l')?"
             r"(luc|lampad|prese?\b|presa|tv|televisor|condizionator|clima|riscaldament|termostat|tapparell|serrand|ventilator|"
             r"aspirapolver|robot|stufa|caldaia|cancello|allarme|camera|salotto|cucina|bagno).*)$", lambda m: self.alexa(m["c"])),
            (r"^(metti|riproduci|suona|fai partire) (?P<q>.+) su amazon music$", lambda m: self.alexa(f"riproduci {m['q']} su amazon music")),
            # --- Spotify ---
            (r"^(metti|riproduci|suona|fai partire) (?P<q>.+) su spotify$", lambda m: self.spotify_riproduci(m["q"])),
            (r"^(pausa|ferma|stop) spotify$|^metti in pausa spotify$|^ferma la musica$", lambda m: self.spotify("pausa")),
            (r"^riprendi spotify$|^(riprendi|fai ripartire) la musica$", lambda m: self.spotify("riprendi")),
            (r"^(prossima canzone|canzone successiva|prossimo brano|salta( canzone)?)$", lambda m: self.spotify("avanti")),
            (r"^(canzone precedente|brano precedente)$", lambda m: self.spotify("indietro")),
            (r"^volume spotify (a |al )?(?P<v>\d{1,3})( ?%| per cento)?$", lambda m: self.spotify("volume", m["v"])),
            (r"^(cosa sto ascoltando|che canzone e( questa)?|cosa suona spotify)$", lambda m: self.spotify_ascolto()),
            # --- Discord (bot) ---
            (r"^(leggi |controlla )?(i )?messaggi (di |su )?discord( (in |nel canale )?(?P<c>[\w-]+))?$", lambda m: self.discord_leggi(m["c"])),
            (r"^scrivi su discord( (in |nel canale )?(?P<c>[\w-]+))?[:,] ?(?P<t>.*)$", lambda m: self.discord_scrivi(m["c"], m["t"])),
            # --- Compiti dai professori (bozze: si inviano SOLO con "manda esercizio") ---
            (r"^(controlla|guarda|cerca) (i )?(compiti|esercizi)( nuovi)?$|^controlla teams e (la )?posta$|^ci sono (nuovi )?(esercizi|compiti)$",
             lambda m: self.compiti_scansiona()),
            (r"^(i )?(miei )?compiti$|^(gli )?esercizi da fare$|^(le )?bozze( degli esercizi)?$", lambda m: self.compiti_elenco()),
            (r"^mostra(mi)? (l'|il )?(esercizio|compito|bozza)( (?P<n>\d{1,3}))?$", lambda m: self.compiti_mostra(m["n"])),
            (r"^manda (l'|il )?(esercizio|compito)( (?P<n>\d{1,3}))?$", lambda m: self.compiti_manda(m["n"])),
            (r"^(scarta|annulla|elimina) (l'|il )?(esercizio|compito|bozza) (?P<n>\d{1,3})$", lambda m: self.compiti_scarta(m["n"])),
            (r"^consigli( per)?( l')?( esercizio| compito)?( (?P<n>\d{1,3}))?$", lambda m: self.compiti_consigli(m["n"])),
            # --- Esercizi (matematica, fisica, meccanica, tecnologia) ---
            (r"^(esercizio|problema|risolvi l'esercizio)[:,]? (?P<q>.+)$", lambda m: self.esercizio(m["q"])),
            (r"^(?P<q>(risolvi|equazione|sistema|deriva|derivata|integra|integrale|limite|semplifica|scomponi|espandi|converti|calcola)\b.+)$", lambda m: self.esercizio(m["q"])),
            # --- Scrittura a mano ---
            (r"^(riconosci|leggi) (la )?(scrittura|calligrafia|quello che scrivo|il mio scritto)$|^scrittura a mano$",
             lambda m: risposta("Scrivi sulla lavagna della sezione Scrittura.", azione_pannello="scrittura")),
            # --- Foto e video ---
            (r"^(mostra(mi)?|fammi vedere|trova|apri) (la |il |le |i |una |un )?(foto|video|immagine|immagini)( (di|della|del|dello|delle|dei|degli|con|sul|sulla))? (?P<q>.+)$", self.mostra_media),
            (r"^(mostra(mi)?|apri) (le |i )?(mie )?(foto|video|galleria)$", lambda m: risposta("Galleria aperta.", azione_pannello="media")),
            # --- Gusti, scoperte, guide, ritratto ---
            (r"^(chi sono|ritratto|cosa sai di me|come sono|descrivimi|conoscimi|quanto mi conosci)$", lambda m: self.ritratto()),
            (r"^(non mi piace|non mi piacciono|odio|non mi interessa|non mi interessano) (?P<x>.+)$", lambda m: self.gusto(m["x"], False)),
            (r"^(mi piace|mi piacciono|adoro|amo|sono appassionat[oa] di|mi interessa|mi interessano|mi appassiona) (?P<x>.+)$", lambda m: self.gusto(m["x"], True)),
            (r"^(i miei gusti|cosa mi piace|i miei interessi)$", lambda m: self.miei_gusti()),
            (r"^(novita|notizie|scoperte|cosa c'e di (nuovo|interessante))( per me)?$|^(novita|notizie) che mi interessano$", lambda m: self.scoperte()),
            (r"^(smetti di seguire|non seguire piu) (?P<x>.+)$", lambda m: self.smetti(m["x"])),
            (r"^(tienimi d'occhio|avvisami se esce|avvisami (?:quando|se) (?:ci sono novita|esce|escono) (?:su|di)|segui) (?P<x>.+)$", lambda m: self.segui(m["x"])),
            (r"^(cosa segui|oggetti seguiti|cosa tieni d'occhio)$", lambda m: self.seguiti()),
            (r"^cerca offert[ae] (per|di|su) (?P<x>.+)$", lambda m: self.offerte(m["x"])),
            (r"^(come (si )?costruisc\w*|spiegami come (si )?(costruisce|costruire|fa|fare|realizza\w*)|guida (per|a)|"
             r"come (posso )?(costruire|realizzare)|come si fa(nno)?( a (costruire|fare))?) (?P<x>.+)$", lambda m: self.guida(m["x"])),
            (r"^(passo successivo|prossimo passo|fatto,? (il )?prossimo( passo)?|avanti con la guida)$", lambda m: self.passo("avanti")),
            (r"^(passo precedente|torna al passo (prima|precedente))$", lambda m: self.passo("indietro")),
            (r"^(ripeti( il passo)?|a che passo sono|ricominciamo la guida)$", lambda m: self.passo("inizio" if "ricomin" in m.group(0) else "resta")),
            (r"^(materiali|attrezzi|cosa mi serve)( per la guida)?$", lambda m: self.materiali()),
            (r"^(si|sì)[,]? (fallo|grazie|certo|vai)$|^fallo$|^si fallo$", lambda m: self.accetta_suggerimento()),
            (r"^(no grazie|non ora|lascia stare)$", lambda m: self.rifiuta_suggerimento()),
            # --- Memoria: cose che mi insegni ---
            (r"^quando (dico|scrivo) (?P<a>.+?),? (intendi|fai|significa|vuol dire|esegui) (?P<b>.+)$", self.insegna_comando),
            (r"^(dimentica|cancella) il comando (?P<a>.+)$", self.dimentica_comando),
            (r"^(ricorda|impara|sappi|memorizza|tieni a mente)( che)?[:,]? (?P<f>(?!di ).+)$", self.impara),
            (r"^ricorda(mi)? di (?P<t>.+)$", lambda m: (extra.aggiungi_nota(m["t"].strip()), risposta(
                f"Annotato: {m['t'].strip()}. Per un promemoria a tempo: 'ricordami tra 20 minuti di ...'."))[1]),
            (r"^(dimentica|cancella dalla memoria)( che)? (?P<f>.+)$", self.dimentica),
            (r"^cosa (hai imparato|ricordi)$", self.cosa_hai_imparato),
            (r"^(cosa sai|cosa ricordi|dimmi cosa sai)( (di|su|del|della|dello|dei|delle|sul|sulla|sugli|sulle|riguardo a?))? (?P<q>.+)$", lambda m: self.chiedi(m["q"])),
            (r"^(domanda|chiedi|cerca nei documenti)[:,]? (?P<q>.+)$", lambda m: self.chiedi(m["q"])),
            # --- Meccanica ---
            (r"^meccanica[:,]? ?(?P<q>.*)$", self.meccanica),
            # --- GitHub ---
            (r"^(github|notifiche (di )?github|controlla github|novita (su|di) github)$", lambda m: self.gh_notifiche()),
            (r"^segna (le )?notifiche (di )?github come lette$", lambda m: self.gh(lambda g: (g.segna_notifiche_lette(), "Notifiche GitHub segnate come lette.")[1])),
            (r"^(i )?(miei )?repository( github| su github)?$|^elenca i (miei )?repository$", lambda m: self.gh_repo()),
            (r"^(le )?(mie )?issue( aperte)?( su github)?$", lambda m: self.gh_elenco("issue")),
            (r"^(le )?(mie )?(pull request|pr)( aperte)?( su github)?$", lambda m: self.gh_elenco("pr")),
            (r"^stato (della |delle )?(build|ci|actions|test) (di |del |su |in )?(?P<r>\S+)$", self.gh_build),
            (r"^cerca su github (?P<q>.+)$", self.gh_cerca),
            (r"^(metti una )?stella (a|su) (?P<r>\S+)$", lambda m: self.gh(lambda g: (g.metti_stella(g.trova_repo(m["r"])), f"Stella aggiunta a {m['r']}.")[1])),
            (r"^crea (una )?issue (su|in|nel|per) (?P<r>[^:]+): ?(?P<t>.*)$", self.gh_crea_issue),
            (r"^commenta (la )?(issue|pr|pull request) (?P<n>\d+) (di|su|in|del) (?P<r>[^:]+): ?(?P<t>.*)$", self.gh_commenta),
            (r"^chiudi (la )?issue (?P<n>\d+) (di|su|in|del) (?P<r>\S+)$", lambda m: self.gh(lambda g: (g.chiudi_issue(g.trova_repo(m["r"]), m["n"]), f"Issue {m['n']} chiusa.")[1])),
            (r"^leggi (il )?file (?P<p>\S+) (di|su|in|del) (?P<r>\S+)$", self.gh_leggi_file),
            (r"^crea (un )?(nuovo )?repository (?P<v>privato |pubblico )?(?P<n>[\w.-]+)$", self.gh_crea_repo),
            (r"^unisci (la )?(pull request|pr) (?P<n>\d+) (di|su|in|del) (?P<r>\S+?)(?P<ok> confermo)?$", self.gh_unisci),
            # --- Chrome (controllo completo, sul PC Msi) ---
            (r"^(apri )?(una )?nuova scheda( (con|su))? ?(?P<u>.*)$", lambda m: self.chrome("vai", url=(m["u"].strip() or "www.google.com"), nuova=True)),
            (r"^(quali )?schede( aperte)?$|^che schede (ho|sono) apert[ei]$", lambda m: self.chrome("schede")),
            (r"^(passa|vai|torna) (alla|sulla|nella) scheda (?P<n>.+)$", lambda m: self.chrome("passa", nome=m["n"].strip())),
            (r"^chiudi tutte le schede$", lambda m: self.chrome("chiudi_tutte")),
            (r"^chiudi (la |questa )?scheda( (?P<n>.+))?$", lambda m: self.chrome("chiudi", nome=(m["n"] or "").strip() or None)),
            (r"^(torna )?indietro$|^pagina precedente$", lambda m: self.chrome("indietro")),
            (r"^(vai )?avanti$|^pagina successiva$", lambda m: self.chrome("avanti")),
            (r"^ricarica( la pagina)?$|^aggiorna la pagina$", lambda m: self.chrome("ricarica")),
            (r"^scorri (in )?giu$|^vai giu$", lambda m: self.chrome("scorri", direzione="giu")),
            (r"^scorri (in )?su$|^vai su$", lambda m: self.chrome("scorri", direzione="su")),
            (r"^vai (in fondo|alla fine)( della pagina)?$", lambda m: self.chrome("scorri", direzione="fine")),
            (r"^(vai |torna )?(all'inizio|in cima)( della pagina)?$", lambda m: self.chrome("scorri", direzione="inizio")),
            (r"^leggi (la pagina|la scheda|questa pagina|cosa c'e scritto)$", lambda m: self.chrome("leggi")),
            (r"^premi invio$", lambda m: self.chrome("invio")),
            (r"^(clicca|premi|cliccare|tocca)( su)? (?P<t>.+)$", self.chrome_clicca),
            (r"^(digita|scrivi nella pagina|scrivi qui|scrivi nel campo)[:,]? (?P<t>.+?)(?P<invio> e premi invio)?$", self.chrome_digita),
            (r"^(metti in )?pausa( il video)?$|^ferma il video$", lambda m: self.chrome("video", azione="pausa")),
            (r"^(riproduci|fai partire|play|riprendi)( il video)?$", lambda m: self.chrome("video", azione="riproduci")),
            (r"^(muto|togli l'audio|metti l'audio|togli il muto)$", lambda m: self.chrome("video", azione="muto")),
            (r"^(video )?a schermo intero$", lambda m: self.chrome("video", azione="schermo intero")),
            (r"^screenshot (di |del )?chrome$", lambda m: self.chrome("screenshot")),
            (r"^cerca su google (?P<q>.+)$", lambda m: self.msi_cerca("google", m["q"])),
            (r"^cerca (?P<q>.+) su google$", lambda m: self.msi_cerca("google", m["q"])),
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
        import agenda

        impegni, avvisi = agenda.prossimi(7)
        nuovi = {x["id"] for x in agenda.nuovi_da_riferire()}
        if not impegni:
            return risposta("Nessun impegno nei prossimi 7 giorni." + (" " + " ".join(avvisi) if avvisi else ""))
        ordinati = [x for x in impegni if x["id"] in nuovi] + [x for x in impegni if x["id"] not in nuovi]
        righe = [("NUOVO – " if x["id"] in nuovi else "") + agenda.frase(x) for x in ordinati[:12]]
        return risposta("Prossimi impegni: " + "; ".join(righe) + "." + (" " + " ".join(avvisi) if avvisi else ""))

    def agenda_tipo(self, tipo):
        import agenda

        impegni, avvisi = agenda.prossimi(30)
        scelti = [x for x in impegni if x.get("tipo") == tipo]
        if not scelti:
            return risposta(f"Nessuna {tipo} in agenda nei prossimi 30 giorni." + (" " + " ".join(avvisi) if avvisi else ""))
        return risposta(f"{tipo.capitalize()}: " + "; ".join(agenda.frase(x) for x in scelti) + ".")

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

    # ------------------------------ Foto e video ------------------------------
    def mostra_media(self, m):
        import media

        trovati = media.cerca(m["q"])
        if not trovati:
            return risposta(incerto(f"Nessuna foto o video con una descrizione che corrisponda al 90% a '{m['q'].strip()}'."), "incerto")
        return risposta(f"Trovati {len(trovati)}: " + "; ".join(x["descrizione"] for x in trovati[:5]) + ".",
                        azione_pannello="media", media=[x["id"] for x in trovati])

    # ------------------------------ Chrome ------------------------------
    def chrome(self, op, **parametri):
        return self.msi("chrome", {"op": op, **{k: v for k, v in parametri.items() if v is not None}})

    def chrome_clicca(self, m):
        testo = m["t"].strip(" '\"")
        if testo in ("invio", "enter"):
            return self.chrome("invio")
        return self.chrome("clicca", testo=testo)

    def chrome_digita(self, m):
        testo = m["t"].strip()
        if not testo:
            return risposta(errore_utente("Digitare cosa?"), "errore_utente")
        return self.chrome("digita", testo=testo, invio=bool(m["invio"]))

    # ------------------------------ GitHub ------------------------------
    def gh(self, funzione):
        import github_jarvis as g

        try:
            esito = funzione(g)
        except g.ErroreGitHub as e:
            return risposta(str(e), "errore")
        return esito if isinstance(esito, dict) else risposta(esito)

    def gh_notifiche(self):
        def f(g):
            n = [x for x in g.notifiche() if x["non_letta"]]
            if not n:
                return "Nessuna notifica GitHub non letta."
            return f"{len(n)} notifiche GitHub: " + "; ".join(f"{x['repo']}: {x['titolo']}" for x in n[:6]) + "."
        return self.gh(f)

    def gh_repo(self):
        return self.gh(lambda g: (lambda r: f"{len(r)} repository. Aggiornati di recente: "
                                  + ", ".join(x["nome"].split("/")[1] for x in r[:8]) + ".")(g.repository(30)))

    def gh_elenco(self, tipo):
        def f(g):
            lista = g.issue_aperte() if tipo == "issue" else g.pr_aperte()
            nome = "issue" if tipo == "issue" else "pull request"
            if not lista:
                return f"Nessuna {nome} aperta che ti riguarda."
            return f"{len(lista)} {nome} aperte: " + "; ".join(f"{x['repo']} #{x['numero']} {x['titolo']}" for x in lista[:6]) + "."
        return self.gh(f)

    def gh_build(self, m):
        def f(g):
            repo = g.trova_repo(m["r"])
            runs = g.stato_build(repo)
            if not runs:
                return f"{repo}: nessuna build (GitHub Actions) trovata."
            x = runs[0]
            esito = {"success": "riuscita", "failure": "FALLITA", "cancelled": "annullata"}.get(x["esito"], x["esito"] or x["stato"])
            return f"{repo}: ultima build '{x['nome']}' sul ramo {x['ramo']}: {esito}."
        return self.gh(f)

    def gh_cerca(self, m):
        return self.gh(lambda g: (lambda r: "Nessun risultato." if not r else "Su GitHub: " + "; ".join(
            f"{x['nome']} ({x['stelle']} stelle)" for x in r[:5]) + ".")(g.cerca_repository(m["q"])))

    def gh_crea_issue(self, m):
        titolo = m["t"].strip()
        if not titolo:
            return risposta(errore_utente("Manca il titolo dell'issue."), "errore_utente")

        def f(g):
            repo = g.trova_repo(m["r"])
            r = g.crea_issue(repo, titolo, "Creata da Jarvis.")
            return f"Issue #{r['numero']} creata su {repo}."
        return self.gh(f)

    def gh_commenta(self, m):
        testo = m["t"].strip()
        if not testo:
            return risposta(errore_utente("Commento vuoto. Cosa devo scrivere?"), "errore_utente")
        return self.gh(lambda g: (g.commenta(g.trova_repo(m["r"]), m["n"], testo), f"Commento aggiunto al numero {m['n']}.")[1])

    def gh_leggi_file(self, m):
        def f(g):
            r = g.leggi_file(g.trova_repo(m["r"]), m["p"])
            if r["cartella"]:
                return f"{m['p']} è una cartella: " + ", ".join(r["voci"][:30]) + "."
            return f"{m['p']} ({r['dimensione']} byte):\n{r['testo'][:3000]}"
        return self.gh(f)

    def gh_crea_repo(self, m):
        privato = (m["v"] or "privato ").strip() != "pubblico"
        return self.gh(lambda g: (lambda r: f"Repository {r['nome']} creato ({'privato' if privato else 'pubblico'}).")(
            g.crea_repository(m["n"], privato)))

    def gh_unisci(self, m):
        if not m["ok"]:
            return risposta(f"Unire la pull request {m['n']} di {m['r']} non si annulla facilmente. "
                            f"Ripeti aggiungendo 'confermo': 'unisci la pr {m['n']} di {m['r']} confermo'.", "incerto")

        def f(g):
            r = g.unisci_pr(g.trova_repo(m["r"]), m["n"])
            return f"Pull request {m['n']} unita." if r["unita"] else f"Non unita: {r['messaggio']}"
        return self.gh(f)

    # ------------------------------ Esercizi ------------------------------
    def esercizio(self, testo):
        import esercizi

        try:
            r = esercizi.risolvi_esercizio(testo.strip())
        except esercizi.ErroreEsercizio as e:
            return risposta(incerto(str(e)), "incerto")
        except Exception as e:  # espressione impossibile da calcolare
            return risposta(f"Calcolo non riuscito: {e}", "errore")
        passi = "\n".join(f"{i}. {p}" for i, p in enumerate(r["passi"], 1))
        return risposta(f"Risultato: {r['risultato']}" + (f"\n\nPassaggi:\n{passi}" if passi else ""), "ok",
                        esercizio=r)

    # ------------------------------ Compiti ------------------------------
    def _bozza(self, n):
        import compiti

        lista = compiti.bozze()
        if not lista:
            return None, risposta("Nessun esercizio in attesa.")
        if n is None:
            if len(lista) > 1:
                return None, risposta(f"Ci sono {len(lista)} bozze: dimmi quale, es. 'mostra esercizio 1'. "
                                      + "; ".join(f"{i}) {b['da']} – {b['titolo']}" for i, b in enumerate(lista, 1)), "incerto")
            return lista[0], None
        b = compiti.trova(int(n))
        if not b:
            return None, risposta(errore_utente(f"Non c'è nessuna bozza numero {n}. Ce ne sono {len(lista)}."), "errore_utente")
        return b, None

    def compiti_scansiona(self):
        import compiti

        nuove, avvisi = compiti.scansiona()
        testo = (f"Trovate {len(nuove)} nuove richieste di esercizi." if nuove else "Nessuna nuova richiesta di esercizi.")
        tot = len(compiti.bozze())
        if tot:
            testo += f" Bozze da rivedere: {tot}. Di' 'mostra esercizio 1'."
        if avvisi:
            testo += " " + " ".join(avvisi)
        return risposta(testo, azione_pannello="compiti" if tot else None)

    def compiti_elenco(self):
        import compiti

        lista = compiti.bozze()
        if not lista:
            return risposta("Nessun esercizio in attesa.")
        return risposta("Bozze: " + "; ".join(
            f"{i}) {b['da']} – {b['titolo']} ({'su foglio' if b['tipo'] == 'foglio' else 'da inviare'}"
            f"{', già vista' if b['mostrato'] else ''})" for i, b in enumerate(lista, 1)) + ".", azione_pannello="compiti")

    def compiti_mostra(self, n):
        import compiti

        b, errore = self._bozza(n)
        if errore:
            return errore
        compiti.segna_mostrata(b["id"])
        righe = [f"Da {b['da']} ({b['titolo']}). Tipo: {'esercizi su foglio' if b['tipo'] == 'foglio' else 'consegna digitale'}.",
                 "Cosa fare: " + " ".join(b["cosa_fare"])]
        if b["tipo"] == "foglio":
            for i, e in enumerate(b["esercizi"], 1):
                righe.append(f"Esercizio {i}: {e['testo']}\n  Consigli: " + " ".join(e["consigli"][:3])
                             + (f"\n  Risultato per controllo: {e['risultato']}" if e["risolto"] else ""))
        else:
            righe.append("Risposta pronta:\n" + b["risposta"])
        if b["fonte"] in ("teams_chat", "gmail", "posta_scuola"):
            righe.append("Per inviarla di' chiaramente: 'manda esercizio" + (f" {n}" if n else "") + "'.")
        return risposta("\n".join(righe), azione_pannello="compiti", bozza=b["id"])

    def compiti_manda(self, n):
        import compiti

        b, errore = self._bozza(n)
        if errore:
            return errore
        try:
            dove = compiti.invia(b["id"])
        except ValueError as e:
            return risposta(str(e), "incerto")
        except Exception as e:
            return risposta(f"Invio non riuscito: {e}", "errore")
        return risposta(f"Esercizio inviato: {dove}.")

    def compiti_scarta(self, n):
        import compiti

        b, errore = self._bozza(n)
        if errore:
            return errore
        compiti.scarta(b["id"])
        return risposta("Bozza scartata.")

    def compiti_consigli(self, n):
        b, errore = self._bozza(n)
        if errore:
            return errore
        righe = [f"Esercizio {i}: " + " ".join(e["consigli"]) for i, e in enumerate(b["esercizi"], 1)]
        return risposta("\n".join(righe) or "Nessun esercizio individuato nel messaggio.")

    # ------------------------------ Alexa ------------------------------
    def alexa(self, testo):
        testo = testo.strip()
        if not testo:
            return risposta(errore_utente("Cosa devo dire ad Alexa?"), "errore_utente")
        try:
            r = self.s["alexa"]("comando", {"testo": testo})
        except RuntimeError as e:
            return risposta(str(e), "errore")
        return risposta(f"Detto ad Alexa ({r.get('echo')}): \"{testo}\".")

    def alexa_parla(self, testo):
        try:
            r = self.s["alexa"]("parla", {"testo": testo})
        except RuntimeError as e:
            return risposta(str(e), "errore")
        return risposta(f"Annunciato su {r.get('echo')}.")

    def alexa_dispositivi(self):
        try:
            r = self.s["alexa"]("dispositivi")
        except RuntimeError as e:
            return risposta(str(e), "errore")
        testo = "Echo: " + (", ".join(d["nome"] for d in r["echo"]) or "nessuno") + "."
        if r.get("casa"):
            testo += " Dispositivi di casa: " + ", ".join(r["casa"][:30]) + "."
        return risposta(testo)

    # ------------------------------ Spotify ------------------------------
    def spotify(self, azione, valore=None):
        import spotify_jarvis as sp

        try:
            return risposta(sp.comando(azione, valore))
        except sp.ErroreSpotify as e:
            if str(e) == "PREMIUM":
                return risposta("Spotify permette di comandare la riproduzione solo con l'account Premium.", "errore")
            return risposta(str(e), "errore")

    def spotify_riproduci(self, testo):
        import spotify_jarvis as sp

        try:
            return risposta(sp.riproduci(testo))
        except sp.ErroreSpotify as e:
            if str(e) == "PREMIUM" or "non collegato" in str(e):
                # senza Premium (o senza collegamento): apro Spotify sul PC Msi con la ricerca
                import urllib.parse

                r = self.msi("apri_uri", {"uri": "spotify:search:" + urllib.parse.quote(testo)})
                if r.get("esito") == "ok":
                    return risposta("Senza Spotify Premium non posso avviare il brano: ho aperto la ricerca su Spotify nel PC Msi, premi play.")
            return risposta(str(e), "errore")

    def spotify_ascolto(self):
        import spotify_jarvis as sp

        try:
            b = sp.in_ascolto()
        except sp.ErroreSpotify as e:
            return risposta(str(e), "errore")
        if not b:
            return risposta("Su Spotify non sta suonando niente.")
        return risposta(f"{'Stai ascoltando' if b['in_riproduzione'] else 'In pausa'}: {b['titolo']} di {b['artisti']}.")

    # ------------------------------ Discord ------------------------------
    def discord_leggi(self, canale):
        import discord_jarvis as dj

        try:
            nome, msgs = dj.ultimi_messaggi(canale)
        except dj.ErroreDiscord as e:
            return risposta(str(e), "errore")
        if not msgs:
            return risposta(f"Nessun messaggio in #{nome}.")
        return risposta(f"#{nome}: " + " ".join(f"{m['autore']}: {m['testo'][:200]}." for m in msgs[-8:]))

    def discord_scrivi(self, canale, testo):
        import discord_jarvis as dj

        if not (testo or "").strip():
            return risposta(errore_utente("Cosa devo scrivere su Discord? Messaggio vuoto."), "errore_utente")
        try:
            nome = dj.scrivi(canale, testo.strip())
        except dj.ErroreDiscord as e:
            return risposta(str(e), "errore")
        return risposta(f"Scritto su Discord in #{nome}.")

    # ------------------------------ Gusti e ritratto ------------------------------
    def ritratto(self):
        import ritratto

        testo, _ = ritratto.ritratto()
        return risposta(testo, azione_pannello="perte")

    def gusto(self, cosa, piace):
        import gusti

        cosa = re.sub(r"^(il|lo|la|i|gli|le|l'|un|uno|una|un')\s*", "", cosa.strip(" .!"), flags=re.I)
        if not cosa:
            return risposta(errore_utente("Cosa? Non l'hai detto."), "errore_utente")
        if piace:
            gusti.mi_piace(cosa)
            return risposta(f"Segnato: ti piace {cosa}. Ti proporrò novità su questo.")
        gusti.non_mi_piace(cosa)
        return risposta(f"Segnato: {cosa} non ti interessa. Non te lo proporrò più.")

    def miei_gusti(self):
        import gusti

        p = gusti.profilo()
        if not p["interessi"] and not p["piace"]:
            return risposta("Dati insufficienti per verificare: non so ancora cosa ti piace. Dimmelo ('mi piace ...') o usami di più.")
        testo = "Ti interessano: " + ", ".join(i["termine"] for i in p["interessi"][:12]) + "."
        if p["non_piace"]:
            testo += " Non ti interessano: " + ", ".join(p["non_piace"][:8]) + "."
        return risposta(testo, azione_pannello="perte")

    def scoperte(self):
        import scoperte

        lista, avvisi = scoperte.per_te(8)
        if not lista:
            return risposta("Nessuna novità trovata per i tuoi interessi." + (" " + avvisi[0] if avvisi else ""))
        return risposta("Per te: " + " ".join(f"{x['titolo']} ({x['fonte']})." for x in lista[:5]), azione_pannello="perte")

    def segui(self, oggetto):
        import scoperte

        oggetto = oggetto.strip(" .!")
        if len(oggetto) < 2:
            return risposta(errore_utente("Seguire cosa?"), "errore_utente")
        scoperte.segui(oggetto)
        return risposta(f"Tengo d'occhio '{oggetto}': ti avviso quando escono notizie, uscite o recensioni.")

    def smetti(self, oggetto):
        import scoperte

        scoperte.smetti_di_seguire(oggetto)
        return risposta(f"Non seguo più '{oggetto.strip()}'.")

    def seguiti(self):
        import scoperte

        o = scoperte.oggetti()
        return risposta("Tengo d'occhio: " + ", ".join(x["nome"] for x in o) + "." if o else "Non sto seguendo nessun oggetto.")

    def offerte(self, oggetto):
        import gusti
        import scoperte

        link = scoperte.link_negozi(oggetto.strip())
        gusti.registra(oggetto, "oggetto", 2.0)
        r = self.msi("apri_url", {"url": link["Idealo"]}) if "msi" in self.s else {"esito": "errore"}
        aperto = " Ho aperto il confronto prezzi su Idealo nel PC Msi." if r.get("esito") == "ok" else ""
        return risposta(f"Non ho accesso diretto ai prezzi dei negozi.{aperto} Link: " +
                        " · ".join(f"{k}: {v}" for k, v in link.items()), link=link)

    # ------------------------------ Guide ------------------------------
    def guida(self, argomento):
        import gusti
        import guide

        try:
            g = guide.crea(argomento, self.s.get("esperto"))
        except guide.ErroreGuida as e:
            return risposta(str(e), "incerto")
        gusti.registra(argomento, "guida", 1.5)
        return risposta(guide.riassunto(g), azione_pannello="guida", guida=g["id"])

    def passo(self, direzione):
        import guide

        try:
            if direzione == "resta":
                g = guide.attuale()
                return risposta(guide.testo_passo(g), azione_pannello="guida", guida=g["id"])
            g, testo = guide.muovi(direzione)
        except guide.ErroreGuida as e:
            return risposta(str(e), "incerto")
        return risposta(testo, azione_pannello="guida", guida=g["id"])

    def materiali(self):
        import guide

        try:
            g = guide.attuale()
        except guide.ErroreGuida as e:
            return risposta(str(e), "incerto")
        return risposta("Materiali: " + (", ".join(g.get("materiali", [])) or "nessuno indicato") + ". Attrezzi: "
                        + (", ".join(g.get("attrezzi", [])) or "nessuno indicato") + ".")

    # ------------------------------ Suggerimenti dalle abitudini ------------------------------
    def accetta_suggerimento(self):
        import ritratto

        c = ritratto.ultimo_suggerimento()
        if not c:
            return risposta("Non ti avevo proposto niente.")
        r = self.esegui(c)
        return {**r, "testo": f"Eseguo \"{c}\": " + r["testo"]}

    def rifiuta_suggerimento(self):
        import ritratto

        c = ritratto.rifiuta_suggerimento()
        return risposta("Va bene." if c else "Non ti avevo proposto niente.")
