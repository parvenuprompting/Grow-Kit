"""PTS-kern — hash-verankering van kadertests.

Tests zijn wet: elke testbestand krijgt een SHA256-hash die in een
append-only manifest staat. Wijkt de hash af zonder registratie,
dan faalt de harnas-check met TESTGEWIJZIGD ZONDER TOESTEMMING.
Geen auto-reparatie, geen auto-fallback: roep de mens.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

FOUT_GEWIJZIGD = "TESTGEWIJZIGD ZONDER TOESTEMMING"
FOUT_ONGEREGISTREERD = "TEST ONGEREGISTREERD"


def hash_bestand(pad: str | Path) -> str:
    data = Path(pad).read_bytes()
    return hashlib.sha256(data).hexdigest()


def laad_manifest(manifest_pad: str | Path) -> dict:
    """Manifest: {"tests": {"<relatief pad>": {"hash": "...", "geregistreerd": "ISO-datum"}}}

    Corrupt manifest = nette fout (roep de mens), nooit auto-herstel.
    """
    pad = Path(manifest_pad)
    if not pad.exists():
        return {"tests": {}}
    try:
        inhoud = json.loads(pad.read_text(encoding="utf-8"))
        if not isinstance(inhoud, dict) or not isinstance(inhoud.get("tests", {}), dict):
            raise ValueError("manifest-vorm onjuist")
        return inhoud
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Manifest corrupt ({exc}) — roep de mens, nooit auto-repareren.") from exc


def schrijf_manifest(manifest_pad: str | Path, manifest: dict) -> None:
    Path(manifest_pad).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def registreer_test(manifest_pad: str | Path, test_pad: str | Path, basis: str | Path) -> dict:
    """Registreer (of her-registreer na menselijk akkoord) één testbestand."""
    test_pad = Path(test_pad)
    basis = Path(basis)
    if not test_pad.exists():
        raise FileNotFoundError(test_pad)
    rel = str(test_pad.relative_to(basis))
    manifest = laad_manifest(manifest_pad)
    manifest.setdefault("tests", {})[rel] = {
        "hash": hash_bestand(test_pad),
    }
    schrijf_manifest(manifest_pad, manifest)
    return manifest


def check_tests(basis: str | Path, manifest_pad: str | Path) -> dict:
    """Verifieer alle testbestanden onder `basis/kadertests` tegen het manifest.

    Retourneert {"ok": bool, "fouten": [...], "gecontroleerd": N}.
    Append-only lezing; muteert niets.
    """
    basis = Path(basis)
    kadertests = basis / "kadertests"
    manifest = laad_manifest(manifest_pad)
    geregistreerd: dict = manifest.get("tests", {})

    fouten: list[str] = []
    gecontroleerd = 0

    bestaand: set[str] = set()
    if kadertests.exists():
        for pad in sorted(kadertests.rglob("*")):
            if not pad.is_file():
                continue
            rel = str(pad.relative_to(basis))
            bestaand.add(rel)
            gecontroleerd += 1
            if rel not in geregistreerd:
                fouten.append(f"{FOUT_ONGEREGISTREERD}: {rel}")
                continue
            if geregistreerd[rel]["hash"] != hash_bestand(pad):
                fouten.append(f"{FOUT_GEWIJZIGD}: {rel}")

    for rel in sorted(geregistreerd):
        if rel not in bestaand:
            fouten.append(f"VERDWENEN: {rel}")

    return {"ok": not fouten, "fouten": fouten, "gecontroleerd": gecontroleerd}
