"""Automatiek-kern voor GrowKit — inbouw van parvenuprompting/Automatiek.

Het zes-blokken-model letterlijk overgenomen uit de web-app
(types.ts + plan.ts): doel & trigger, bronnen & data, stappen,
kwaliteit & verificatie, planning & uitvoering, randvoorwaarden & privacy.

Huisregels van GrowKit eromheen:
- een plan is `concept` tot alle zes blokken valide zijn (zet_klaar);
- de secrets-scanner uit het taak-contract geldt óók voor plannen —
  authenticatie hoort op de doelmachine, nooit in een plan;
- export naar markdown (mens) en JSON (machine); import leest JSON terug;
- append-only log per actie.

Op de doelmachine: KairOS voert KLAAR-plannen uit via de gewone
wachtrij (gouverneur en faalcontract blijven de bewakers).
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSIE = 1

_TRIGGER_TYPES = ("schema", "webhook", "handmatig", "event")

# secrets-scanner: zelfde patronen als kern/growkit_contract.py
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

_BLOKKEN = (
    ("doel_en_trigger", "Doel & trigger"),
    ("bronnen", "Bronnen & data"),
    ("stappen", "Stappen"),
    ("kwaliteit", "Kwaliteit & verificatie"),
    ("uitvoering", "Planning & uitvoering"),
    ("randvoorwaarden", "Randvoorwaarden & privacy"),
)


def _nu() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _scan(waarde: str) -> str | None:
    for patroon, label in _PATRONEN:
        if patroon.search(waarde):
            return label
    return None


def _heeft_secret(diepte: object) -> str | None:
    """Zoek secrets door het hele blokken-dict (alle strings)."""
    if isinstance(diepte, str):
        return _scan(diepte)
    if isinstance(diepte, dict):
        for v in diepte.values():
            t = _heeft_secret(v)
            if t:
                return t
    if isinstance(diepte, list):
        for v in diepte:
            t = _heeft_secret(v)
            if t:
                return t
    return None


def nieuw_plan(titel: str, *, trigger_type: str = "schema") -> dict:
    """Nieuw plan in concept-status met lege zes blokken."""
    if trigger_type not in _TRIGGER_TYPES:
        raise ValueError(
            f"Onbekend trigger-type '{trigger_type}' — kies uit: "
            + ", ".join(_TRIGGER_TYPES))
    nu = _nu()
    return {
        "id": str(uuid.uuid4()),
        "versie": SCHEMA_VERSIE,
        "titel": titel.strip() or "Naamloos plan",
        "status": "concept",
        "aangemaakt": nu,
        "gewijzigd": nu,
        "blokken": {
            "doel_en_trigger": {"doel": "", "trigger": "",
                                "trigger_type": trigger_type},
            "bronnen": {"diensten": "", "data": "", "authenticatie": ""},
            "stappen": [],
            "kwaliteit": {"verificatie": "", "testaanpak": ""},
            "uitvoering": {"omgeving": "", "planning": "",
                           "faalafhandeling": ""},
            "randvoorwaarden": {"privacy": "", "randgevallen": ""},
        },
    }


def valideer_klaar(plan: dict) -> dict:
    """Mag dit plan naar KLAAR? Alle zes blokken inhoudelijk gevuld,
    elke stap compleet (omschrijving + foutscenario), geen secrets."""
    b = plan.get("blokken", {})
    for sleutel, _ in _BLOKKEN:
        if sleutel not in b:
            return {"geldig": False, "fout": f"Plan mist blok '{sleutel}'."}

    det = b["doel_en_trigger"]
    if not det.get("doel", "").strip():
        return {"geldig": False, "fout": "Blok 01: doel is leeg."}
    if not det.get("trigger", "").strip():
        return {"geldig": False, "fout": "Blok 01: trigger is leeg."}

    bronnen = b["bronnen"]
    for veld in ("diensten", "data", "authenticatie"):
        if not bronnen.get(veld, "").strip():
            return {"geldig": False, "fout": f"Blok 02: '{veld}' is leeg."}

    stappen = b["stappen"]
    if not stappen:
        return {"geldig": False, "fout": "Blok 03: geen stappen."}
    for stap in stappen:
        if not stap.get("omschrijving", "").strip():
            return {"geldig": False,
                    "fout": f"Blok 03: stap {stap.get('nummer', '?')} heeft geen omschrijving."}
        if not stap.get("foutscenario", "").strip():
            return {"geldig": False,
                    "fout": f"Blok 03: stap {stap.get('nummer', '?')} heeft geen foutscenario."}

    for sleutel, velden in (("kwaliteit", ("verificatie", "testaanpak")),
                            ("uitvoering", ("omgeving", "planning",
                                            "faalafhandeling")),
                            ("randvoorwaarden", ("privacy", "randgevallen"))):
        for veld in velden:
            if not b[sleutel].get(veld, "").strip():
                return {"geldig": False,
                        "fout": f"Blok '{sleutel}': '{veld}' is leeg."}

    secret = _heeft_secret(b)
    if secret:
        return {"geldig": False,
                "fout": f"Secret geweigerd in plan: {secret}. "
                        "Authenticatie leg je vast op de doelmachine."}
    return {"geldig": True}


def zet_klaar(plan: dict) -> dict:
    """Concept → klaar; weigert een onvolledig plan (nette ValueError)."""
    r = valideer_klaar(plan)
    if not r["geldig"]:
        raise ValueError(r["fout"])
    plan["status"] = "klaar"
    plan["gewijzigd"] = _nu()
    return plan


# ---------------------------------------------------------------------------
# Opslag (JSON-lijst) + append-only log
# ---------------------------------------------------------------------------

def _opslag_pad() -> Path:
    return Path.home() / ".growkit" / "automatiek" / "plannen.json"


def _log_pad() -> Path:
    return Path.home() / ".growkit" / "automatiek" / "log.json"


def _log(actie: str, detail: dict) -> None:
    pad = _log_pad()
    pad.parent.mkdir(parents=True, exist_ok=True)
    regels = []
    if pad.exists():
        try:
            regels = json.loads(pad.read_text())
        except (json.JSONDecodeError, OSError):
            regels = []
    regels.append({"actie": actie, "tijd": _nu(), **detail})
    pad.write_text(json.dumps(regels, ensure_ascii=False, indent=1))


def _lees_alle() -> list[dict]:
    pad = _opslag_pad()
    if not pad.exists():
        return []
    try:
        return json.loads(pad.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def _schrijf_alle(plannen: list[dict]) -> None:
    pad = _opslag_pad()
    pad.parent.mkdir(parents=True, exist_ok=True)
    pad.write_text(json.dumps(plannen, ensure_ascii=False, indent=1))


def voeg_toe(titel: str, blokken: dict) -> dict:
    """Nieuw plan met gegeven blokken opslaan (status concept of klaar
    na validatie — valide plannen gaan direct naar klaar)."""
    secret = _heeft_secret(blokken)
    if secret:
        raise ValueError(f"Secret geweigerd in plan: {secret}. "
                         "Authenticatie leg je vast op de doelmachine.")
    plan = nieuw_plan(titel)
    plan["blokken"] = blokken
    if valideer_klaar(plan)["geldig"]:
        plan["status"] = "klaar"
    plannen = _lees_alle()
    plannen.append(plan)
    _schrijf_alle(plannen)
    _log("toevoegen", {"id": plan["id"], "titel": plan["titel"],
                       "status": plan["status"]})
    return plan


def lijst() -> list[dict]:
    """Overzicht zonder blokken-inhoud (titel, status, tijden)."""
    return [{"id": p["id"], "titel": p["titel"], "status": p["status"],
             "aangemaakt": p["aangemaakt"], "gewijzigd": p["gewijzigd"]}
            for p in _lees_alle()]


def lees(plan_id: str) -> dict:
    for p in _lees_alle():
        if p["id"] == plan_id:
            return p
    raise ValueError(f"Onbekend plan: {plan_id}")


def bewaar(plan: dict) -> dict:
    """Plan terugwegen (na bewerking of status-wissel)."""
    plannen = _lees_alle()
    for i, p in enumerate(plannen):
        if p["id"] == plan["id"]:
            plan["gewijzigd"] = _nu()
            plannen[i] = plan
            _schrijf_alle(plannen)
            _log("bewaar", {"id": plan["id"], "status": plan["status"]})
            return plan
    raise ValueError(f"Onbekend plan: {plan['id']}")


# ---------------------------------------------------------------------------
# Export / import (zelfde geest als de web-app: markdown voor mensen,
# JSON voor machines)
# ---------------------------------------------------------------------------

def export_markdown(plan: dict) -> str:
    b = plan["blokken"]
    det = b["doel_en_trigger"]
    regels = [
        f"# {plan['titel']}",
        "",
        f"Status: {plan['status']} · schema {plan['versie']}",
        "",
        "## 01 · Doel & trigger",
        f"- Doel: {det.get('doel', '')}",
        f"- Trigger: {det.get('trigger', '')} ({det.get('trigger_type', '')})",
        "",
        "## 02 · Bronnen & data",
        f"- Diensten: {b['bronnen'].get('diensten', '')}",
        f"- Data: {b['bronnen'].get('data', '')}",
        f"- Authenticatie: {b['bronnen'].get('authenticatie', '')}",
        "",
        "## 03 · Stappen",
    ]
    for stap in b["stappen"]:
        regels.append(f"{stap.get('nummer', '?')}. {stap.get('omschrijving', '')}")
        regels.append(f"   - Invoer: {stap.get('invoer', '')}")
        regels.append(f"   - Uitvoer: {stap.get('uitvoer', '')}")
        regels.append(f"   - Foutscenario: {stap.get('foutscenario', '')}")
    regels += [
        "",
        "## 04 · Kwaliteit & verificatie",
        f"- Verificatie: {b['kwaliteit'].get('verificatie', '')}",
        f"- Testaanpak: {b['kwaliteit'].get('testaanpak', '')}",
        "",
        "## 05 · Planning & uitvoering",
        f"- Omgeving: {b['uitvoering'].get('omgeving', '')}",
        f"- Planning: {b['uitvoering'].get('planning', '')}",
        f"- Faalafhandeling: {b['uitvoering'].get('faalafhandeling', '')}",
        "",
        "## 06 · Randvoorwaarden & privacy",
        f"- Privacy: {b['randvoorwaarden'].get('privacy', '')}",
        f"- Randgevallen: {b['randvoorwaarden'].get('randgevallen', '')}",
        "",
    ]
    return "\n".join(regels)


def export_json(plan: dict) -> str:
    return json.dumps(plan, ensure_ascii=False, indent=1)


def import_json(tekst: str) -> dict:
    doc = json.loads(tekst)
    for veld in ("id", "titel", "status", "blokken"):
        if veld not in doc:
            raise ValueError(f"Plan mist verplicht veld '{veld}'.")
    if doc.get("versie") != SCHEMA_VERSIE:
        raise ValueError(f"Onbekende schema-versie: {doc.get('versie')}")
    return doc
