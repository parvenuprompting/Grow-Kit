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


def redenatie_uit(tekst: str) -> str | None:
    """Haal het denkproces (redenatie) uit ruwe Hermes CLI-output.

    Dat is alles vóór het antwoordblok: de query-echo, de init-regels en
    vooral de inhoud van de ☤ Hermes-box vóór het antwoord. Voor berichten
    zonder box is er meestal geen zichtbare redenatie → None.
    """
    if not tekst:
        return None
    regels = tekst.splitlines()
    begin = next((i for i, r in enumerate(regels) if r.lstrip().startswith("╭─")), None)
    eind = next((i for i, r in enumerate(regels) if r.lstrip().startswith("╰─")), None)
    if begin is None:
        # Geen box: redenatie = init-regels vóór het eerste antwoordblok,
        # als die er zijn
        kop = [r for r in regels
               if r.lstrip().startswith(("Query:", "Initializing agent"))
               or "─────" in r]
        red = "\n".join(kop).strip()
        return red or None
    binnen = regels[begin + 1:eind if eind and eind > begin else len(regels)]
    binnen = [r for r in binnen
              if r.strip() and "⚕" not in r]
    red = "\n".join(binnen).strip()
    return red or None


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

    # Box gevonden? Het antwoord staat búiten de box (na ╰─…); de inhoud
    # binnenin is het denkproces.
    begin = next((i for i, r in enumerate(regels) if r.lstrip().startswith("╭─")), None)
    eind = next((i for i, r in enumerate(regels) if r.lstrip().startswith("╰─")), None)
    if begin is not None and eind is not None and eind > begin:
        na_box = [r for r in regels[eind + 1:]
                  if r.strip()
                  and not r.lstrip().startswith("Resume this session with:")
                  and not r.lstrip().startswith("hermes ")
                  and not r.lstrip().startswith(("Session:", "Title:", "Duration:", "Messages:"))]
        puur = "\n".join(na_box).strip()
        if puur:
            return puur

    # Geen box: alles vóór 'Resume this session with:' en na de init-regels
    regels = [r for r in tekst.splitlines()
              if not r.lstrip().startswith("Resume this session with:")]
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


def stuur(agent: str, tekst: str, *, van: str = "",
          uitvoerder=at._standaard_uitvoerder,
          timeout: int = 20) -> dict:
    """Chatbericht → wachtrij van de agent (bron=agentchat).

    `van` = naam van de mens die praat; de agent weet dan wie hem
    aanspreekt, wat ook de TITULATUUR-regel in de SOUL ondersteunt.
    """
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
                       van=van.strip(),
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
    """Alles onder pad in ÉÉN SSH-roundtrip: find + cat + scheidingsmarker.

    Voorheen één SSH-call per bestand — bij 20 berichten 20 roundtrips
    van elk ~0,5s. Nu: één commando, bestanden gescheiden door een
    unieke marker-regel zodat JSON-multilines veilig blijven.
    """
    marker = "===GROWKIT_BESTAND==="
    script = ('for f in ' + pad + '/*.json; do '
              '[ -f "$f" ] || continue; '
              'echo "' + marker + '"; echo "FILE:$f"; cat "$f"; done 2>/dev/null')
    code, uit = ssh(["ssh", "-o", "BatchMode=yes",
                     "-o", f"ConnectTimeout={max(timeout - 5, 5)}",
                     at.HOST, script], None, timeout)
    if code == 255:
        raise ConnectionError("VPS onbereikbaar")
    if code != 0:
        return {}

    resultaat: dict[str, dict] = {}
    blokken = uit.split(marker)
    for blok in blokken:
        blok = blok.strip("\n")
        if not blok:
            continue
        regels = blok.splitlines()
        if not regels or not regels[0].startswith("FILE:"):
            continue
        naam = regels[0][5:].strip().split("/")[-1]
        inhoud = "\n".join(regels[1:])
        try:
            resultaat[naam] = json.loads(inhoud)
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
            "van": doc.get("van", ""),
            "antwoord": (antwoord_doc or {}).get("antwoord"),
            "redenatie": (antwoord_doc or {}).get("redenatie"),
            "antwoord_tijd": (antwoord_doc or {}).get("afgerond_op"),
        })
    thread.sort(key=lambda x: x["tijd"])
    return {"ok": True, "data": {"agent": agent, "draad": thread}}


# ---------------------------------------------------------------------------
# Geschiedenis: wissen = naar archief; archief lezen; archief definitief weg
# ---------------------------------------------------------------------------

