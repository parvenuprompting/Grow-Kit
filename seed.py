#!/usr/bin/env python3
"""GrowKit seed.py — het plant-mechanisme.

Gebruik:
    python3 seed.py                          # interactieve kiemkeuze
    python3 seed.py --profiel tweede-brein --doel ~/mijn-brein
    python3 seed.py --slijp                  # Prompt-slijper (fase 3)
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

PROFILES_DIR = Path(__file__).parent / "profielen"
SLIJPER_LOG = Path(__file__).parent / "groei" / "slijper-logboek.json"
VERSIE = "0.1.0"


def _log_slijper(ruwe_invoer: str, geschuurd: str, beslissing: str) -> None:
    """Append-only log van elke slijper-beurt: ruw + geschuurd + beslissing (§11.1)."""
    SLIJPER_LOG.parent.mkdir(parents=True, exist_ok=True)
    entries = json.loads(SLIJPER_LOG.read_text(encoding="utf-8")) if SLIJPER_LOG.exists() else []
    entries.append({
        "type": "slijper",
        "ruw": ruwe_invoer,
        "concept": geschuurd,
        "beslissing": beslissing,
        "tijdstip": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    })
    SLIJPER_LOG.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def mijlpaal_blok(profiel: dict, doel: Path, logboek: Path) -> str:
    """Vast mijlpaal-formaat (spec §11.4): begrepen / afgesproken mèt
    logboek-verwijzing / bewijs tot nu toe / hierna."""
    stappen = len(profiel.get("stappen", []))
    return (
        "  ── Mijlpaal-controle (§11.4) ──\n"
        f"  1. Wat ik begrepen heb: profiel '{profiel['profiel']}' planten in {doel} — {stappen} stappen.\n"
        f"  2. Wat we afgesproken hebben: het stappenplan staat in het profiel; elke stap wordt\n"
        f"     append-only gelogd in {logboek} (controleerbaar, geen 'volgens mij was dat zo').\n"
        "  3. Het bewijs tot nu toe: nog geen stappen uitgevoerd — dit is de start van de plant.\n"
        "  4. Wat hierna komt: de motor voert de stappen uit; bij faal of twijfel stopt zij en roept de mens."
    )


def vraag_mijlpaal_bevestiging(profiel: dict, doel: Path, logboek: Path,
                               invoer_fn=input) -> bool:
    """Eén bevestiging vóór de motorstart (§11.4). 'ja' → append-only gelogd,
    daarna pas planten. Alles anders → geen actie."""
    print(mijlpaal_blok(profiel, doel, logboek))
    antwoord = invoer_fn("  Klopt dit? (ja / pas aan): ").strip().lower()
    if antwoord != "ja":
        print("  Geen bevestiging — geen actie.")
        return False
    entries = json.loads(logboek.read_text(encoding="utf-8")) if logboek.exists() else []
    entries.append({
        "type": "mijlpaal",
        "stap": "mijlpaal-start",
        "status": "bevestigd",
        "bewijs": "mijlpaal-controle bevestigd door de mens (§11.4)",
        "tijdstip": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    })
    logboek.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def laad_profielen() -> list[dict]:
    """Lees alle profiel.json-bestanden uit profielen/."""
    profielen = []
    if not PROFILES_DIR.exists():
        return profielen
    for pad in sorted(PROFILES_DIR.glob("*/profiel.json")):
        try:
            with open(pad, encoding="utf-8") as f:
                profielen.append(json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ! Ongeldig profielbestand {pad}: {e}")
    return profielen


def kiemkeuze() -> dict | None:
    """Interactieve kiemkeuze: welke boom, welke plek."""
    print()
    print("  Wat wil je laten groeien?")
    print()
    profielen = laad_profielen()
    if not profielen:
        print("  Geen profielen gevonden in profielen/. Roep de mens.")
        return None
    for i, p in enumerate(profielen, start=1):
        status = p.get("status", "?")
        print(f"  {i}. {p['profiel']} — {p.get('beschrijving', '')}"
              + ("  (in ontwikkeling)" if status == "in-ontwikkeling" else ""))
    print()
    keuze = input("  Kies een nummer (of 'q' om te stoppen): ").strip()
    if keuze.lower() == "q":
        return None
    try:
        gekozen = profielen[int(keuze) - 1]
    except (ValueError, IndexError):
        print("  Ongeldige keuze. Dit is nog geen opdracht — dit is ruis.")
        return None
    if gekozen.get("status") == "in-ontwikkeling":
        print(f"  Profiel '{gekozen['profiel']}' is nog in ontwikkeling; "
              "de agent stelt onderweg vragen. Voor nu: kies een bewezen profiel.")
        return None
    doel = input("  Waar moet het groeien? (map, bijv. ~/mijn-brein): ").strip()
    if not doel:
        print("  Geen doel = geen opdracht. Noem een map, dan plant ik.")
        return None
    return {"profiel": gekozen["profiel"], "doel": doel}


def slijper_stub() -> int:
    """Prompt-slijper komt in fase 3; nu een nette stub."""
    print("  De Prompt-slijper komt in fase 3. Voor nu: kies rechtstreeks een profiel.")
    return 0


def verwerk_vrije_beschrijving(beschrijving: str) -> int:
    """Vrije beschrijving → eerst de Scope-poort; geen actie zonder scope (spec §11)."""
    import json as _json

    from kern import growkit_poort

    invoer = {"type": "vrije_beschrijving", "tekst": beschrijving}
    # Eenvoudige veldextractie: wat expliciet genoemd is, wordt meegenomen;
    # wat ontbreekt blijft ontbrekend — de poort beslist, nooit de agent.
    for veld, sleutel in (("einddoel", "einddoel:"), ("omgeving", "omgeving:"), ("slaag_criterium", "slaag-criterium:")):
        if sleutel in beschrijving:
            invoer[veld] = beschrijving.split(sleutel, 1)[1].strip()
    ok, tekst, vragen = growkit_poort.beoordeel_invoer(invoer, "vrije_beschrijving")
    _log_slijper(beschrijving, tekst, "geaccepteerd_concept" if ok else "geweigerd")
    print()
    if not ok:
        print(f"  {tekst}")
        print()
        print("  Vragenlijst (§11.3):")
        print(f"  {_json.dumps({'vragen': vragen}, indent=2, ensure_ascii=False)}")
        print()
        print("  Geen opdracht — geen actie.")
        return 1
    print("  Concept-opdracht (§11.1 — wacht op mens-bevestiging):")
    print(f"  {tekst}")
    print()
    print("  Klopt dit? (ja / pas aan) — pas na jouw bevestiging wordt er geplant.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seed.py", description="GrowKit — plant een boom.")
    parser.add_argument("--profiel", help="profielnaam, bijv. tweede-brein")
    parser.add_argument("--doel", help="doelmap voor de plant")
    parser.add_argument("--slijp", action="store_true", help="open de Prompt-slijper (fase 3)")
    parser.add_argument("--vrij", metavar="BESCHRIJVING", help="vrije beschrijving van een nieuwe boom (gaat eerst door de Scope-poort)")
    args = parser.parse_args(argv)

    print()
    print("  ────────────────────────────────────────")
    print("   GrowKit — het zaadje dat vanzelf groeit")
    print(f"   versie {VERSIE}")
    print("  ────────────────────────────────────────")

    if args.slijp:
        return slijper_stub()

    if args.vrij is not None:
        return verwerk_vrije_beschrijving(args.vrij)

    if args.profiel and args.doel:
        keuze = {"profiel": args.profiel, "doel": args.doel}
    else:
        keuze = kiemkeuze()
        if keuze is None:
            print("  Geen opdracht — geen actie. Tot ziens.")
            return 1

    from kern import growkit_motor
    from kern.growkit_review import laad_reviewconfig
    reviewconfig = laad_reviewconfig(Path(__file__).parent / "reviewconfig.json")
    doel = Path(keuze["doel"]).expanduser().resolve()
    doel.mkdir(parents=True, exist_ok=True)
    logboek = doel / "logboek.json"
    if not logboek.exists():
        logboek.write_text("[]", encoding="utf-8")
    profiel_pad = PROFILES_DIR / keuze["profiel"] / "profiel.json"
    with open(profiel_pad, encoding="utf-8") as f:
        profiel = json.load(f)
    profiel = growkit_motor.vervang_growkit_pad(profiel, Path(__file__).parent.resolve())
    from kern import growkit_poort
    if growkit_poort.mijlpaal_nodig(profiel):
        if not vraag_mijlpaal_bevestiging(profiel, doel, logboek):
            return 1
    sjablonen = PROFILES_DIR / keuze["profiel"] / "sjablonen"
    geslaagd = growkit_motor.voer_uit(profiel, doel, logboek, sjablonen, reviewconfig=reviewconfig)
    return 0 if geslaagd else 2


if __name__ == "__main__":
    sys.exit(main())
