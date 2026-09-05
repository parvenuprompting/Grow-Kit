#!/usr/bin/env python3
"""GrowKit knowledge-graaf (fase A+) — het hele brein als kaart.

Bron: het brein-manifest op de VPS (alle documenten, hun sectie, titel).
Vorm: centrum (de boom) → sectie-hubs → documenten. Elk document is
bereikbaar; klikken opent het document in-app (alleen-lezen).

Dit is bewust géén app-inhoud-mix: de app toont het brein plus de
eigen functies als startpunten in het centrum.
"""
import json
import subprocess

from kern.growkit_verbind import HOST
MANIFEST = "/root/.hermes/context/agent-brain/brein/manifest.json"

# App-functies als vaste startpunten in het centrum
_FUNCTIES = [
    {"id": "fn:agenten", "label": "Agenten", "soort": "functie", "doel": "agenten"},
    {"id": "fn:dialoog", "label": "Dialoog", "soort": "functie", "doel": "dialoog"},
    {"id": "fn:ratificatie", "label": "Ratificatie", "soort": "functie", "doel": "ratificatie"},
    {"id": "fn:planten", "label": "Planten", "soort": "functie", "doel": "planten"},
    {"id": "fn:audit", "label": "Audit", "soort": "functie", "doel": "audit"},
    {"id": "fn:taak", "label": "Taak", "soort": "functie", "doel": "taak"},
]


def _standaard_uitvoerder(commando: list[str], timeout: int) -> tuple[int, str]:
    try:
        p = subprocess.run(commando, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired:
        return 124, ""


def bouw_knopen(manifest: dict) -> dict:
    """Van manifest naar knopen + verbindingen (pure functie, testbaar)."""
    knopen: list[dict] = [{"id": "centrum", "label": "GrowKit", "soort": "centrum"}]
    verbindingen: list[dict] = []

    for f in _FUNCTIES:
        knopen.append({"id": f["id"], "label": f["label"], "soort": "functie"})
        verbindingen.append({"bron": "centrum", "doel": f["id"]})

    hubs: set[str] = set()
    for d in manifest.get("documenten", []):
        pad = d.get("pad", "")
        sectie = d.get("sectie", "?")
        if sectie != "root" and sectie not in hubs:
            hubs.add(sectie)
            knopen.append({"id": f"hub:{sectie}", "label": sectie, "soort": "hub"})
            verbindingen.append({"bron": f"hub:{sectie}", "doel": "centrum"})
        knopen.append({"id": f"doc:{pad}", "label": d.get("titel", pad),
                       "soort": "document", "sectie": sectie, "pad": pad})
        if sectie == "root":
            verbindingen.append({"bron": f"doc:{pad}", "doel": "centrum"})
        else:
            verbindingen.append({"bron": f"doc:{pad}", "doel": f"hub:{sectie}"})

    return {"knopen": knopen, "verbindingen": verbindingen}


def haal_graaf(*, uitvoerder=_standaard_uitvoerder, timeout: int = 30) -> dict:
    """Lees het manifest van de VPS (alleen-lezen) en bouw de graaf."""
    code, uit = uitvoerder(["ssh", "-o", "BatchMode=yes",
                            "-o", f"ConnectTimeout={max(timeout - 5, 5)}",
                            HOST, f"cat {MANIFEST}"], timeout)
    if code != 0:
        return {"ok": False, "fout": "Brein-manifest onbereikbaar — graaf onbekend."}
    try:
        manifest = json.loads(uit)
    except json.JSONDecodeError:
        return {"ok": False, "fout": "Manifest is geen geldige JSON — roep de mens."}
    graaf = bouw_knopen(manifest)
    return {"ok": True, "data": graaf}


def lees_document(pad: str, *, uitvoerder=_standaard_uitvoerder,
                  timeout: int = 20) -> dict:
    """Eén document ophalen (alleen-lezen) voor de in-app lezer."""
    if not pad or ".." in pad or pad.startswith("/"):
        return {"ok": False, "fout": "Ongeldig documentpad."}
    basis = MANIFEST.rsplit("/", 1)[0]  # .../agent-brain/brein → brein
    doc_pad = f"{basis}/../{pad}" if not pad.startswith("brein/") else f"{basis}/{pad}"
    code, uit = uitvoerder(["ssh", "-o", "BatchMode=yes",
                            "-o", f"ConnectTimeout={max(timeout - 5, 5)}",
                            HOST, f"cat {doc_pad}"], timeout)
    if code != 0:
        return {"ok": False, "fout": f"Document niet gelezen: {pad}"}
    return {"ok": True, "data": {"pad": pad, "inhoud": uit[:60000]}}
