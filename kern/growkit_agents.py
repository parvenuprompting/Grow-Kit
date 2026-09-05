#!/usr/bin/env python3
"""GrowKit agent-governor — hoeveel taken mag één agent dragen? (fase 7)

Regels (besloten met Tiëndo, 5 sept 2026):
1.  Elke agent behandelt maximaal 2 taken tegelijk.
2.  Wil een agent meer dan 2 taken, dan wordt een tijdelijke subagent
    aangemaakt die de extra taken draagt (zelfde grenzen).
3.  Na het afronden van een taak volgt een controle. Pas na goedkeuring
    is de taak echt af en wordt — bij geen open taken — de agent
    vrijgelaten (de tijdelijke subagent stopt dan).
4.  Er is altijd één observer: die schrijft géén code en voert niets uit.
    De enige rol is alles observeren, onthouden en belangrijke
    bevindingen aan de gebruiker melden. De observer kan nooit taken
    krijgen.
5.  Grenzen: maximaal 8 agents tegelijk (2 taken elk = 16 taken).
    Toekomstvisie (na bewezen Arché): 16 of 32 agents — bewust NIET
    geactiveerd; deze constanten veranderen pas na een expliciet
    besluit van Tiëndo.

Deze module beheert alleen de toestand (het register): wie draagt wat,
wie wacht op controle, wie mag erbij. Uitvoering en goedkeuring blijven
bij de bestaande kern (poort, motor, review) — de governor is een
bedienaar van aantallen, nooit een machthebber over inhoud.
"""
import copy
from datetime import datetime, timezone

# --- grenzen (bewust constanten, geen configuratie: dit is beleid) ---
MAX_TAKEN_PER_AGENT = 2
MAX_AGENTS = 8                 # toekomst: 16 of 32, pas na bewezen Arché
MAX_TAKEN_TOTAAL = MAX_AGENTS * MAX_TAKEN_PER_AGENT

# De observer: mag nooit taken dragen, voert nooit iets uit.
OBSERVER_NAAM = "observer"

GEBEURTENISSEN = ("aangemeld", "subagent_gevormd", "wacht_op_controle",
                  "goedgekeurd", "afgewezen", "agent_vrijgelaten",
                  "geweigerd_limiet")


def _nu() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def nieuw_register() -> dict:
    """Leeg register: geen agents, geen taken, observer bestaat altijd."""
    return {
        "agents": {OBSERVER_NAAM: {"rol": "observer", "open": [], "afrondend": []}},
        "taken": {},      # taak_id -> {"agent": ..., "status": ..., "bewijs": ...}
        "gebeurtenissen": [],
    }


def _log(register: dict, gebeurtenis: str, agent: str, taak: str | None = None,
         noot: str | None = None) -> None:
    entry = {"gebeurtenis": gebeurtenis, "agent": agent, "tijdstip": _nu()}
    if taak:
        entry["taak"] = taak
    if noot:
        entry["noot"] = noot
    register["gebeurtenissen"].append(entry)


def _is_subagent(register: dict, agent: str) -> bool:
    rol = register["agents"].get(agent, {}).get("rol")
    return rol == "subagent"


def _open_taken(register: dict, agent: str) -> int:
    return len(register["agents"].get(agent, {}).get("open", []))


def _bestaande_agents(register: dict) -> int:
    """Aantal agents dat taken mag dragen (observer telt niet mee)."""
    return sum(1 for naam, a in register["agents"].items()
               if a.get("rol") != "observer")


def _vrije_agent_naam(register: dict) -> str:
    n = 1
    while f"subagent-{n}" in register["agents"]:
        n += 1
    return f"subagent-{n}"


