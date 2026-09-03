#!/usr/bin/env python3
"""GrowKit loop.py — het harnas: dunne provider-agnostische orchestratieloop (§8).

De loop tekent de formulieren zelf (§11.3-4) maar interpreteert geen inhoud:
de Scope-poort blijft de enige invoerbescherming en de motor het enige
uitvoeringspad. Kernregel in fase 4 (§11.1 hard): de loop voert niets uit
dat niet de mensbevestiging heeft gehad.
"""
import json
import sys
from pathlib import Path

from seed import laad_profielen, vraag_mijlpaal_bevestiging, PROFILES_DIR
from kern import growkit_motor, growkit_poort
from kern import growkit_hervat
from kern.growkit_review import laad_reviewconfig
from kern.growkit_taken import laad_taken, log_taakgebeurtenis, valideer_taak

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
        profiel = json.load(f)
    profiel = growkit_motor.vervang_growkit_pad(profiel, REPO.resolve())
    if growkit_poort.mijlpaal_nodig(profiel):
        if not vraag_mijlpaal_bevestiging(profiel, doel_pad, logboek, invoer_fn=invoer_fn):
            return 1
    sjablonen = PROFILES_DIR / naam / "sjablonen"
    geslaagd = growkit_motor.voer_uit(profiel, doel_pad, logboek, sjablonen, reviewconfig=reviewconfig)
    return 0 if geslaagd else 2


def hervat_boom(doel: Path | None = None, profiel: dict | None = None, invoer_fn=input) -> int:
    """Hervat-modus: reconstructie uit het logboek (§7) → restdraai-profiel.

    Overslaan-stappen draaien nooit opnieuw (niet-idempotent: hard filter).
    De rest draait pas na mens-bevestiging. Corrupt logboek → mens, geen crash.
    """
    if doel is None:
        doel_invoer = invoer_fn("  Waar groeit de boom? (map): ").strip()
        if not doel_invoer:
            print("  Geen map — geen actie.")
            return 1
        doel = Path(doel_invoer).expanduser().resolve()
    logboek = doel / "logboek.json"
    if profiel is None:
        try:
            bewijs = json.loads((doel / "geboortebewijs.json").read_text(encoding="utf-8"))
            with open(PROFILES_DIR / bewijs["profiel"] / "profiel.json", encoding="utf-8") as f:
                profiel = json.load(f)
        except (OSError, json.JSONDecodeError, KeyError) as e:
            print(f"  Geboortebewijs of profiel onleesbaar ({e}) — roep de mens.")
            return 1
    profiel = growkit_motor.vervang_growkit_pad(profiel, REPO.resolve())
    resultaat = growkit_hervat.reconstructie(logboek, profiel)
    if resultaat.get("fout") == "corrupt_logboek":
        print("  Logboek is corrupt — roep de mens. Geen auto-reparatie.")
        return 1
    restdraai = [s for s in profiel.get("stappen", [])
                 if resultaat["stappen"][s["id"]]["beslissing"] in ("heraanbieden", "uitvoeren")]
    if not restdraai:
        print("  Niets te hervatten — alle stappen zijn geslaagd of wachten op ratificatie.")
        return 0
    herstartpunt = resultaat["herstartpunt"]
    if herstartpunt == "start":
        print("  Herstartpunt: de start — er is nog geen mijlpaal bevestigd.")
    else:
        print(f"  Herstartpunt: {herstartpunt['stap']} bevestigd op {herstartpunt['tijdstip']}.")
    for stap in profiel.get("stappen", []):
        info = resultaat["stappen"][stap["id"]]
        if info["beslissing"] == "overslaan" and info["noot"]:
            print(f"  — {stap['id']}: {info['noot']}")
    print(f"  Restdraai: {len(restdraai)} stappen ({', '.join(s['id'] for s in restdraai)}).")
    if invoer_fn("  Restdraai uitvoeren? (ja / pas aan): ").strip().lower() != "ja":
        print("  Geen bevestiging — geen actie.")
        return 1
    reviewconfig = laad_reviewconfig(REPO / "reviewconfig.json")
    geslaagd = growkit_motor.voer_uit({**profiel, "stappen": restdraai}, doel, logboek,
                                      PROFILES_DIR / profiel["profiel"] / "sjablonen",
                                      reviewconfig=reviewconfig)
    return 0 if geslaagd else 2


