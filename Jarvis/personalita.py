"""
Jarvis - Personalita'.

Regole:
- risposte serie, precise, senza giri di parole e senza complimenti;
- se Jarvis non e' sicuro almeno al 90% (SOGLIA_CERTEZZA), non risponde/non agisce
  e lo dice;
- insulta SOLO quando l'errore e' dell'utente (comando vuoto o incompleto,
  nome inesistente, password sbagliata...), mai per errori propri.
"""

import random

import config

SOGLIA_CERTEZZA = getattr(config, "SOGLIA_CERTEZZA", 0.90)

_INSULTI = [
    "Coglione.",
    "Ma sei serio, coglione?",
    "Svegliati, genio.",
    "Complimenti, un capolavoro di stupidità.",
    "Usa il cervello, ogni tanto.",
    "Ritenta, testa vuota.",
    "Neanche un criceto avrebbe sbagliato così.",
]


def insulto():
    if not getattr(config, "INSULTI_ATTIVI", True):
        return ""
    return random.choice(_INSULTI)


def errore_utente(spiegazione):
    """Errore causato dall'utente: spiegazione secca + insulto."""
    i = insulto()
    return f"{i} {spiegazione}".strip()


def incerto(cosa=""):
    base = "Dati insufficienti per verificare."
    return f"{base} {cosa}".strip()


def saggio(testo_normale, testo_saggio):
    """Sceglie la frase in base allo stile impostato."""
    return testo_saggio if getattr(config, "STILE_SAGGIO", False) else testo_normale
