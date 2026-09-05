#!/usr/bin/env python3
"""GrowKit observaties (slice E) — Genius' voorstellen uit de brein-inbox.

Alleen-lezen: ls + cat op /root/.hermes/context/agent-brain/inbox/.
Geen mutaties — curatie (boeken/verwerpen) blijft in het brein bij de
mens, conform de tweede-brein-werkwijze.
"""
import json
import re
import subprocess

HOST = "root@168.119.248.208"
INBOX = "/root/.hermes/context/agent-brain/inbox"


def _standaard_uitvoerder(commando: list[str], stdin, timeout) -> tuple[int, str]:
    try:
        p = subprocess.run(commando, input=stdin, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired:
        return 124, ""


def _ssh(commando: str, *, uitvoerder, timeout: int) -> tuple[int, str]:
    return uitvoerder(["ssh", "-o", "BatchMode=yes",
                       "-o", f"ConnectTimeout={max(timeout - 5, 5)}",
                       HOST, commando], None, timeout)


_TITEL = re.compile(r'^titel:\s*"?(.+?)"?\s*$', re.M)
_AFZENDER = re.compile(r"^afzender:\s*(\S+)", re.M)


def lees(*, uitvoerder=_standaard_uitvoerder, timeout: int = 20,
         maximum: int = 20) -> dict:
    code, uit = _ssh(f"ls {INBOX}/*.md 2>/dev/null",
                     uitvoerder=uitvoerder, timeout=timeout)
    if code not in (0, 2):
        return {"ok": False, "fout": "Brein-inbox onbereikbaar."}

    voorstellen: list[dict] = []
    for pad in [l.strip() for l in uit.splitlines() if l.strip()][-maximum:]:
        c, doc = _ssh(f"cat {pad}", uitvoerder=uitvoerder, timeout=timeout)
        if c != 0:
            continue
        naam = pad.split("/")[-1]
        mt = _TITEL.search(doc)
        ma = _AFZENDER.search(doc)
        inhoud = doc.split("---", 2)[-1].strip() if doc.startswith("---") else doc
        voorstellen.append({
            "bestand": naam,
            "titel": (mt.group(1) if mt else naam),
            "afzender": (ma.group(1) if ma else "onbekend"),
            "inhoud": inhoud[:1500],
        })
    return {"ok": True, "data": {"voorstellen": voorstellen}}