def wis_draad(agent: str, *, uitvoerder=at._standaard_uitvoerder,
              timeout: int = 25) -> dict:
    """Wis de zichtbare chat: alle agentchat-berichten (wachtrij/bezig/
    afgerond + antwoorden) gaan naar <agent>/geschiedenis/. Niets gaat
    verloren — dit is de leesweergave leegmaken, niet verwijderen."""
    agent = agent.strip().lower()
    if agent not in at._AGENTEN:
        return {"ok": False, "fout": f"Onbekende agent '{agent}'."}
    basis = f"{at.WACHTRIJ_ROOT}/{agent}"
    script = (
        f"mkdir -p {basis}/geschiedenis && "
        f"for sub in wachtrij bezig afgerond; do "
        f"  for f in {basis}/$sub/*.json; do "
        f'    [ -f "$f" ] || continue; '
        f'    grep -q \'"bron": "agentchat"\' "$f" 2>/dev/null && '
        f"    mv \"$f\" {basis}/geschiedenis/ ; "
        f"  done; done; "
        f"for f in {basis}/antwoorden/*.json; do "
        f'  [ -f "$f" ] || continue; '
        f'  bn=$(basename "$f"); mv "$f" {basis}/geschiedenis/antwoord-"$bn" ; '
        f"done; echo OK"
    )
    code, _ = uitvoerder(["ssh", "-o", "BatchMode=yes",
                          "-o", f"ConnectTimeout={max(timeout - 5, 5)}",
                          at.HOST, script], None, timeout)
    if code == 255:
        return {"ok": False, "fout": "VPS onbereikbaar — niets gewist."}
    if code != 0:
        return {"ok": False, "fout": "Wissen mislukt op de VPS."}
    return {"ok": True, "data": {"agent": agent, "gewist": True}}


def geschiedenis(agent: str, *, uitvoerder=at._standaard_uitvoerder,
                 timeout: int = 25) -> dict:
    """De gearchiveerde sessie: berichten + antwoorden, alleen-lezen."""
    agent = agent.strip().lower()
    if agent not in at._AGENTEN:
        return {"ok": False, "fout": f"Onbekende agent '{agent}'."}
    try:
        berichten = _lees_alle(ssh=uitvoerder,
                               pad=f"{at.WACHTRIJ_ROOT}/{agent}/geschiedenis",
                               timeout=timeout)
    except ConnectionError:
        return {"ok": False, "fout": "VPS onbereikbaar — geschiedenis onbekend."}

    thread: list[dict] = []
    antwoorden = {n[len("antwoord-"):]: d for n, d in berichten.items()
                  if n.startswith("antwoord-")}
    for naam, doc in berichten.items():
        if doc.get("bron") != "agentchat" or naam.startswith("antwoord-"):
            continue
        taak_id = doc.get("taak_id", naam)
        antw = antwoorden.get(f"{taak_id}.json")
        thread.append({
            "taak_id": taak_id,
            "bericht": doc.get("titel", ""),
            "tijd": doc.get("aangemeld_op", ""),
            "van": doc.get("van", ""),
            "antwoord": (antw or {}).get("antwoord"),
            "redenatie": (antw or {}).get("redenatie"),
        })
    thread.sort(key=lambda x: x["tijd"])
    return {"ok": True, "data": {"agent": agent, "geschiedenis": thread}}


def wis_geschiedenis(agent: str, *, bevestig: bool = False,
                     uitvoerder=at._standaard_uitvoerder,
                     timeout: int = 25) -> dict:
    """DEFINITIEF wissen van de gearchiveerde sessie. Vereist
    bevestig=True — zonder die vlag gebeurt er niets (faalcontract)."""
    agent = agent.strip().lower()
    if agent not in at._AGENTEN:
        return {"ok": False, "fout": f"Onbekende agent '{agent}'."}
    if not bevestig:
        return {"ok": False,
                "fout": "Definitief wissen vereist bevestiging (bevestig=true)."}
    script = (f"rm -f {at.WACHTRIJ_ROOT}/{agent}/geschiedenis/*.json && echo OK")
    code, _ = uitvoerder(["ssh", "-o", "BatchMode=yes",
                          "-o", f"ConnectTimeout={max(timeout - 5, 5)}",
                          at.HOST, script], None, timeout)
    if code == 255:
        return {"ok": False, "fout": "VPS onbereikbaar — niets gewist."}
    if code != 0:
        return {"ok": False, "fout": "Verwijderen mislukt op de VPS."}
    return {"ok": True, "data": {"agent": agent, "definitief_gewist": True}}
