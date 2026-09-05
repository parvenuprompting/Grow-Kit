#!/usr/bin/env python3
"""GrowKit agentcontrole (slice D) — de rondte: ophalen wat af is, uitspraak doen.

Mappen per agent op de VPS:
  wachtrij/    → GrowKit legt taken neer (slice C)
  afgerond/    → agent legt een afgeronde taak met bewijs neer
  controle/    → GrowKit haalt afgeronde taken hierheen voor de mens
  goedgekeurd/ → na goedkeuring van de mens
  afgekeurd/   → na afkeuring van de mens

Alleen mv + cat + ls: geen andere operaties, geen shell-constructie met
taakinhoud. De gouverneur-kern blijft de machthebber over aantallen.
"""
import json
import re
import subprocess

HOST = "root@168.119.248.208"
WACHTRIJ_ROOT = "/root/.hermes/agenttaken"
_AGENTEN = {"kairos", "riri", "vigil", "libra", "memoria", "codex", "genius"}
_W = WACHTRIJ_ROOT
_BESTAND = re.compile(r"^[\w-]+\.json$")


def _standaard_uitvoerder(commando: list[str], stdin: str | None,
                          timeout: int) -> tuple[int, str]:
    try:
        p = subprocess.run(commando, input=stdin, capture_output=True, text=True,
                           timeout=timeout)
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired:
        return 124, ""


def _ssh(commando: str, *, uitvoerder, timeout: int) -> tuple[int, str]:
    return uitvoerder(["ssh", "-o", "BatchMode=yes",
                       "-o", f"ConnectTimeout={max(timeout - 5, 5)}",
                       HOST, commando], None, timeout)


def ophalen(*, uitvoerder=_standaard_uitvoerder, timeout: int = 20) -> dict:
    """Lees afgerond/*.json van alle agents, verplaats naar controle/."""
    code, uit = _ssh(f"ls {_W}/*/afgerond/*.json 2>/dev/null",
                     uitvoerder=uitvoerder, timeout=timeout)
    if code not in (0, 2):
        return {"ok": False, "fout": "VPS onbereikbaar — controle onbekend."}

    afgerond: list[dict] = []
    for pad in [l.strip() for l in uit.splitlines() if l.strip()]:
        delen = pad.split("/")
        if len(delen) < 3 or delen[-3] != _W.lstrip("/").split("/")[0]:
            pass  # padvorm strikt: /root/.hermes/agenttaken/<agent>/afgerond/<id>.json
        agent = pad.split("/")[-3]
        naam = pad.split("/")[-1]
        if agent not in _AGENTEN or not _BESTAND.match(naam):
            continue
        c, doc = _ssh(f"cat {pad}", uitvoerder=uitvoerder, timeout=timeout)
        if c != 0:
            continue
        try:
            item = json.loads(doc)
        except json.JSONDecodeError:
            item = {"taak_id": naam[:-5], "agent": agent,
                    "fout": "taakdocument is geen geldige JSON"}
        c2, _ = _ssh(f"mv {pad} {_W}/{agent}/controle/{naam}",
                     uitvoerder=uitvoerder, timeout=timeout)
        if c2 == 0:
            afgerond.append(item)

    return {"ok": True, "data": {"afgerond": afgerond}}


def besluit(agent: str, taak_id: str, *, goed: bool,
            uitvoerder=_standaard_uitvoerder, timeout: int = 20) -> dict:
    """Mens-uitspraak: verplaats controle/<id>.json naar de juiste map."""
    agent = agent.strip().lower()
    taak_id = taak_id.strip()
    if agent not in _AGENTEN:
        return {"ok": False, "fout": f"Onbekende agent '{agent}'."}
    if not _BESTAND.match(taak_id + ".json"):
        return {"ok": False, "fout": "Ongeldige taak-id."}
    bestemming = "goedgekeurd" if goed else "afgekeurd"
    bron = f"{_W}/{agent}/controle/{taak_id}.json"
    doel = f"{_W}/{agent}/{bestemming}/{taak_id}.json"
    code, _ = _ssh(f"mv {bron} {doel}", uitvoerder=uitvoerder, timeout=timeout)
    if code != 0:
        return {"ok": False, "fout": f"Taakbestand niet gevonden in controle/ van {agent}."}
    return {"ok": True, "data": {"agent": agent, "taak_id": taak_id,
                                 "besluit": bestemming}}
