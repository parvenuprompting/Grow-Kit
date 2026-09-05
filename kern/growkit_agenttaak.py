#!/usr/bin/env python3
"""GrowKit agenttaak (slice C) — taak van de Mac naar de wachtrij van een agent.

Eén richting, één poort: GrowKit schrijft uitsluitend taakbestanden in
/root/.hermes/agenttaken/<agent>/wachtrij/ op de VPS. Geen andere paden,
geen shell-constructie met taakinhoud — de JSON reist via stdin.

De gouverneur-kern (growkit_agents.py) blijft de machthebber over
hoeveelheden; deze module bedient alleen het transport.
"""
import json
import re
import subprocess
from datetime import datetime, timezone

HOST = "root@168.119.248.208"
WACHTRIJ_ROOT = "/root/.hermes/agenttaken"
# alleen bekende familieleden; gelijk aan het familie-register
_AGENTEN = {"kairos", "riri", "vigil", "libra", "memoria", "codex", "genius"}
# taak-id: letters, cijfers, streepjes en lage streepjes — niets anders
_TAAKID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _standaard_uitvoerder(commando: list[str], stdin: str | None,
                          timeout: int) -> tuple[int, str]:
    try:
        p = subprocess.run(commando, input=stdin, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired:
        return 124, ""


def verstuur(agent: str, taak_id: str, titel: str, *,
             contract: dict | None = None,
             uitvoerder=_standaard_uitvoerder, timeout: int = 20) -> dict:
    agent = agent.strip().lower()
    taak_id = taak_id.strip()
    if agent not in _AGENTEN:
        return {"ok": False, "fout": f"Onbekende agent '{agent}' — de familie is wie hij is."}
    if not _TAAKID.match(taak_id):
        return {"ok": False, "fout": "Taak-id mag alleen letters, cijfers, - en _ bevatten."}
    if not titel.strip():
        return {"ok": False, "fout": "Een taak zonder titel kan niemand opvallen."}

    document = {
        "taak_id": taak_id,
        "agent": agent,
        "titel": titel,
        "bron": "growkit-ui",
        "aangemeld_op": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if contract:
        document["contract"] = contract
    doel = f"{WACHTRIJ_ROOT}/{agent}/wachtrij/{taak_id}.json"
    commando = ["ssh", "-o", "BatchMode=yes",
                "-o", f"ConnectTimeout={max(timeout - 5, 5)}",
                HOST,
                "umask 177; cat > " + doel + ".deel && mv " + doel + ".deel " + doel]
    code, _ = uitvoerder(commando, json.dumps(document, ensure_ascii=False), timeout)
    if code != 0:
        return {"ok": False, "fout": "VPS-wachtrij onbereikbaar — taak niet verstuurd."}
    return {"ok": True, "data": {"bestand": doel, "agent": agent,
                                 "taak_id": taak_id}}
