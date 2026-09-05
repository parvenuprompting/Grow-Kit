#!/usr/bin/env python3
"""GrowKit taak-contract (Fase 3) — de zes Automatiek-bouwblokken.

Een taak is geen los zinnetje maar een contract: elk blok legt een
kant vast, zodat de agent weet wat, waarom, hoe en met welke grenzen.

Regel uit Automatiek, ingebakken: secrets horen nóóit in een plan —
authenticatie leg je vast op de doelmachine. De scanner weigert taken
met key/token/wachtwoord-patronen.
"""
import re

_BLOKKEN = (
    ("doel", "01 · Doel & trigger"),
    ("bronnen", "02 · Bronnen & data"),
    ("stappen", "03 · Stappen"),
    ("verificatie", "04 · Kwaliteit & verificatie"),
    ("planning", "05 · Planning & uitvoering"),
    ("privacy", "06 · Randvoorwaarden & privacy"),
)

# secrets-scanner: wat hier op slaat, mag het contract nooit in
_PATRONEN = (
    (re.compile(r"sk-[a-zA-Z0-9_-]{16,}"), "API-sleutel (sk-…)"),
    (re.compile(r"ghp_[A-Za-z0-9]{30,}"), "GitHub-token (ghp_…)"),
    (re.compile(r"gho_[A-Za-z0-9]{30,}"), "GitHub-token (gho_…)"),
    (re.compile(r"\b\d{8,12}:AA[A-Za-z0-9_-]{30,}"), "bot-token"),
    (re.compile(r"(?i)\bwachtwoord\s*[=:]\s*\S+"), "wachtwoord in tekst"),
    (re.compile(r"(?i)\bpassword\s*[=:]\s*\S+"), "wachtwoord in tekst"),
    (re.compile(r"(?i)\bapi[-_ ]?key\s*[=:]\s*\S+"), "API-key in tekst"),
    (re.compile(r"(?i)\btoken\s*[=:]\s*\S+"), "token in tekst"),
)


def _scan(waarde: str) -> str | None:
    for patroon, label in _PATRONEN:
        if patroon.search(waarde):
            return label
    return None


def maak(*, doel: str = "", bronnen: str = "", stappen: str = "",
         verificatie: str = "", planning: str = "", privacy: str = "") -> dict:
    """Stel het contract op. doel + verificatie zijn verplicht (wat en
    hoe weten we dat het gelukt is); de rest mag nog leeg blijven."""
    velden = {"doel": doel.strip(), "bronnen": bronnen.strip(),
              "stappen": stappen.strip(), "verificatie": verificatie.strip(),
              "planning": planning.strip(), "privacy": privacy.strip()}
    if not velden["doel"]:
        return {"ok": False, "fout": "Elk contract begint bij het doel — vul blok 01."}
    if not velden["verificatie"]:
        return {"ok": False, "fout": "Zonder verificatie (blok 04) weet niemand of het gelukt is."}
    for veld, waarde in velden.items():
        treffer = _scan(waarde)
        if treffer:
            return {"ok": False, "fout":
                    f"Secret geweigerd in blok '{veld}': {treffer}. "
                    "Authenticatie leg je vast op de doelmachine, nooit in het plan."}
    blokken = []
    for veld, kop in _BLOKKEN:
        blokken.append({"nr": kop.split(" · ")[0], "titel": kop.split(" · ", 1)[1],
                        "tekst": velden[veld]})
    return {"ok": True, "data": {"blokken": blokken}}


def markdown(contract: dict) -> str:
    """Leesbare export: het contract als markdown-document."""
    regels = ["# Taak-contract", ""]
    for blok in contract.get("blokken", []):
        regels.append(f"## {blok['nr']} {blok['titel']}")
        if blok["tekst"]:
            regels.append(blok["tekst"])
        else:
            regels.append("_(nog niet ingevuld)_")
        regels.append("")
    return "\n".join(regels)