def meld_taak_aan(register: dict, agent: str, taak_id: str) -> tuple[dict, bool, str]:
    """Meld een taak aan voor een agent. Retourneer (nieuw_register, ok, reden).

    Weigert (fail-safe) wanneer:
    - de agent de observer is (die observeert, die bouwt niet);
    - de agent al MAX_TAKEN_PER_AGENT taken draagt (tip: subagent vormen);
    - er meer agents zouden bestaan dan MAX_AGENS toestaat;
    - de taak al bestaat of het totaallimiet is bereikt.
    """
    nieuw = copy.deepcopy(register)
    agent = agent.strip() or OBSERVER_NAAM
    if agent == OBSERVER_NAAM:
        _log(nieuw, "geweigerd_limiet", agent, taak_id,
             "de observer voert niets uit en krijgt nooit taken")
        return nieuw, False, (f"De observer neemt geen taken aan — die kijkt "
                              f"alleen en meldt bevindingen. Kies een andere agent.")
    if taak_id in nieuw["taken"]:
        # Dubbele aanmelding van dezelfde taak bij dezelfde agent is geen
        # weigering maar een no-op (herstart/herhaal-situaties in het harnas).
        if nieuw["taken"][taak_id].get("agent") == agent:
            return nieuw, True, f"Taak '{taak_id}' was al aangemeld bij {agent}."
        return nieuw, False, f"Taak '{taak_id}' bestaat al."
    if _open_taken(nieuw, agent) >= MAX_TAKEN_PER_AGENT:
        _log(nieuw, "geweigerd_limiet", agent, taak_id,
             f"limiet van {MAX_TAKEN_PER_AGENT} taken per agent bereikt")
        return nieuw, False, (f"{agent} draagt al {MAX_TAKEN_PER_AGENT} taken. "
                              f"Vorm eerst een subagent (zie vorm_subagent).")
    if agent not in nieuw["agents"]:
        if _bestaande_agents(nieuw) >= MAX_AGENTS:
            _log(nieuw, "geweigerd_limiet", agent, taak_id,
                 f"maximaal {MAX_AGENTS} agents gelijktijdig")
            return nieuw, False, (f"Limiet bereikt: maximaal {MAX_AGENTS} agents "
                                  f"gelijktijdig ({MAX_TAKEN_TOTAAL} taken). "
                                  f"Hoort bij de bewuste grens — geen agents extra.")
        nieuw["agents"][agent] = {"rol": "subagent" if agent.startswith("subagent-")
                                  else "hoofd", "open": [], "afrondend": []}
    if len(nieuw["taken"]) >= MAX_TAKEN_TOTAAL:
        _log(nieuw, "geweigerd_limiet", agent, taak_id,
             f"totaallimiet van {MAX_TAKEN_TOTAAL} taken")
        return nieuw, False, (f"Limiet bereikt: {MAX_TAKEN_TOTAAL} taken tegelijk "
                              f"is genoeg. Meer willen is gewoon gretig.")
    nieuw["agents"][agent]["open"].append(taak_id)
    nieuw["taken"][taak_id] = {"agent": agent, "status": "open"}
    _log(nieuw, "aangemeld", agent, taak_id)
    return nieuw, True, f"Taak '{taak_id}' aangemeld bij {agent}."


def vorm_subagent(register: dict, ouder: str) -> tuple[dict, bool, str]:
    """Vorm een tijdelijke subagent voor extra taken van `ouder`.

    Alleen nodig (en alleen toegestaan) als de ouder op de limiet zit —
    zo voorkom je dat agents 'voor de groei' makkers aanmaken.
    """
    nieuw = copy.deepcopy(register)
    if ouder not in nieuw["agents"] or nieuw["agents"][ouder]["rol"] == "observer":
        return nieuw, False, "Onbekende agent (of de observer): geen subagent."
    if _open_taken(nieuw, ouder) < MAX_TAKEN_PER_AGENT:
        return nieuw, False, (f"{ouder} draagt nog geen {MAX_TAKEN_PER_AGENT} taken "
                              f"— een subagent is nu niet nodig.")
    if _bestaande_agents(nieuw) >= MAX_AGENTS:
        _log(nieuw, "geweigerd_limiet", ouder, None,
             f"maximaal {MAX_AGENTS} agents gelijktijdig")
        return nieuw, False, (f"Limiet bereikt: maximaal {MAX_AGENTS} agents "
                              f"gelijktijdig. Wacht tot er een vrijkomt.")
    naam = _vrije_agent_naam(nieuw)
    nieuw["agents"][naam] = {"rol": "subagent", "ouder": ouder,
                             "open": [], "afrondend": []}
    _log(nieuw, "subagent_gevormd", ouder, None, f"subagent: {naam}")
    return nieuw, True, f"Subagent '{naam}' gevormd voor extra taken van {ouder}."