def _wacht_ratificatie_stappen(logboek: Path) -> list[str]:
    """Stappen waarvan de laatst gelogde status review_ok_wacht_ratificatie is,
    in volgorde van eerste verschijning."""
    laatste: dict[str, str] = {}
    volgorde: list[str] = []
    for entry in json.loads(logboek.read_text(encoding="utf-8")):
        sid = entry.get("stap")
        if not sid:
            continue
        if sid not in laatste:
            volgorde.append(sid)
        laatste[sid] = entry.get("status")
    return [sid for sid in volgorde if laatste[sid] == "review_ok_wacht_ratificatie"]


def ratificeer(doel: Path, invoer_fn=input) -> int:
    """Bulk-ratificatie (§9): één bevestiging; append-only vervolg-entries;
    afkeuring → herziening_nodig + doorloop-vermelding; nooit auto-rollback."""
    logboek = doel / "logboek.json"
    if not logboek.exists():
        print("  Geen ratificatie-moment — het logboek bestaat niet.")
        return 0
    wacht = _wacht_ratificatie_stappen(logboek)
    if not wacht:
        print("  Geen ratificatie-moment — geen stappen wachten op de mens.")
        return 0
    print("  Ratificatie — mens-moment in bulk (§9):")
    for i, sid in enumerate(wacht, start=1):
        print(f"    {i}. {sid} — review_ok_wacht_ratificatie")
    antwoord = invoer_fn(
        "  Alles ratificeren? (ja / nummers om af te keuren, bijv. 1 / nee): ").strip().lower()
    if antwoord == "ja":
        entries = json.loads(logboek.read_text(encoding="utf-8"))
        for sid in wacht:
            entries.append({"type": "ratificatie", "stap": sid, "status": "geratificeerd",
                            "bewijs": "bulk-ratificatie door de mens (§9)",
                            "tijdstip": _nu()})
        logboek.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  {len(wacht)} stappen geratificeerd — append-only bijgeschreven.")
        return 0
    afkeuringen = [nummer.strip() for nummer in antwoord.split(",") if nummer.strip()]
    if not all(n.isdigit() and 1 <= int(n) <= len(wacht) for n in afkeuringen):
        print("  Geen ratificatie — onbegrepen antwoord is geen actie.")
        return 1
    afgekeurd = [wacht[int(n) - 1] for n in afkeuringen]
    entries = json.loads(logboek.read_text(encoding="utf-8"))
    for sid in afgekeurd:
        laatste_index = max(i for i, e in enumerate(entries) if e.get("stap") == sid)
        latere = []
        for e in entries[laatste_index + 1:]:
            sid2 = e.get("stap")
            if sid2 and sid2 != sid and e.get("type") not in ("mijlpaal", "ratificatie") \
                    and sid2 not in latere:
                latere.append(sid2)
        vermelding = (f"afgekeurd bij bulk-ratificatie; latere stappen in het logboek: "
                      f"{', '.join(latere) if latere else 'geen'}")
        entries.append({"type": "ratificatie", "stap": sid, "status": "herziening_nodig",
                        "bewijs": vermelding, "tijdstip": _nu()})
        print(f"  {sid}: herziening_nodig — {vermelding}")
    logboek.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


