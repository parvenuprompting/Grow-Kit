"""GrowKit stappen-motor — voert uit, seed.py-gedrag: bewijs of mens.

Faalcontract: één commando, bij falen precies één alternatief, dan de mens.
Elke stap wordt append-only gelogd vóórdat de volgende begint.

Review-laag (spec §9, fase 3): bij een mens_nodig-stap mét review-rol én
reviewconfig krijgt de reviewer eerst een blik. Oordeel 'geslaagd' →
status review_ok_wacht_ratificatie en de motor GAAT DOOR (ratificatie in
bulk, later). 'gefaald'/'onduidelijk'/geen config → klassiek mens-moment.
Machine-bewijs-stappen gaan nooit naar een reviewer.
"""
import datetime
import json
import subprocess
from pathlib import Path

from kern.growkit_bewijs import controleer


def vervang_growkit_pad(profiel: dict, growkit_root: Path) -> dict:
    """Vervang {GROWKIT}-plaatshouders in stap-commando's door het echte repo-pad.

    Enige plek waar deze substitutie mag plaatsvinden — de motor draait
    commando's met cwd=doel, dus paden naar sjablonen moeten absoluut zijn.
    """
    root = str(growkit_root)
    for stap in profiel.get("stappen", []):
        if "commando" in stap and isinstance(stap["commando"], str):
            stap["commando"] = stap["commando"].replace("{GROWKIT}", root)
        alternatief = stap.get("bij_falen", {}).get("alternatief_commando")
        if alternatief:
            stap["bij_falen"]["alternatief_commando"] = alternatief.replace("{GROWKIT}", root)
    return profiel


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


def _log(logboek: Path, stap_id: str, status: str, bewijstekst: str,
         extra: dict | None = None) -> None:
    entries = json.loads(logboek.read_text(encoding="utf-8")) if logboek.exists() else []
    entry = {"stap": stap_id, "status": status, "bewijs": bewijstekst, "tijdstip": _nu()}
    if extra:
        entry.update(extra)
    entries.append(entry)
    logboek.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _behandel_mensstap(stap: dict, logboek: Path, reviewconfig: dict | None) -> None:
    """Mens-stap: reviewer eerst (indien geconfigureerd), anders klassiek mens-moment."""
    instructie = stap["mens_nodig"].get("instructie", "")
    rol = stap.get("review")
    oordeel = None
    if rol and reviewconfig:
        from kern.growkit_review import roep_reviewer
        oordeel = roep_reviewer(rol, stap, instructie, reviewconfig)
    if oordeel == "geslaagd":
        extra = {"review_rol": rol, "review_oordeel": oordeel,
                 "noot": "latere stappen bouwen mogelijk op deze nog-te-ratificeren stap"}
        _log(logboek, stap["id"], "review_ok_wacht_ratificatie", instructie, extra)
        print(f"  [review-ok] {stap['id']}: reviewer '{rol}' oordeelde geslaagd — wacht op ratificatie.")
        return  # motor gaat door
    if oordeel is not None:
        extra = {"review_rol": rol, "review_oordeel": oordeel}
        _log(logboek, stap["id"], "wacht_op_mens", instructie, extra)
        print(f"  [mens-moment] {stap['id']}: reviewer '{rol}' oordeelde '{oordeel}' — de mens beslist. {instructie}")
        return
    _log(logboek, stap["id"], "wacht_op_mens", instructie)
    print(f"  [mens-moment] {stap['id']}: {instructie}")


def voer_uit(profiel: dict, doel: Path, logboek: Path, sjablonen_map: Path | None,
             reviewconfig: dict | None = None) -> bool:
    """Volledige run. Mens-stappen pauzeren (wacht_op_mens), bewijs-stappen bewijzen."""
    alles_geslaagd = True
    for stap in profiel["stappen"]:
        if stap.get("mens_nodig"):
            _behandel_mensstap(stap, logboek, reviewconfig)
            continue  # fase 1: mens-momenten tonen we, auto-hervatten komt later
        ok, bewijstekst = voer_stap_uit(stap, doel, sjablonen_map)
        _log(logboek, stap["id"], "geslaagd" if ok else "gefaald", bewijstekst)
        print(f"  [{'OK' if ok else 'X'}] {stap['id']} — {bewijstekst}")
        if not ok:
            print(f"  Stap {stap['id']} faalde na alternatief. Roep de mens.")
            return False
    return alles_geslaagd
