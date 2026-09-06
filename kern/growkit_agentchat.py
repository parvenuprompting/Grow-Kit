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




# Engelse meta-regels waaraan we "dit is nog hardop-denken" herkennen.
# Het model denkt in het Engels en antwoordt in de taal van de gebruiker;
# daardoor is de taalwissel EN→NL een betrouwbare grens.
_DENK_MARKERS = (
    "the user", "let me", "i should", "i'll ", "i will ", "this is a test",
    "i need to", "i think", "it seems", "probably", "meaning ",
    "since this is", "given that", "keep it short", "respond briefly",
    "in other words", "so the answer", "first,", "second,", "okay,",
)


def _regels_zijn_nederlands(regels: list[str]) -> bool:
    """Heuristiek: minstens de helft van de niet-lege regels bevat typisch
    Nederlandse woorden/tekens die in Engelse meta-tekst zeldzaam zijn."""
    nl_hint = re.compile(
        r"\b(de|het|een|van|is|dat|niet|je|zij|we|voor|met|na|ook|maar|"
        r"bij|uit|al|nog|wel|zijn|word|wordt|mijn|onze|daar|dit|die)\b",
        re.I)
    echte = [r for r in regels if r.strip()]
    if not echte:
        return False
    treffers = sum(1 for r in echte if nl_hint.search(r))
    return treffers >= max(1, len(echte) // 2)


def splits_antwoord_redenatie(tekst: str) -> tuple[str | None, str]:
    """Scheid redenatie (hardop-denken) van het zuivere antwoord.

    Volgorde van herkenning:
    1. Hermes-box: inhoud binnen de box = redenatie, alles erna = antwoord.
    2. Geen box: zoek de LAATSTE overgang van Engelse meta-regels naar een
       aaneengesloten Nederlands eindblok; dat eindblok is het antwoord,
       alles ervoor is redenatie.
    3. Geen wissel gevonden: alles is antwoord, redenatie None.
    """
    if not tekst or not tekst.strip():
        return None, tekst or ""

    regels = tekst.splitlines()

    # 1) box
    begin = next((i for i, r in enumerate(regels)
                  if r.lstrip().startswith("╭─")), None)
    eind = next((i for i, r in enumerate(regels)
                 if r.lstrip().startswith("╰─")), None)
    if begin is not None and eind is not None and eind > begin:
        binnen = [r for r in regels[begin + 1:eind]
                  if r.strip() and "⚕" not in r]
        red = "\n".join(binnen).strip() or None
        na = [r for r in regels[eind + 1:]
              if r.strip()
              and not r.lstrip().startswith("Resume this session with:")
              and not r.lstrip().startswith("hermes ")
              and not r.lstrip().startswith(("Session:", "Title:",
                                             "Duration:", "Messages:"))]
        antw = "\n".join(na).strip()
        if antw:
            return red, antw
        # antwoord zát in de box (bv. korte sessie): box = antwoord
        return None, "\n".join(binnen).strip()

    # 2) taalwissel zoeken: kies de ONDERSTE grens waarboven Engelse
    #    meta-regels zitten en waaronder een aaneengesloten NL-blok. Een
    #    regel met veel NL-hints is antwoord; een regel die op EN-meta
    #    lijkt (of die NL is maar begint als voortzetting van een EN-zin)
    #    is denken. We scannen van onderen en stoppen bij de eerste echte
    #    meta-regel; halve grenzen worden niet geaccepteerd.
    nl_hint_re = re.compile(
        r"\b(de|het|een|van|is|dat|niet|je|zij|we|voor|met|na|ook|maar|"
        r"bij|uit|al|nog|wel|zijn|word|wordt|mijn|onze)\b", re.I)

    def _is_meta(r: str) -> bool:
        laag = r.strip().lower()
        if not laag:
            return True
        if laag.startswith(_DENK_MARKERS):
            return True
        if any(m in laag for m in _DENK_MARKERS):
            return True
        # Voortzettingsregel: begint klein EN heeft weinig NL-hintwoorden —
        # vrijwel zeker een doorlopende (Engelse) zin. MAAR: bekende NL-
        # openers ("hallo", "hardop", "keep it kort" staat er ook in) zijn
        # géén meta — dat zijn antwoordregels.
        eerste = laag.split()[0] if laag.split() else ""
        if eerste[:1].islower():
            if laag.startswith(("hallo", "hardop", "hoi", "keep it kort",
                                "klaar voor", "prima", "goed")):
                return False
            if not nl_hint_re.search(laag) or laag.startswith(
                    ("delivery", "session", "channel", "poller", "resumed")):
                return True
        return False

    # vind de laatste reeks NL-regels van onderen
    i = len(regels)
    while i > 0 and not regels[i - 1].strip():
        i -= 1
    eind_nl = i
    start_nl = eind_nl
    while start_nl > 0:
        regel = regels[start_nl - 1]
        if not regel.strip() or _is_meta(regel):
            break
        blok = regels[start_nl - 1:eind_nl]
        if not _regels_zijn_nederlands(blok):
            break
        start_nl -= 1

    antw_regels = [r for r in regels[start_nl:eind_nl] if r.strip()]
    if antw_regels and start_nl > 0:
        red = "\n".join(r for r in regels[:start_nl] if r.strip())
        antw = "\n".join(antw_regels).strip()
        return (red or None), antw

    # 3) geen wissel: klassieke CLI-opruiming (query-echo, init, sessie-stats)
    opgeschoond = [r for r in regels
                   if r.strip()
                   and not r.lstrip().startswith(("Query:", "Initializing agent",
                                                  "Resume this session with:",
                                                  "hermes ", "Session:", "Title:",
                                                  "Duration:", "Messages:"))
                   and "─────" not in r and "⚕" not in r]
    alles = "\n".join(opgeschoond).strip() or "\n".join(
        r for r in regels if r.strip())
    return None, alles


def zuiver_antwoord(tekst: str) -> str:
    """Het zuivere antwoord uit ruwe Hermes CLI-output (zie splits_antwoord_redenatie)."""
    return splits_antwoord_redenatie(tekst)[1]


def redenatie_uit(tekst: str) -> str | None:
    """Het denkproces uit ruwe Hermes CLI-output (zie splits_antwoord_redenatie)."""
    return splits_antwoord_redenatie(tekst)[0]


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
