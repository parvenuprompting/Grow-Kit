#!/usr/bin/env python3
"""GrowKit seed.py — het plant-mechanisme.

Gebruik:
    python3 seed.py                          # interactieve kiemkeuze
    python3 seed.py --profiel tweede-brein --doel ~/mijn-brein
    python3 seed.py --slijp                  # Prompt-slijper (fase 3)
"""
import argparse
import json
import sys
from pathlib import Path

PROFILES_DIR = Path(__file__).parent / "profielen"
VERSIE = "0.1.0"


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seed.py", description="GrowKit — plant een boom.")
    parser.add_argument("--profiel", help="profielnaam, bijv. tweede-brein")
    parser.add_argument("--doel", help="doelmap voor de plant")
    parser.add_argument("--slijp", action="store_true", help="open de Prompt-slijper (fase 3)")
    args = parser.parse_args(argv)

    print()
    print("  ────────────────────────────────────────")
    print("   GrowKit — het zaadje dat vanzelf groeit")
    print(f"   versie {VERSIE}")
    print("  ────────────────────────────────────────")

    if args.slijp:
        return slijper_stub()

    if args.profiel and args.doel:
        keuze = {"profiel": args.profiel, "doel": args.doel}
    else:
        keuze = kiemkeuze()
        if keuze is None:
            print("  Geen opdracht — geen actie. Tot ziens.")
            return 1

    import growkit_motor
    doel = Path(keuze["doel"]).expanduser().resolve()
    doel.mkdir(parents=True, exist_ok=True)
    logboek = doel / "logboek.json"
    if not logboek.exists():
        logboek.write_text("[]", encoding="utf-8")
    profiel_pad = PROFILES_DIR / keuze["profiel"] / "profiel.json"
    with open(profiel_pad, encoding="utf-8") as f:
        profiel = json.load(f)
    sjablonen = PROFILES_DIR / keuze["profiel"] / "sjablonen"
    geslaagd = growkit_motor.voer_uit(profiel, doel, logboek, sjablonen)
    return 0 if geslaagd else 2


if __name__ == "__main__":
    sys.exit(main())
