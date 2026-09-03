"""GrowKit bewijs-controles — machine-toetsbaar, nooit zelf-gerapporteerd.

Elke functie voert precies één gecodeerde check uit. Geen enkele check
vertrouwt op interpretatie van agent-output.
"""
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

BEWIJS_TYPES = {"shell_check", "http_check", "file_exists", "json_valid", "file_equals"}


def _shell_check(bewijs: dict, doel: Path, **_) -> tuple[bool, str]:
    resultaat = subprocess.run(bewijs["commando"], shell=True, cwd=doel,
                               capture_output=True, text=True, timeout=60)
    tekst = resultaat.stdout + resultaat.stderr
    geslaagd = bewijs["verwacht_substr"] in tekst
    return geslaagd, f"shell_check: zocht '{bewijs['verwacht_substr']}', kreeg: {tekst.strip()[:200]!r}"


def _http_check(bewijs: dict, doel: Path, **_) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(bewijs["url"], timeout=10) as r:
            status = r.status
    except Exception as e:  # ook HTTP-fouten (404 e.d.) vallen hieronder
        return False, f"http_check: {bewijs['url']} faalde: {e}"
    return status == bewijs["verwacht_status"], f"http_check: {bewijs['url']} -> {status}"


def _file_exists(bewijs: dict, doel: Path, **_) -> tuple[bool, str]:
    bestand = doel / bewijs["pad"]
    if not bestand.exists():
        return False, f"file_exists: {bewijs['pad']} bestaat niet"
    if "bevat" in bewijs and bewijs["bevat"] not in bestand.read_text(encoding="utf-8"):
        return False, f"file_exists: {bewijs['pad']} bevat niet {bewijs['bevat']!r}"
    return True, f"file_exists: {bewijs['pad']} OK"


def _json_valid(bewijs: dict, doel: Path, **_) -> tuple[bool, str]:
    try:
        with open(doel / bewijs["pad"], encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return False, f"json_valid: {bewijs['pad']} is geen valide JSON: {e}"
    if "top_level" in bewijs:
        verwacht = list if bewijs["top_level"] == "array" else dict
        if not isinstance(data, verwacht):
            return False, f"json_valid: top-level is geen {bewijs['top_level']}"
    if "exacte_lengte" in bewijs and len(data) != bewijs["exacte_lengte"]:
        return False, f"json_valid: lengte {len(data)} != {bewijs['exacte_lengte']}"
    if "verplicht_veld" in bewijs:
        items = data if isinstance(data, list) else [data]
        if not all(bewijs["verplicht_veld"] in item for item in items):
            return False, f"json_valid: veld {bewijs['verplicht_veld']!r} ontbreekt"
    return True, f"json_valid: {bewijs['pad']} OK"


def _file_equals(bewijs: dict, doel: Path, sjablonen_map: Path | None = None, **_) -> tuple[bool, str]:
    if sjablonen_map is None:
        return False, "file_equals: geen sjablonenmap meegegeven"
    sjabloon = sjablonen_map / bewijs["sjabloon"]
    bestand = doel / bewijs["pad"]
    if not sjabloon.exists() or not bestand.exists():
        return False, f"file_equals: {bewijs['sjabloon']} of {bewijs['pad']} bestaat niet"
    h1 = hashlib.sha256(sjabloon.read_bytes()).hexdigest()
    h2 = hashlib.sha256(bestand.read_bytes()).hexdigest()
    return h1 == h2, f"file_equals: {bewijs['pad']} {'=' if h1 == h2 else '!='} sjabloon"


_CONTROLES = {
    "shell_check": _shell_check,
    "http_check": _http_check,
    "file_exists": _file_exists,
    "json_valid": _json_valid,
    "file_equals": _file_equals,
}


def controleer(bewijs: dict, doel: Path, sjablonen_map: Path | None = None) -> tuple[bool, str]:
    """Voer één gecodeerde bewijscheck uit. Retourneert (geslaagd, bewijstekst)."""
    soort = bewijs.get("type")
    if soort not in BEWIJS_TYPES:
        return False, f"onbekend bewijstype: {soort!r} (geldige types: {sorted(BEWIJS_TYPES)})"
    return _CONTROLES[soort](bewijs, doel, sjablonen_map=sjablonen_map)
