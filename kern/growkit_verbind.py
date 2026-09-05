"""Centrale verbinding-constanten voor de agent-bridges (audit 5 sept 2026).

Het SSH-doel van de agent-familie staat hier op precies één plek.
Omleidbaar via de omgeving, zelfde patroon als de GROWKIT_*-overrides:

    GROWKIT_HOST=gebruiker@voorbeeld.test python3 adapter.py status

Of via een lokaal .env-bestand in de repo (in .gitignore, per machine):

    GROWKIT_HOST=gebruiker@jouw.vps.adres

De drift-guard-regel (§13: ssh-doeleinden blijven lokaal per boom) geldt
onverminderd; deze constante is alleen de standaardwaarde voor de
agent-bridges (agenttaak, agentcontrole, agentstatus, graaf, observaties).
"""
import os


def _lees_env(pad: str) -> dict[str, str]:
    """Lees GROWKIT_HOST uit een lokaal .env-bestand (één per regel)."""
    env: dict[str, str] = {}
    if not os.path.isfile(pad):
        return env
    with open(pad, encoding="utf-8") as f:
        for regel in f:
            regel = regel.strip()
            if not regel or regel.startswith("#") or "=" not in regel:
                continue
            sleutel, _, waarde = regel.partition("=")
            env[sleutel.strip()] = waarde.strip().strip("\"'")
    return env


# Volgorde: omgevingsvariabele → lokaal .env → fout
HOST = os.environ.get("GROWKIT_HOST")
if not HOST:
    _env = _lees_env(os.path.join(os.path.dirname(__file__), "..", ".env"))
    HOST = _env.get("GROWKIT_HOST", "")
if not HOST:
    raise RuntimeError(
        "GROWKIT_HOST niet ingesteld. Zet je VPS-adres via één van deze wegen:\n"
        "  1) Omgevingsvariabele: export GROWKIT_HOST=gebruiker@jouw.vps.adres\n"
        "  2) .env-bestand in de repo-root (zie .gitignore): GROWKIT_HOST=…"
    )