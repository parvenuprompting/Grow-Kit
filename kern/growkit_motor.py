"""GrowKit stappen-motor — voert uit, seed.py-gedrag: bewijs of mens.

Faalcontract: één commando, bij falen precies één alternatief, dan de mens.
Elke stap wordt append-only gelogd vóórdat de volgende begint.
"""
import datetime
import json
import subprocess
from pathlib import Path

from kern.growkit_bewijs import controleer


def _nu() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def voer_stap_uit(stap: dict, doel: Path, sjablonen_map: Path | None) -> tuple[bool, str]:
    """Eén stap: commando → bewijs → (alternatief) → mens."""
    resultaat = subprocess.run(stap["commando"], shell=True, cwd=doel,
                               capture_output=True, text=True, timeout=300)
    ok, bewijstekst = controleer(stap["bewijs"], doel, sjablonen_map=sjablonen_map)
    if not ok and stap.get("bij_falen", {}).get("alternatief_commando"):
        subprocess.run(stap["bij_falen"]["alternatief_commando"], shell=True, cwd=doel,
                       capture_output=True, text=True, timeout=300)
        ok, bewijstekst = controleer(stap["bewijs"], doel, sjablonen_map=sjablonen_map)
        if not ok:
            bewijstekst += " — ook na alternatief_commando"
    return ok, bewijstekst


def _log(logboek: Path, stap_id: str, status: str, bewijstekst: str) -> None:
    entries = json.loads(logboek.read_text(encoding="utf-8")) if logboek.exists() else []
    entries.append({"stap": stap_id, "status": status, "bewijs": bewijstekst, "tijdstip": _nu()})
    logboek.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def voer_uit(profiel: dict, doel: Path, logboek: Path, sjablonen_map: Path | None) -> bool:
    """Volledige run. Mens-stappen pauzeren (wacht_op_mens), bewijs-stappen bewijzen."""
    alles_geslaagd = True
    for stap in profiel["stappen"]:
        if stap.get("mens_nodig"):
            _log(logboek, stap["id"], "wacht_op_mens", stap["mens_nodig"].get("instructie", ""))
            print(f"  [mens-moment] {stap['id']}: {stap['mens_nodig'].get('instructie', '')}")
            continue  # fase 1: mens-momenten tonen we, auto-hervatten komt later
        ok, bewijstekst = voer_stap_uit(stap, doel, sjablonen_map)
        _log(logboek, stap["id"], "geslaagd" if ok else "gefaald", bewijstekst)
        print(f"  [{'OK' if ok else 'X'}] {stap['id']} — {bewijstekst}")
        if not ok:
            print(f"  Stap {stap['id']} faalde na alternatief. Roep de mens.")
            return False
    return alles_geslaagd
