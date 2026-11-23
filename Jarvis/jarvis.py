"""
JARVIS - Assistente personale.
Funzioni attuali:
  - lettura della casella Gmail (sola lettura)
  - risposte di meccanica basate sul manuale nella cartella "manuali"
  - lettura dei messaggi raccolti dalla segreteria WhatsApp
Avvio: doppio clic su avvia_jarvis.bat
"""

import os
import sys
import textwrap

import config
import voce
import whatsapp_reader

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

LINEA = "-" * 70


def stampa(testo=""):
    for riga in str(testo).splitlines() or [""]:
        print(textwrap.fill(riga, 100) if riga.strip() else "")


def mostra_elenco(email):
    if not email:
        stampa("Jarvis: nessuna email trovata.")
        return
    print(LINEA)
    for n, e in enumerate(email, 1):
        nuova = "[NUOVA] " if e["non_letta"] else ""
        print(f"{n:>2}. {nuova}{e['oggetto']}")
        print(f"    Da:   {e['mittente']}")
        print(f"    Data: {e['data']}")
        print(f"    {e['anteprima'][:120]}")
    print(LINEA)


def sessione_email(query, solo_posta_in_arrivo=True):
    try:
        import gmail_reader
    except ImportError:
        stampa("Jarvis: librerie Google mancanti. Fai doppio clic su installa.bat e riprova.")
        return

    try:
        stampa("Jarvis: controllo la posta...")
        email = gmail_reader.elenca_email(
            query, config.EMAIL_DA_MOSTRARE, solo_posta_in_arrivo
        )
        mostra_elenco(email)
        while email:
            scelta = input("Numero dell'email da leggere (Invio per tornare al menu): ").strip()
            if not scelta:
                return
            if not scelta.isdigit() or not 1 <= int(scelta) <= len(email):
                stampa("Jarvis: numero non valido.")
                continue
            m = gmail_reader.leggi_email(email[int(scelta) - 1]["id"])
            print(LINEA)
            stampa(f"Da:      {m['mittente']}")
            stampa(f"A:       {m['destinatario']}")
            stampa(f"Data:    {m['data']}")
            stampa(f"Oggetto: {m['oggetto']}")
            print(LINEA)
            stampa(m["corpo"])
            print(LINEA)
            mostra_elenco(email)
    except gmail_reader.ErroreGmail as e:
        stampa("Jarvis: " + str(e))


def sessione_meccanica(esperto):
    stampa("Jarvis: modalita' meccanica. Fonte: " + ", ".join(esperto.manuali_caricati()))
    stampa("Scrivi la tua domanda (Invio vuoto per tornare al menu).")
    while True:
        domanda = input("\nDomanda di meccanica: ").strip()
        if not domanda:
            return
        stampa("Jarvis: consulto il manuale...")
        risposta, brani = esperto.rispondi(domanda)
        print(LINEA)
        stampa(risposta)
        if brani:
            print(LINEA)
            stampa("Fonti nel manuale:")
            for n, b in enumerate(brani, 1):
                stampa(f"  [{n}] {b['manuale']} - sezione \"{b['sezione']}\"")
        print(LINEA)


def riferisci_whatsapp(registrazioni, ad_alta_voce=True):
    if not registrazioni:
        stampa("Jarvis: nessun messaggio WhatsApp.")
        return
    vocali_totali = []
    print(LINEA)
    for reg in registrazioni:
        testo, parlato, vocali = whatsapp_reader.descrivi(reg, len(vocali_totali))
        stampa(testo)
        print()
        if ad_alta_voce:
            voce.parla(parlato)
        vocali_totali.extend(vocali)
    print(LINEA)
    if not vocali_totali:
        return
    stampa(f"Ci sono {len(vocali_totali)} messaggi vocali.")
    while True:
        scelta = input("Numero del vocale da ascoltare (Invio per continuare): ").strip()
        if not scelta:
            return
        if scelta.isdigit() and 1 <= int(scelta) <= len(vocali_totali):
            file_audio = vocali_totali[int(scelta) - 1]
            if not os.path.exists(file_audio):
                stampa("Jarvis: file del vocale non trovato.")
            elif hasattr(os, "startfile"):
                os.startfile(file_audio)  # apre il lettore audio di Windows
            else:
                stampa("File: " + file_audio)
        else:
            stampa("Jarvis: numero non valido.")


def all_avvio_whatsapp():
    nuovi = whatsapp_reader.nuovi()
    if not nuovi:
        stampa("Jarvis: nessun nuovo messaggio WhatsApp.")
        return
    annuncio = f"Bentornato. Hai {len(nuovi)} nuovi messaggi WhatsApp."
    stampa("Jarvis: " + annuncio)
    voce.parla(annuncio)
    riferisci_whatsapp(nuovi)
    whatsapp_reader.segna_letti(nuovi)


def main():
    from meccanica import EspertoMeccanica

    print(LINEA)
    stampa("  J.A.R.V.I.S.  -  Assistente personale")
    print(LINEA)
    esperto = EspertoMeccanica()
    stampa(f"Jarvis: manuale di meccanica caricato ({len(esperto.brani)} passaggi).")
    all_avvio_whatsapp()

    while True:
        print()
        print("  1) Leggi le email NON lette")
        print("  2) Leggi le ultime email")
        print("  3) Cerca nelle email")
        print("  4) Domanda di meccanica")
        print("  5) Rileggi i messaggi WhatsApp di oggi")
        print("  0) Esci")
        scelta = input("Scelta: ").strip()
        if scelta == "1":
            sessione_email("is:unread")
        elif scelta == "2":
            sessione_email("")
        elif scelta == "3":
            stampa("Esempi: from:amazon   subject:fattura   bolletta   after:2026/11/01")
            q = input("Cosa cerco? ").strip()
            if q:
                sessione_email(q, solo_posta_in_arrivo=False)
        elif scelta == "4":
            sessione_meccanica(esperto)
        elif scelta == "5":
            oggi = whatsapp_reader.tutti()
            from datetime import datetime
            inizio_giornata = datetime.now().astimezone().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            oggi = [
                r for r in oggi
                if datetime.fromisoformat(r["inizio"].replace("Z", "+00:00")) >= inizio_giornata
            ]
            riferisci_whatsapp(oggi)
            whatsapp_reader.segna_letti(oggi)
        elif scelta == "0":
            stampa("Jarvis: a presto.")
            return
        else:
            stampa("Jarvis: scelta non valida.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nJarvis: a presto.")
