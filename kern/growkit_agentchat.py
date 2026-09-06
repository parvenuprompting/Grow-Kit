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


def zuiver_antwoord(tekst: str) -> str:
    """Haal het pure antwoord uit ruwe Hermes CLI-output.

    De poller op de VPS slaat anders de hele terminal-uitvoer op: query-
    echo, init-regels, de ☤ Hermes-box, resume-commando's en sessie-stats.
    Het echte antwoord staat in de box tussen ╭─ en ╰─ (of, zonder box,
    na de init-regels en vóór 'Resume this session with:').
    """
    if not tekst:
        return tekst
    regels = tekst.splitlines()

    # Box gevonden? Neem de inhoud tussen ╭─… en ╰─…
    begin = next((i for i, r in enumerate(regels) if r.lstrip().startswith("╭─")), None)
    eind = next((i for i, r in enumerate(regels) if r.lstrip().startswith("╰─")), None)
    if begin is not None and eind is not None and eind > begin:
        binnen = regels[begin + 1:eind]
        # Legende-regel zoals '⚕ Hermes' of 'Hermes' bovenin de box weg
        binnen = [r for r in binnen
                  if r.strip() and r.strip() != "Hermes"
                  and "⚕" not in r
                  and not r.lstrip().startswith("Query:")
                  and not r.lstrip().startswith("Initializing agent")]
        puur = "\n".join(binnen).strip()
        if puur:
            return puur

    # Geen box: alles vóór 'Resume this session with:' en na de init-regels
    if "Resume this session with:" in tekst:
        tekst = tekst.split("Resume this session with:")[0]
    gestript = [r for r in regels
                if r.strip()
                and not r.lstrip().startswith("Query:")
                and not r.lstrip().startswith("Initializing agent")
                and "─────" not in r
                and not r.lstrip().startswith("hermes ")
                and not r.lstrip().startswith("Session:")
                and not r.lstrip().startswith("Title:")
                and not r.lstrip().startswith("Duration:")
                and not r.lstrip().startswith("Messages:")
                and "⚕" not in r]
    puur = "\n".join(gestript).strip()
    return puur if puur else tekst.strip()


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
    """De gespreksdraad: berichten (bron=agentchat) met hun antwoorden.

    Leest uit ALLE mappen (wachtrij, bezig, afgerond) zodat de poller
    berichten veilig kan verplaatsen zonder de draad te breken.
    """
    agent = agent.strip().lower()
    if agent not in at._AGENTEN:
        return {"ok": False, "fout": f"Onbekende agent '{agent}'."}
    try:
        berichten: dict[str, dict] = {}
        for sub in ("wachtrij", "bezig", "afgerond"):
            berichten.update(_lees_alle(
                ssh=uitvoerder, pad=f"{at.WACHTRIJ_ROOT}/{agent}/{sub}",
                timeout=timeout))
        antwoorden = _lees_alle(ssh=uitvoerder,
                                pad=f"{at.WACHTRIJ_ROOT}/{agent}/antwoorden",
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
