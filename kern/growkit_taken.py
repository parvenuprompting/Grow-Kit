"""GrowKit takenlijst — taken bestaan alleen mét bewijs (spec §7).

Elke taak volgt het stappen-schema (§4): zonder `bewijs` met `type` bestaat
de taak niet (poort-regel). Gebeurtenissen worden append-only gelogd.
"""
import datetime
import json
from pathlib import Path

from kern.growkit_poort import beoordeel_invoer


# ---------------------------------------------------------------- governor
def _governor_lees(pad: Path) -> dict:
    """Governor-register lezen; afwezig/corrupt = vers leeg register
    (fail-open richting leeg register, nooit auto-reparatie van inhoud)."""
    from kern import growkit_agents as ag
    try:
        return json.loads(Path(pad).read_text(encoding="utf-8"))
    except Exception:
        return ag.nieuw_register()


def _governor_bewaar(pad: Path, register: dict) -> None:
    """Register wegschrijven; faalt stil (de taak-logboekregels blijven de
    waarheid — het register is de governing-laag, niet het bewijs)."""
    try:
        pad = Path(pad)
        pad.parent.mkdir(parents=True, exist_ok=True)
        pad.write_text(json.dumps(register, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
    except Exception:
        pass


def _governor_afronden(pad: Path | None, agent: str | None, taak_id: str,
                       geslaagd: bool) -> None:
    """Na de motor: klaargemeld → 'wacht_op_controle' (mens keurt in de app)."""
    if pad is None or not agent:
        return
    from kern import growkit_agents as ag
    reg = _governor_lees(pad)
    if geslaagd:
        reg, _, _ = ag.taak_afgerond(reg, agent, taak_id,
                                     bewijs="machine-bewijs (§3)")
    else:
        # gefaalde taak: afkeuren met reden zodat de agent hem herhaalt
        if reg["taken"].get(taak_id, {}).get("status") == "wacht_op_controle":
            reg, _, _ = ag.keur_taak(reg, taak_id, goed=False,
                                     reden="motor faalde na alternatief")
    _governor_bewaar(pad, reg)


def laad_taken(pad: Path) -> list[dict]:
    """Lees de takenlijst; afwezig bestand is een lege lijst."""
    if not pad.exists():
        return []
    try:
        return json.loads(pad.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(
            f"takenlijst {pad} is corrupt — roep de mens, nooit auto-repareren: {e}"
        ) from e


def valideer_taak(taak: dict) -> list[str]:
    """Poort-regel (§11, taak-type): geen bewijs-check → de taak bestaat niet."""
    bevindingen = []
    if not taak.get("id"):
        bevindingen.append("taak zonder id — ongeldig volgens het stappen-schema (§4)")
    ok, tekst, _ = beoordeel_invoer(taak, "taak")
    if not ok:
        bevindingen.append(tekst)
    return bevindingen


def log_taakgebeurtenis(pad: Path, taak_id: str, status: str, bewijs: str) -> None:
    """Append-only gebeurtenis per taak; bestaande entries blijven staan."""
    pad.parent.mkdir(parents=True, exist_ok=True)
    entries = json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else []
    entries.append({
        "type": "taak",
        "taak": taak_id,
        "status": status,
        "bewijs": bewijs,
        "tijdstip": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    })
    pad.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def voer_taak_uit(doel: Path, taak: dict, reviewconfig=None,
                  governor_pad: Path | None = None, agent: str | None = None,
                  vereist_governor: bool = False) -> tuple[bool, list[str]]:
    """Poort → gebeurtenissen → motor: de volledige taak-uitvoering als kern.

    Geen prints — loop.py en de adapter geven zelf hun eigen vorm. Retourneert
    (geslaagd, bevindingen): bevindingen non-leeg = poort-weigering (niets
    uitgevoerd, gebeurtenis 'geweigerd' gelogd). Faalcontract van de motor
    staat onaangetast: één alternatief, dan de mens.

    Governor-koppeling (slice 10): mét governor_pad + agent loopt de taak
    door het governerspoor — aanmelden vóór uitvoering, afronden erna
    (status 'wacht_op_controle'; de mens keurt in de app). Weigert de
    governor (limiet, observer), dan start de motor niet: poortgetrouw.
    Zonder governor_pad verandert het gedrag niet (achterwaarts compatibel).
    """
    import json as _json
    from kern import growkit_motor

    taak_id = taak.get("id", "onbekend")
    taken_logboek = doel / "taken-logboek.json"

    # Governor vóór de poort: aanmelden (of weigeren) vóórdat iets draait.
    reg = None
    if governor_pad is not None and agent:
        from kern import growkit_agents as ag
        reg = _governor_lees(governor_pad)
        reg, ok, reden = ag.meld_taak_aan(reg, agent, taak_id)
        if not ok:
            log_taakgebeurtenis(taken_logboek, taak_id, "geweigerd",
                                "governor-weigering: " + reden)
            return False, [f"governor-weigering: {reden}"]
        _governor_bewaar(governor_pad, reg)

    bevindingen = valideer_taak(taak)
    if bevindingen:
        log_taakgebeurtenis(taken_logboek, taak_id, "geweigerd",
                            "poort-weigering: " + "; ".join(bevindingen))
        return False, bevindingen
    log_taakgebeurtenis(taken_logboek, taak_id, "bezig", "motor-start")
    boom_logboek = doel / "logboek.json"
    if not boom_logboek.exists():
        boom_logboek.write_text("[]", encoding="utf-8")
    geslaagd = growkit_motor.voer_uit({"profiel": f"taak-{taak_id}", "stappen": [taak]},
                                      doel, boom_logboek, None, reviewconfig=reviewconfig,
                                      vangnet=growkit_motor.vangnet_pad_voor(doel))
    if geslaagd:
        log_taakgebeurtenis(taken_logboek, taak_id, "geslaagd", "machine-bewijs (§3)")
    else:
        log_taakgebeurtenis(taken_logboek, taak_id, "gefaald", "motor-faalcontract — roep de mens")
    _governor_afronden(governor_pad, agent, taak_id, geslaagd)
    return geslaagd, []
