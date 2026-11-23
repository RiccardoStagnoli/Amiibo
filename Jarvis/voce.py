"""
Jarvis - Voce (sintesi vocale gratuita di Windows, tramite pyttsx3).
Se la voce non e' disponibile, Jarvis continua a funzionare solo con il testo.
"""

import config

_motore = None
_disponibile = None


def _prepara():
    global _motore, _disponibile
    if _disponibile is not None:
        return _disponibile
    _disponibile = False
    if not getattr(config, "VOCE_ATTIVA", True):
        return False
    try:
        import pyttsx3

        _motore = pyttsx3.init()
        for v in _motore.getProperty("voices"):
            descrizione = (str(v.id) + " " + str(v.name) + " " + str(v.languages)).lower()
            if "ital" in descrizione or "it-it" in descrizione or "it_it" in descrizione:
                _motore.setProperty("voice", v.id)
                break
        _motore.setProperty("rate", getattr(config, "VELOCITA_VOCE", 175))
        _disponibile = True
    except Exception:
        _motore = None
    return _disponibile


def parla(testo):
    if not testo or not _prepara():
        return
    try:
        _motore.say(testo)
        _motore.runAndWait()
    except Exception:
        pass
