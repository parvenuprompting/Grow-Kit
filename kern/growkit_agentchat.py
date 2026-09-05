#!/usr/bin/env python3
"""GrowKit agentchat (ronde 3) — praten met de familie.

Een chatbericht is een taak met bron='agentchat': hij reist via de
bewezen wachtrij (gouverneur, één poort, JSON via stdin) naar de VPS.
De poller op de VPS voert hem uit met het profiel van de agent en zet
het antwoord in antwoorden/. De draad hier leest alleen (ls + cat).

De secrets-scanner geldt óók voor chatberichten.
"""
import json
import re
from datetime import datetime, timezone

from kern import growkit_agenttaak as at

_ANTWOORDEN_ROOT = at.WACHTRIJ_ROOT  # zelfde boom: <agent>/antwoorden/


def _scan_tekst(tekst: str) -> str | None:
    """Dezelfde secret-patronen als het taak-contract, voor chatberichten."""
    from kern.growkit_contract import _PATRONEN as contract_patronen
    for patroon, label in contract_patronen:
        if patroon.search(tekst):
            return label
    return None


def stuur(agent: str, tekst: str, *, uitvoerder=at._standaard_uitvoerder,
          timeout: int = 20) -> dict:
    """Chatbericht → wachtrij van de agent (bron=agentchat)."""
    if not tekst.strip():
        return {"ok": False, "fout": "Een leeg bericht kan niemand bereiken."}
    treffer = _scan_tekst(tekst)
    if treffer:
        return {"ok": False, "fout":
                f"Secret geweigerd in chatbericht: {treffer}. "
                "Authenticatie hoort op de doelmachine."}
    taak_id = "chat-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")[:-3]
    return at.verstuur(agent, taak_id, tekst.strip(),
                       contract={"blokken": []},   # bron=agentchat, geen contract
                       uitvoerder=_stuur_uitvoerder(uitvoerder), timeout=timeout)


def _stuur_uitvoerder(uitvoerder):
    """Zet bron=agentchat in het document vóór verzending."""
    def met_bron(commando, stdin, timeout):
        if stdin:
            try:
                doc = json.loads(stdin)
                doc["bron"] = "agentchat"
                stdin = json.dumps(doc, ensure_ascii=False)
            except json.JSONDecodeError:
                pass
        return uitvoerder(commando, stdin, timeout)
    return met_bron


def _lees_alle(ssh, pad: str, timeout: int) -> dict[str, dict]:
    """ls + cat: alles onder pad. SSH-code 255 = echte verbindingfout."""
    code, uit = ssh(["ssh", "-o", "BatchMode=yes",
                     "-o", f"ConnectTimeout={max(timeout - 5, 5)}",
                     at.HOST, f"ls {pad}/*.json 2>/dev/null"], None, timeout)
    if code == 255:
        raise ConnectionError("VPS onbereikbaar")
    if code != 0:
        return {}
    resultaat: dict[str, dict] = {}
    for bestand in [l.strip() for l in uit.splitlines() if l.strip()]:
        naam = bestand.split("/")[-1]
        c, doc = ssh(["ssh", "-o", "BatchMode=yes", at.HOST, f"cat {bestand}"],
                     None, timeout)
        if c == 0:
            try:
                resultaat[naam] = json.loads(doc)
            except json.JSONDecodeError:
                resultaat[naam] = {"fout": "onleesbaar document"}
    return resultaat


def draad(agent: str, *, uitvoerder=at._standaard_uitvoerder,
          timeout: int = 25) -> dict:
    """De gespreksdraad: berichten (bron=agentchat) met hun antwoorden."""
    agent = agent.strip().lower()
    if agent not in at._AGENTEN:
        return {"ok": False, "fout": f"Onbekende agent '{agent}'."}
    try:
        berichten = _lees_alle(ssh=uitvoerder, pad=f"{at.WACHTRIJ_ROOT}/{agent}/wachtrij",
                               timeout=timeout)
        berichten.update(_lees_alle(ssh=uitvoerder, pad=f"{at.WACHTRIJ_ROOT}/{agent}/bezig",
                                    timeout=timeout))
        antwoorden = _lees_alle(ssh=uitvoerder, pad=f"{at.WACHTRIJ_ROOT}/{agent}/antwoorden",
                                timeout=timeout)
    except ConnectionError:
        return {"ok": False, "fout": "VPS onbereikbaar — draad onbekend."}

    thread: list[dict] = []
    for naam, doc in berichten.items():
        if doc.get("bron") != "agentchat":
            continue
        taak_id = doc.get("taak_id", naam)
        antwoord_doc = antwoorden.get(f"{taak_id}.json")
        thread.append({
            "taak_id": taak_id,
            "bericht": doc.get("titel", ""),
            "tijd": doc.get("aangemeld_op", ""),
            "antwoord": (antwoord_doc or {}).get("antwoord"),
            "antwoord_tijd": (antwoord_doc or {}).get("afgerond_op"),
        })
    thread.sort(key=lambda x: x["tijd"])
    return {"ok": True, "data": {"agent": agent, "draad": thread}}
