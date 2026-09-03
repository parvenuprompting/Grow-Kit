#!/usr/bin/env python3
"""GrowKit loop.py — het harnas: dunne provider-agnostische orchestratieloop (§8).

De loop tekent de formulieren zelf (§11.3-4) maar interpreteert geen inhoud:
de Scope-poort blijft de enige invoerbescherming en de motor het enige
uitvoeringspad. Kernregel in fase 4 (§11.1 hard): de loop voert niets uit
dat niet de mensbevestiging heeft gehad.
"""
import sys
from pathlib import Path

from seed import laad_profielen, vraag_mijlpaal_bevestiging, PROFILES_DIR
from kern import growkit_motor, growkit_poort
from kern.growkit_review import laad_reviewconfig

REPO = Path(__file__).parent
MODI = {
    "1": ("planten", "nieuwe boom planten"),
    "2": ("hervatten", "restdraai vanuit het logboek"),
    "3": ("taak", "taak uit de groeilaag uitvoeren"),
    "4": ("ratificatie", "mens-momenten in bulk ratificeren"),
    "5": ("status", "toon de staat van de boom"),
}


def formuliervraag(vraag: str, opties: list[str], invoer_fn=input) -> str:
    """§11.3-formulier in de terminal: opties met nummers + 'iets anders'."""
    print(f"  {vraag}")
    for i, optie in enumerate(opties, start=1):
        print(f"    {i}. {optie}")
    antwoord = invoer_fn("  Kies een nummer (of beschrijf iets anders): ").strip()
    try:
        return opties[int(antwoord) - 1]
    except (ValueError, IndexError):
        return antwoord


def _bewezen_profielen() -> list[dict]:
    return [p for p in laad_profielen() if p.get("status") == "bewezen-vorm"]


def plant_profiel(invoer_fn=input) -> int:
    """Plant-modus: formulier → concept via de poort → één bevestiging → motor."""
    print()
    print("  Wat wil je laten groeien?")
    profielen = _bewezen_profielen()
    if not profielen:
        print("  Geen bewezen profielen gevonden in profielen/. Roep de mens.")
        return 1
    naam = formuliervraag("Kies een boom:", [p["profiel"] for p in profielen], invoer_fn)
    doel = invoer_fn("  Waar moet het groeien? (map, bijv. ~/mijn-brein): ").strip()
    ok, tekst, _ = growkit_poort.beoordeel_invoer({"profiel": naam, "doel": doel}, "kiemkeuze")
    print()
    if not ok:
        print(f"  {tekst}")
        print("  Geen opdracht — geen actie.")
        return 1
    print(f"  Concept-opdracht: profiel '{naam}' planten in {Path(doel).expanduser()}")
    print("  Klopt dit? (ja / pas aan) — pas na jouw bevestiging wordt er geplant.")
    if invoer_fn("  > ").strip().lower() != "ja":
        print("  Geen bevestiging — geen actie.")
        return 1

    reviewconfig = laad_reviewconfig(REPO / "reviewconfig.json")
    doel_pad = Path(doel).expanduser().resolve()
    doel_pad.mkdir(parents=True, exist_ok=True)
    logboek = doel_pad / "logboek.json"
    if not logboek.exists():
        logboek.write_text("[]", encoding="utf-8")
    with open(PROFILES_DIR / naam / "profiel.json", encoding="utf-8") as f:
        import json
        profiel = json.load(f)
    profiel = growkit_motor.vervang_growkit_pad(profiel, REPO.resolve())
    if growkit_poort.mijlpaal_nodig(profiel):
        if not vraag_mijlpaal_bevestiging(profiel, doel_pad, logboek, invoer_fn=invoer_fn):
            return 1
    sjablonen = PROFILES_DIR / naam / "sjablonen"
    geslaagd = growkit_motor.voer_uit(profiel, doel_pad, logboek, sjablonen, reviewconfig=reviewconfig)
    return 0 if geslaagd else 2


def main(invoer_fn=input) -> int:
    print()
    print("  ────────────────────────────────────────")
    print("   GrowKit — het harnas")
    print("  ────────────────────────────────────────")
    print("  Wat wil je doen?")
    for nummer, (_, omschrijving) in MODI.items():
        print(f"    {nummer}. {omschrijving}")
    print("    q. stop")
    keuze = invoer_fn("  Kies een modus: ").strip().lower()
    if keuze == "q":
        print("  Tot ziens.")
        return 0
    if keuze == "1":
        return plant_profiel(invoer_fn)
    if keuze in MODI:
        print(f"  Modus '{MODI[keuze][0]}' volgt in een latere taak van fase 4.")
        return 0
    print("  Onbekende modus — geen actie.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
