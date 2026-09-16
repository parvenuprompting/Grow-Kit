"""GrowKit Skills-beheer fase A2 (ZT-7) — view-model voor het
skills-scherm (lijst + monospace-weergave).

Voedt het SwiftUI-scherm op basis van de A1-kern
(`kern/growkit_skills.py`, adapter-commando's `skillslijst` /
`skillslees` / `skillsschrijf`). Geen Swift-logica hier — alleen
data en regels, getest in Python.

Regels:
- lijst is altijd alfabetisch gesorteerd en negeert mappen zonder
  SKILL.md (append-only geest: niets gewist, alleen gelezen);
- laad_inhoud() splitst frontmatter van body; onbestaand pad is een
  nette fout, geen crash;
- vergelijk() is een minimale tekstvergelijking (oud/nieuw onder
  elkaar, verwijderde/veranderde regels gemarkeerd) — geen diff-UI;
- schrijven gaat altíjd via de A1-validatie (valideer) — inhoud met
  een secrets-patroon wordt geweigerd vóór er ook maar iets op schijf
  belandt.
"""
from __future__ import annotations

import os
from difflib import SequenceMatcher

from kern import growkit_skills as sk


def laad_lijst(*, bronnen: dict | None = None) -> list[dict]:
    """Sorteerbare lijst van skills: {naam, bron, pad}, alfabetisch."""
    uit: list[dict] = []
    for bron_id, spec in (bronnen or sk.STANDAARD_BRONNEN).items():
        pad = spec["pad"]
        if not os.path.isdir(pad):
            continue
        for naam in os.listdir(pad):
            bestand = os.path.join(pad, naam, "SKILL.md")
            if os.path.isfile(bestand):
                uit.append({"naam": naam, "bron": bron_id, "pad": bestand})
    return sorted(uit, key=lambda s: s["naam"])


def laad_inhoud(pad: str) -> dict:
    """SKILL.md gesplitst in frontmatter en body; nette fout als het
    bestand niet bestaat (geen crash)."""
    if not os.path.isfile(pad):
        return {"fout": "skill niet gevonden: " + pad}
    with open(pad, encoding="utf-8") as f:
        inhoud = f.read()
    frontmatter = ""
    body = inhoud
    if inhoud.lstrip().startswith("---"):
        delen = inhoud.split("---", 2)
        frontmatter = delen[1].strip() if len(delen) >= 2 else ""
        body = delen[2].lstrip("\n") if len(delen) >= 3 else ""
    return {"frontmatter": frontmatter, "body": body}


def vergelijk(oud: str, nieuw: str) -> list[dict]:
    """Minimale tekstvergelijking: verwijderde en veranderde regels
    gemarkeerd als [{'type': 'verwijderd'|'nieuw', 'regel': str}]."""
    uit: list[dict] = []
    sm = SequenceMatcher(a=oud.splitlines(), b=nieuw.splitlines())
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            for regel in oud.splitlines()[i1:i2]:
                uit.append({"type": "verwijderd", "regel": regel})
        if tag in ("insert", "replace"):
            for regel in nieuw.splitlines()[j1:j2]:
                uit.append({"type": "nieuw", "regel": regel})
    return uit


def schrijf(bron: str, naam: str, inhoud: str, *,
            bronnen: dict | None = None) -> dict:
    """Schrijven via de A1-kern, mét validatie. Secrets of ongeldige
    inhoud worden geweigerd vóór er iets op schijf belandt."""
    ok, melding = sk.valideer(inhoud)
    if not ok:
        return {"ok": False, "fout": melding}
    resultaat = sk.schrijf(bron, naam, inhoud, bronnen=bronnen)
    return {"ok": True, "pad": resultaat["pad"],
            "backup": resultaat.get("backup")}
