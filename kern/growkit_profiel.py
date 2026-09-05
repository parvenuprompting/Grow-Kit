#!/usr/bin/env python3
"""GrowKit profiel (slice H) — het geboortemoment van het geheugen.

Regel 6 van het huis, toegepast op het geheugen zelf:
concept → ratificatie (mens-moment) → pas dán opslag.

- Opslag is append-only: elke bekrachtiging voegt een regel toe in
  regels/; huidig/ is altijd afgeleid van de laatste regel.
- Elke regel draagt een datum: geheugen vervalt, "rol van 2026" is
  niet "rol van 2028".
- Alles lokaal (wortel/profiel.json). Niks de cloud in.
- Lege velden zijn toegestaan — "Later invullen" is een recht.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

_VELDEN = ("naam", "rol", "doel", "taal", "moment", "agenten")


def _nu() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _pad(wortel: Path | None) -> Path:
    """wortel mag een map zijn (profiel.json erin) of het bestand zelf."""
    if not wortel:
        return Path.home() / "growkit-profiel" / "profiel.json"
    w = Path(wortel)
    return w / "profiel.json" if w.is_dir() else w


def concept(naam: str = "", *, rol: str = "", doel: str = "", taal: str = "",
            moment: str = "", agenten: str = "", wortel: Path | None = None) -> dict:
    """Stap 1: het concept. Sláát niets op — het wacht op bekrachtiging."""
    ruw = {"naam": naam.strip(), "rol": rol.strip(), "doel": doel.strip(),
           "taal": taal.strip().upper(), "moment": moment.strip(),
           "agenten": agenten.strip()}
    schoon = {k: v for k, v in ruw.items() if v}
    return {"ok": True, "data": {"concept": schoon, "opgeslagen": None}}


def bekrachtig(concept_doc: dict, *, wortel: Path | None = None) -> dict:
    """Stap 3: de ratificatie. Pas hier ontstaat opslag — append-only."""
    if not isinstance(concept_doc, dict):
        return {"ok": False, "fout": "Concept is geen document."}
    schoon = {k: str(concept_doc.get(k, "")).strip()
              for k in _VELDEN if str(concept_doc.get(k, "")).strip()}
    pad = _pad(wortel)
    pad.parent.mkdir(parents=True, exist_ok=True)

    document: dict = {"huidig": {}, "regels": []}
    if pad.exists():
        try:
            document = json.loads(pad.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"ok": False, "fout": "profiel.json is corrupt — roep de mens, geen auto-herstel."}

    regel = {"datum": _nu(), **schoon}
    document["regels"].append(regel)
    document["huidig"] = {"datum": regel["datum"], **schoon}
    pad.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    return {"ok": True, "data": {"opgeslagen": str(pad), "regel": regel}}


def vergeten(veld: str, *, wortel: Path | None = None) -> dict:
    """AVG-recht: een veld laten vergeten = nieuwe regel zonder dat veld."""
    pad = _pad(wortel)
    if not pad.exists():
        return {"ok": False, "fout": "Er is nog geen profiel."}
    document = json.loads(pad.read_text(encoding="utf-8"))
    if veld not in document.get("huidig", {}):
        return {"ok": False, "fout": f"Veld '{veld}' staat niet in het profiel."}
    nieuw = {k: v for k, v in document["huidig"].items() if k != veld}
    document["regels"].append({"datum": _nu(), "vergeten": veld})
    document["huidig"] = nieuw
    pad.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    return {"ok": True, "data": {"vergeten": veld}}


def lees(*, wortel: Path | None = None) -> dict:
    pad = _pad(wortel)
    if not pad.exists():
        return {"ok": True, "data": {"profiel": None, "bestaat": False}}
    try:
        document = json.loads(pad.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "fout": "profiel.json is corrupt — roep de mens."}
    return {"ok": True, "data": {"profiel": document.get("huidig"),
                                 "regels": len(document.get("regels", [])),
                                 "bestaat": True}}


def context_regel(*, wortel: Path | None = None) -> str:
    """De ene regel die elke agent-context meekrijgt (stap 5)."""
    r = lees(wortel=wortel)
    p = r["data"]["profiel"] if r["ok"] else None
    if not p:
        return "Gebruiker is nog onbekend — stel beleefd open vragen, één per keer."
    delen = []
    if p.get("naam"):
        delen.append(f"Naam: {p['naam']}")
    if p.get("rol"):
        delen.append(f"Rol: {p['rol']}")
    if p.get("doel"):
        delen.append(f"Doel met GrowKit: {p['doel']}")
    if p.get("taal"):
        delen.append(f"Taal: {p['taal']}")
    if p.get("moment"):
        delen.append(f"Overzichtmoment: {p['moment']}")
    if p.get("agenten"):
        delen.append(f"Agenten: {p['agenten']}")
    return "Profiel van de gebruiker (geratificeerd): " + " · ".join(delen)