def taak_afgerond(register: dict, agent: str, taak_id: str,
                  bewijs: str | None = None) -> tuple[dict, bool, str]:
    """Agent zegt: de taak is klaar. Status wordt 'wacht_op_controle' —
    de taak is pas echt af na goedkeuring (controle verplicht)."""
    nieuw = copy.deepcopy(register)
    taak = nieuw["taken"].get(taak_id)
    if not taak or taak["agent"] != agent:
        return nieuw, False, f"Taak '{taak_id}' hoort niet bij {agent}."
    if taak["status"] != "open":
        return nieuw, False, f"Taak '{taak_id}' is niet open (status: {taak['status']})."
    if taak_id in nieuw["agents"][agent]["open"]:
        nieuw["agents"][agent]["open"].remove(taak_id)
    nieuw["agents"][agent]["afrondend"].append(taak_id)
    taak["status"] = "wacht_op_controle"
    taak["bewijs"] = bewijs or ""
    _log(nieuw, "wacht_op_controle", agent, taak_id)
    return nieuw, True, f"Taak '{taak_id}' klaargemeld — wacht op controle."


def keur_taak(register: dict, taak_id: str, goed: bool,
              reden: str | None = None) -> tuple[dict, bool, str]:
    """De controle: goedkeuring laat de taak (en eventueel de agent) vrij;
    afkeuring zet de taak terug naar open bij dezelfde agent."""
    nieuw = copy.deepcopy(register)
    taak = nieuw["taken"].get(taak_id)
    if not taak or taak["status"] != "wacht_op_controle":
        return nieuw, False, f"Taak '{taak_id}' wacht niet op controle."
    agent = taak["agent"]
    if goed:
        taak["status"] = "goedgekeurd"
        if taak_id in nieuw["agents"][agent]["afrondend"]:
            nieuw["agents"][agent]["afrondend"].remove(taak_id)
        _log(nieuw, "goedgekeurd", agent, taak_id, reden)
        bericht = f"Taak '{taak_id}' goedgekeurd."
        # Vrijlating: agent zonder open of afrondende taken stopt (subagent).
        a = nieuw["agents"][agent]
        if a["rol"] == "subagent" and not a["open"] and not a["afrondend"]:
            a["vrijgelaten"] = True
            _log(nieuw, "agent_vrijgelaten", agent)
            bericht += f" {agent} heeft niets meer open en is vrijgelaten."
        return nieuw, True, bericht
    taak["status"] = "open"
    if taak_id not in nieuw["agents"][agent]["open"]:
        nieuw["agents"][agent]["open"].append(taak_id)
    if taak_id in nieuw["agents"][agent]["afrondend"]:
        nieuw["agents"][agent]["afrondend"].remove(taak_id)
    _log(nieuw, "afgewezen", agent, taak_id, reden)
    return nieuw, True, f"Taak '{taak_id}' afgekeurd en terug naar {agent}." \
                        + (f" Reden: {reden}" if reden else "")


def melding_van_observer(register: dict, tekst: str) -> tuple[dict, bool, str]:
    """De observer meldt een bevinding aan de gebruiker. Dit is de ENIGE
    actie die de observer doet: lezen, onthouden, melden."""
    nieuw = copy.deepcopy(register)
    nieuw.setdefault("observer_meldingen", []).append({"tekst": tekst, "tijdstip": _nu()})
    return nieuw, True, "Bevinding genoteerd voor de gebruiker."