def _nu() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def voer_taak(doel: Path, invoer_fn=input) -> int:
    """Taak-modus (§7): poort eerst, motor uit, append-only gebeurtenissen.

    Een taak zonder bewijs bestaat niet: geweigerd, niets uitgevoerd.
    Bij faal: mens — het motor-faalcontract staat, geen retries.
    """
    takenlijst = doel / "takenlijst.json"
    taken = laad_taken(takenlijst)
    if not taken:
        print("  Geen taken in de groeilaag — niets te doen.")
        return 0
    print("  Taken in de groeilaag:")
    for i, taak in enumerate(taken, start=1):
        print(f"    {i}. {taak.get('id', 'onbekend')} — {taak.get('titel', '')}")
    keuze = invoer_fn("  Welke taak? (nummer / q): ").strip().lower()
    if keuze == "q":
        print("  Geen actie.")
        return 0
    try:
        taak = taken[int(keuze) - 1]
    except (ValueError, IndexError):
        print("  Onbekende taak — geen actie.")
        return 1
    taak_id = taak.get("id", "onbekend")
    bevindingen = valideer_taak(taak)
    if bevindingen:
        print("  Deze taak bestaat niet: poort-weigering.")
        for b in bevindingen:
            print(f"    — {b}")
        log_taakgebeurtenis(doel / "taken-logboek.json", taak_id, "geweigerd",
                            "poort-weigering: " + "; ".join(bevindingen))
        return 1
    print(f"  Taak {taak_id} uitvoeren — taak: {taak.get('titel', '')}")
    log_taakgebeurtenis(doel / "taken-logboek.json", taak_id, "bezig", "motor-start")
    boom_logboek = doel / "logboek.json"
    if not boom_logboek.exists():
        boom_logboek.write_text("[]", encoding="utf-8")
    reviewconfig = laad_reviewconfig(REPO / "reviewconfig.json")
    geslaagd = growkit_motor.voer_uit({"profiel": f"taak-{taak_id}", "stappen": [taak]},
                                      doel, boom_logboek, None, reviewconfig=reviewconfig)
    if geslaagd:
        log_taakgebeurtenis(doel / "taken-logboek.json", taak_id, "geslaagd",
                            "machine-bewijs (§3)")
        return 0
    log_taakgebeurtenis(doel / "taken-logboek.json", taak_id, "gefaald",
                        "motor-faalcontract — roep de mens")
    return 2


def detecteer_omgeving(profiel_pad: Path) -> dict:
    """§11.3-3b: omgevingsdetectie als gelabelde bron (fase-3-mechanisme).

    Alleen veldaanwezigheid: bestaat vps-doel.json in het profiel → VPS-
    standaard, anders lokaal. De inhoud (host/gebruiker/poort) wordt nooit
    geopend en kan daarom nooit in een concept verschijnen.
    """
    if (profiel_pad / "vps-doel.json").exists():
        return {"waarde": "een VPS", "standaardwaarde": True,
                "bron": "omgevingsdetectie: vps-doel.json aanwezig in het profiel (§11.3-3b)"}
    return {"waarde": "deze machine (lokaal)", "standaardwaarde": True,
            "bron": "omgevingsdetectie: geen vps-doel.json in het profiel (§11.3-3b)"}


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
    if keuze == "2":
        return hervat_boom(invoer_fn=invoer_fn)
    if keuze == "3":
        doel_invoer = invoer_fn("  Waar groeit de boom? (map): ").strip()
        if not doel_invoer:
            print("  Geen map — geen actie.")
            return 1
        return voer_taak(Path(doel_invoer).expanduser().resolve(), invoer_fn=invoer_fn)
    if keuze == "4":
        doel_invoer = invoer_fn("  Waar groeit de boom? (map): ").strip()
        if not doel_invoer:
            print("  Geen map — geen actie.")
            return 1
        return ratificeer(Path(doel_invoer).expanduser().resolve(), invoer_fn=invoer_fn)
    if keuze in MODI:
        print(f"  Modus '{MODI[keuze][0]}' volgt in een latere taak van fase 4.")
        return 0
    print("  Onbekende modus — geen actie.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
