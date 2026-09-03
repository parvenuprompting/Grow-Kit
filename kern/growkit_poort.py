"""GrowKit Scope-poort — geen actie zonder heldere scope (spec §11).

De poort beoordeelt uitsluitend of de verplichte structuur aanwezig is:
veldaanwezigheid en -vorm, nooit inhoud. Kwaliteitsbeoordeling is
interpretatie en blijft bij de mens.
"""
import json

# Vaste weigeringsteksten (spec §11) — constanten, nooit gegenereerd.
WEIGERING_BUI = (
    "Dit is nog geen opdracht — dit is een bui. "
    "Noem: wat wil je laten groeien, waar, en wanneer is het geslaagd. Dan plant ik."
)
WEIGERING_TUINIER = (
    "Ik ga niet raden wat je bedoelt; ik ben een tuinier, geen helderziende. "
    "Drie vragen: doel, plek, slaag-criterium."
)
WEIGERING_TAAK = (
    "Deze taak bestaat niet: zonder bewijs-check is een taak ongeldig. "
    "Voeg een bewijs-veld toe volgens het stappen-schema (spec §4)."
)

_VERPLICHT_VRIJ = ("einddoel", "omgeving", "slaag_criterium")


def _vragenlijst_vrij() -> list[dict]:
    """Vragenlijst in het vaste §11.3-JSON-formaat."""
    return [
        {
            "vraag": "Wat is het einddoel?",
            "opties": ["tweede-brein", "autonome-fabriek", "dev-werkplaats", "iets anders (beschrijf)"],
        },
        {
            "vraag": "Waar moet het groeien (omgeving)?",
            "opties": ["deze machine (lokaal)", "een VPS", "iets anders (beschrijf)"],
        },
        {
            "vraag": "Wanneer is het geslaagd (slaag-criterium)?",
            "opties": ["structuur bestaat en logboek is leeg", "ik zie het werken in één voorbeeld", "iets anders (beschrijf)"],
        },
    ]


def beoordeel_invoer(invoer: dict, type_: str) -> tuple[bool, str, list[dict]]:
    """Beoordeel invoer op verplichte structuur.

    Retourneert (geaccepteerd, tekst-of-concept, vragenlijst).
    Geaccepteerd=True betekent: de invoer is een geldige opdracht die
    als concept wacht op mens-bevestiging (§11.1) — niet direct uitvoeren.
    """
    if type_ == "kiemkeuze":
        if not invoer.get("profiel") or not invoer.get("doel"):
            return False, WEIGERING_TUINIER, _vragenlijst_vrij()
        return True, "kiemkeuze compleet (profiel + doel) — wacht_op_mens", []

    if type_ == "vrije_beschrijving":
        ontbreekt = [v for v in _VERPLICHT_VRIJ if not invoer.get(v)]
        if ontbreekt:
            return False, WEIGERING_BUI, _vragenlijst_vrij()
        concept = {
            "einddoel": invoer["einddoel"],
            "omgeving": invoer["omgeving"],
            "slaag_criterium": invoer["slaag_criterium"],
            "status": "wacht_op_mens",
        }
        return True, json.dumps(concept, indent=2, ensure_ascii=False), []

    if type_ == "taak":
        bewijs = invoer.get("bewijs")
        if not isinstance(bewijs, dict) or "type" not in bewijs:
            return False, WEIGERING_TAAK, []
        return True, "taak heeft bewijs-check — geldig volgens §4-schema", []

    raise ValueError(f"onbekend invoertype: {type_!r} (geldige types: kiemkeuze, vrije_beschrijving, taak)")
