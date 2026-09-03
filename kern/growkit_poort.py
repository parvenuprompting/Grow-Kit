"""GrowKit Scope-poort — geen actie zonder heldere scope (spec §11).

De poort beoordeelt uitsluitend of de verplichte structuur aanwezig is:
veldaanwezigheid en -vorm, nooit inhoud. Kwaliteitsbeoordeling is
interpretatie en blijft bij de mens.

Slijper-schuring (§11.1, fase 3): de slijper voegt formulier-antwoorden
samenvoegend zonder her-interpretatie in het concept; wat ontbreekt wordt
een vraag, nooit een aanname. Enige uitzondering: de gelabelde
standaardwaarde voor omgeving (standaardwaarde: true + bronvermelding).
Het mens-moment (bevestiging) blijft onaangetast.
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

# §11.3-vragen per verplicht veld — alleen gesteld over wat écht ontbreekt.
_VRAGEN_PER_VELD = {
    "einddoel": {
        "vraag": "Wat is het einddoel?",
        "opties": ["tweede-brein", "autonome-fabriek", "dev-werkplaats", "iets anders (beschrijf)"],
    },
    "omgeving": {
        "vraag": "Waar moet het groeien (omgeving)?",
        "opties": ["deze machine (lokaal)", "een VPS", "iets anders (beschrijf)"],
    },
    "slaag_criterium": {
        "vraag": "Wanneer is het geslaagd (slaag-criterium)?",
        "opties": ["structuur bestaat en logboek is leeg", "ik zie het werken in één voorbeeld", "iets anders (beschrijf)"],
    },
}

# Slijper-standaard (§11.1 punt 2): de enige invul die de slijper mag doen —
# altijd gelabeld (standaardwaarde: true) met bronvermelding, nooit het einddoel.
_OMGEVING_STANDAARD = {
    "waarde": "deze machine (lokaal)",
    "standaardwaarde": True,
    "bron": "slijper-standaard (§11.1 punt 2) — niet uit de invoer afgeleid; bevestig of pas aan",
}


def _vragenlijst_vrij() -> list[dict]:
    """Vragenlijst in het vaste §11.3-JSON-formaat (alle verplichte velden)."""
    return [_VRAGEN_PER_VELD[veld] for veld in _VERPLICHT_VRIJ]


def _concept_uit_invoer(invoer: dict, standaarden: dict | None = None) -> dict:
    """Formulier-antwoorden → opdracht (§11.3 punt 2): samenvoegen zonder
    her-interpretatie. Alleen velden met een gelabelde standaardwaarde worden
    ingevuld; de rauwe invoer gaat mee als bron (§11.1 loggen)."""
    concept: dict = {}
    for veld in _VERPLICHT_VRIJ:
        if standaarden and veld in standaarden:
            concept[veld] = dict(standaarden[veld])
        else:
            concept[veld] = invoer[veld]
    concept["bron"] = {"ruwe_invoer": invoer.get("tekst", "")}
    concept["status"] = "wacht_op_mens"
    return concept


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
        if not ontbreekt:
            concept = _concept_uit_invoer(invoer)
            return True, json.dumps(concept, indent=2, ensure_ascii=False), []
        if ontbreekt == ["omgeving"]:
            # slijper-schuring (§11.1): uitsluitend de gelabelde standaardwaarde
            concept = _concept_uit_invoer(invoer, standaarden={"omgeving": _OMGEVING_STANDAARD})
            return True, json.dumps(concept, indent=2, ensure_ascii=False), []
        return False, WEIGERING_BUI, [_VRAGEN_PER_VELD[veld] for veld in ontbreekt]

    if type_ == "taak":
        bewijs = invoer.get("bewijs")
        if not isinstance(bewijs, dict) or "type" not in bewijs:
            return False, WEIGERING_TAAK, []
        return True, "taak heeft bewijs-check — geldig volgens §4-schema", []

    raise ValueError(f"onbekend invoertype: {type_!r} (geldige types: kiemkeuze, vrije_beschrijving, taak)")
