"""RAM-detectie + model-manifest voor CyberSeed (kern/data/cyberseed_models.json).

Leest sysctl hw.memsize (macOS) en koppelt aan RAM-klassen. De mapping
lokaal/cloud staat in een los manifest — bij te werken zonder app-release.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

_KLASSEN = [
    ("8-15", 8),
    ("16-23", 16),
    ("24-36", 24),
    ("48-64", 48),
    ("96+", 96),
]

_MANIFEST_PAD = Path(__file__).resolve().parent.parent / "kern" / "data" / "cyberseed_models.json"


def ram_gb() -> float:
    """Totaal unified memory in GB (macOS: sysctl hw.memsize)."""
    try:
        uit = subprocess.run(["sysctl", "-n", "hw.memsize"],
                             capture_output=True, text=True, timeout=5)
        return round(int(uit.stdout.strip()) / 1024**3)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0.0


def ram_klasse(gb: float | None = None) -> str:
    """Klasse waar het geheugen in past; onder 8 GB valt terug op '8-15'
    (alle namen worden daar vergrendeld door de mapping)."""
    gb = ram_gb() if gb is None else gb
    huidige = "8-15"
    for naam, onder in _KLASSEN:
        if gb >= onder:
            huidige = naam
    return huidige


def manifest() -> dict:
    try:
        return json.loads(_MANIFEST_PAD.read_text())
    except (OSError, json.JSONDecodeError):
        return {"versie": 0, "lokaal": {}, "cloud": {}, "namen": {}}


def model_voor(klasse: str, naam: str) -> str | None:
    """Lokaal model voor (klasse, naam); None = vergrendeld."""
    return manifest().get("lokaal", {}).get(klasse, {}).get(naam)


def is_vergrendeld(klasse: str, naam: str) -> bool:
    return model_voor(klasse, naam) is None


def min_ram_gb(naam: str) -> int:
    """Laagste RAM-grens waarop de naam beschikbaar wordt."""
    for klasse, onder in _KLASSEN:
        if not is_vergrendeld(klasse, naam):
            return onder
    return _KLASSEN[0][1]  # zou niet gebeuren (sprout is er altijd)


def cloud_model_voor(naam: str) -> str:
    return manifest().get("cloud", {}).get(naam, "")
