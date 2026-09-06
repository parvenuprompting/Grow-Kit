"""Telegram-koppel-kern — de wizard-data achter "Telegram Connect".

De begeleiding (wat de mens in Telegram/BotFather doet) staat hier als
stappenlijsten; de tokens gaan één keer in via de app en leven uitsluitend
in de macOS Sleutelhangar. De wizard-state (voortgang) bevat nooit tokens.

Familie-modus: 7 agents × 6 stappen + 2 groep-stappen (uit bouwplan B3).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

FAMILIE = ["kairos", "riri", "vigil", "libra", "memoria", "codex", "genius"]

# 6 stappen per agent (familie-modus, bouwplan B3)
_AGENT_STAPPEN = [
    "BotFather: /newbot → naam (bijv. {Naam}) + gebruikersnaam "
    "(bijv. {lower}_family_bot) → token kopiëren",
    "Token plakken in het invoerveld hieronder — hij gaat één keer naar "
    "de Sleutelhangar en is daarna niet meer terug te lezen in de app",
    "@userinfobot: stuur hem een bericht → noteer jouw chat-ID",
    "Chat-ID invullen hieronder — de app zet hem in het profiel-config",
    "Gateway-herstart (commando staat bij de knop — uitvoeren blijft bij jou, "
    "systeemgrens)",
    "Test: stuur /status naar díe bot — verwacht antwoord van díe agent",
]

# 2 groep-stappen (familie-afsluiting)
_GROEP_STAPPEN = [
    'Telegram-groep "Parvenu Agent Family" aanmaken en alle 7 bots '
    "toevoegen; groep-ID invullen (komt in elk profiel-config)",
    "Verdeelregel-test: één bericht in de groep → precies één agent "
    "antwoordt (volgens de ANTWOORD-VERDEELREGEL in de SOUL's)",
]


def stappen_voor(agent: str) -> list[str]:
    if agent not in FAMILIE:
        raise ValueError(f"Onbekende agent: {agent}")
    naam = agent.capitalize()
    lower = agent.lower()
    return [s.replace("{Naam}", naam).replace("{lower}", lower)
            for s in _AGENT_STAPPEN]


def groep_stappen() -> list[str]:
    return list(_GROEP_STAPPEN)


# ---------------------------------------------------------------------------
# Voortgang (append-only log → genormaliseerde stand)
# ---------------------------------------------------------------------------

def _voortgang_pad() -> Path:
    return Path.home() / ".growkit" / "telegram_wizard.json"


def _lees_stand() -> dict[str, list[int]]:
    pad = _voortgang_pad()
    if not pad.exists():
        return {}
    try:
        return json.loads(pad.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def voortgang() -> dict[str, list[int]]:
    """{agent: [voltooide stapnummers]} — nooit tokens."""
    return _lees_stand()


def markeer_klaar(agent: str, stap: int, *, token: str = "") -> None:
    """Markeer stap <stap> van <agent> als voltooid. Een eventueel token
    gaat uitsluitend naar de Sleutelhangar — de state bevat het nooit."""
    if agent not in FAMILIE:
        raise ValueError(f"Onbekende agent: {agent}")
    if token:
        if not bewaar_token(agent, token):
            raise RuntimeError("Token kon niet in de Sleutelhangar worden bewaard.")
    stand = _lees_stand()
    lijst = stand.get(agent, [])
    if stap not in lijst:
        lijst.append(stap)
        lijst.sort()
    stand[agent] = lijst
    pad = _voortgang_pad()
    pad.parent.mkdir(parents=True, exist_ok=True)
    pad.write_text(json.dumps(stand, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------------------
# Sleutelhangar (token óók veilig op de Mac; VPS-koppeling is fase B4)
# ---------------------------------------------------------------------------

def _keychain_service(agent: str) -> str:
    return f"GrowKit Telegram: {agent}"


def bewaar_token(agent: str, token: str) -> bool:
    if agent not in FAMILIE:
        raise ValueError(f"Onbekende agent: {agent}")
    try:
        subprocess.run(
            ["security", "add-generic-password",
             "-s", _keychain_service(agent),
             "-a", agent,
             "-w", token,
             "-U"],
            check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def toon_token_mask(agent: str) -> str:
    """Alleen de laatste 4 tekens — de app toont nooit het hele token."""
    try:
        r = subprocess.run(
            ["security", "find-generic-password",
             "-s", _keychain_service(agent), "-w"],
            capture_output=True, text=True)
        if r.returncode != 0:
            return "niet ingesteld"
        waarde = r.stdout.strip()
        return "••••" + waarde[-4:] if len(waarde) >= 4 else "••••"
    except OSError:
        return "niet ingesteld"
