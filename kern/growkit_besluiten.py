"""growkit_besluiten — Slice B: besluiten-tijdlijn (voor de Grow Kit-app).

Bron: /root/.hermes/context/agent-brain/besluiten.md op de VPS.
Regelformaat: [BSL-xxx] Titel | status: <status> | dd-mm-jjjj | bron: inbox/<bestand>

Publieke functies:
- parseer_regel(regel) — één regel naar dict, of None als het geen besluit is
- tijdlijn(tekst, status=None) — alle besluiten, nieuwste datum eerst
"""
import re

PATROON = re.compile(
    r"^\[(BSL-\d+)\]\s*(.+?)\s*\|\s*status:\s*(\S+)\s*\|\s*(\d{2}-\d{2}-\d{4})\s*\|\s*bron:\s*(\S+)\s*$"
)


def parseer_regel(regel: str) -> dict | None:
    m = PATROON.match(regel.strip())
    if not m:
        return None
    return {
        "id": m.group(1),
        "titel": m.group(2),
        "status": m.group(3),
        "datum": m.group(4),
        "bron": m.group(5),
    }


def _datum_sleutel(datum: str) -> str:
    """dd-mm-jjjj → jjjj-mm-dd (sorteerbaar)."""
    d, m, j = datum.split("-")
    return f"{j}-{m}-{d}"


def tijdlijn(tekst: str, status: str | None = None) -> list[dict]:
    """Alle besluiten uit de registertekst, nieuwste datum eerst.
    Herziene regels (zelfde id, nieuwere datum) blijven allebei zichtbaar —
    append-only is de wet van het register."""
    besluiten = []
    for regel in tekst.splitlines():
        d = parseer_regel(regel)
        if d:
            besluiten.append(d)
    if status:
        besluiten = [d for d in besluiten if d["status"] == status]
    besluiten.sort(key=lambda d: _datum_sleutel(d["datum"]), reverse=True)
    return besluiten
