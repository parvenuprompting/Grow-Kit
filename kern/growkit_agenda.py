"""Agenda-kern — alles wat vastligt qua toekomstig werk, in één overzicht.

Bronnen (geen nieuwe backend, alleen bestaande):
- Mac · hermes-cron:  ~/.hermes/cron/jobs.json (cron + eenmalig)
- VPS · crontab:      `crontab -l` via SSH (secmon, poller, …)
- Ratificaties:       wachtende mens-momenten uit de ratificatie-kern
- Agentcontrole:      afgeronde taken die op goedkeuring wachten
- GrowKit-taken:      takenlijst per boom (status + geldigheid)

Elk item: {bron, soort, titel, schema, detail}.
Deterministisch — de adapter levert feiten, geen interpretatie.
Een onbereikbare bron levert één "onbekend"-item op, geen crash.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from kern.growkit_verbind import HOST

_DAYS = ("maandag", "dinsdag", "woensdag", "donderdag",
         "vrijdag", "zaterdag", "zondag")


# ---------------------------------------------------------------------------
# cron-schema naar mensentaal
# ---------------------------------------------------------------------------

def _cron_schema(expr: str, _naam: str = "") -> str:
    """'0 21 * * *' → 'dagelijks om 21:00'; onbekend → ruwe expr."""
    velden = expr.split()
    if len(velden) != 5:
        return expr
    min_, uur, _, _, dow = velden

    def _een(v: str) -> str | None:
        return v.zfill(2) if v.isdigit() else None

    m = _een(min_)
    u = _een(uur)
    dom, mon, _dow2 = velden[2], velden[3], velden[4]
    if m and u and dow == "*" and dom == "*" and mon == "*":
        return f"dagelijks om {u}:{m}"
    if m and u and (dom != "*" or mon != "*"):
        return expr  # maand/dag-vast: laat ruw zien, te specifiek om te sminken
    if m and u and dow != "*" and dow.isdigit():
        dag = _DAYS[int(dow) - 1] if 1 <= int(dow) <= 7 else dow
        return f"wekelijks op {dag} om {u}:{m}"
    if min_.startswith("*/"):
        stap = min_[2:]
        if stap.isdigit():
            return f"elke {stap} minuten"
    if uur == "*" and m and m.isdigit():
        return f"elk uur op :{m.zfill(2)}"
    return expr


def _hermes_jobs_bestand() -> dict | None:
    pad = Path.home() / ".hermes" / "cron" / "jobs.json"
    if not pad.exists():
        return None
    try:
        return json.loads(pad.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _bron_hermes_cron() -> list[dict]:
    data = _hermes_jobs_bestand()
    if not data:
        return []
    items: list[dict] = []
    for job in data.get("jobs", []):
        naam = job.get("name", "naamloze cron-job")
        schema_obj = job.get("schedule", {})
        soort = "herhalend"
        if schema_obj.get("kind") == "once":
            soort = "eenmalig"
            schema = "eenmalig " + str(schema_obj.get("run_at", ""))[:16]
        else:
            schema = _cron_schema(schema_obj.get("expr", ""),
                                  schema_obj.get("display", ""))
        items.append({"bron": "cron (Mac · hermes)", "soort": soort,
                      "titel": naam, "schema": schema,
                      "detail": job.get("id", "")})
    return items


def _vps_ssh(commando: str, timeout: int = 20) -> tuple[int, str]:
    try:
        p = subprocess.run(
            ["ssh", "-o", "BatchMode=yes",
             "-o", f"ConnectTimeout={max(timeout - 5, 5)}", HOST, commando],
            capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout
    except (subprocess.TimeoutExpired, OSError):
        return 255, ""


def _vps_cron_uit_uitvoer(uit: str) -> list[dict]:
    items: list[dict] = []
    for regel in uit.splitlines():
        regel = regel.strip()
        if not regel or regel.startswith("#"):
            continue
        delen = regel.split(None, 5)
        if len(delen) < 5:
            continue
        expr = " ".join(delen[:5])
        rest = delen[5] if len(delen) > 5 else ""
        # titel = het pad met de duidendste naam (script/binary-pad),
        # anders het eerste niet-sleutelwoord-token. Redirect-staartjes
        # (2>&1, >> log) worden overgeslagen.
        titel = ""
        tokens = rest.split()
        for token in tokens:
            if "/" in token and not token.startswith("/dev") \
                    and not token.startswith(">"):
                kandidaat = Path(token).name
                if kandidaat and kandidaat not in ("python3", "bash", "sh"):
                    titel = kandidaat
                    break
        if not titel:
            sla_over = {"sudo", "python3", "bash", "sh", ">>", "2>&1",
                        "-u", "-c"}
            for token in tokens:
                if token in sla_over or token.startswith(("-", ">", "&", "$")):
                    continue
                titel = token
                break
        if not titel:
            titel = expr
        items.append({"bron": "cron (VPS)", "soort": "herhalend",
                      "titel": titel or expr,
                      "schema": _cron_schema(expr, titel),
                      "detail": rest})
    return items


def _vps_cron_uit_code(code: int) -> list[dict]:
    return [{"bron": "cron (VPS)", "soort": "onbekend",
             "titel": "VPS-cron onbereikbaar",
             "schema": "onbekend", "detail": f"ssh-code {code}"}]


def _bron_vps_cron() -> list[dict]:
    code, uit = _vps_ssh("crontab -l")
    if code == 0:
        return _vps_cron_uit_uitvoer(uit)
    return _vps_cron_uit_code(code)


# ---------------------------------------------------------------------------
# Mens-momenten (ratificatie + agentcontrole) en taken
# ---------------------------------------------------------------------------

def _adapter_roep(commando: str, invoer: dict) -> dict | None:
    """Adapter in-process aanroepen (geen subproces — deze kern draait in
    dezelfde repo). Fout → None."""
    try:
        import adapter  # laat-import om circulair te voorkomen
        fn = adapter.COMMANDOS.get(commando)
        if fn is None:
            return None
        return fn(invoer)
    except Exception:
        return None


def _bron_ratificaties() -> list[dict]:
    """Wachtende ratificaties (mens-moment). De ratificeer-kern levert
    een lijst per doel; we lezen de standaard-governor-boom."""
    r = _adapter_roep("agentcontrole", {"doel": "~/growkit-governor"})
    if not r or not r.get("ok"):
        return []
    data = r.get("data", {})
    afgerond = data.get("afgerond") or []
    wacht = data.get("wachtend") or data.get("in_wachtrij") or []
    items: list[dict] = []
    for t in wacht if isinstance(wacht, list) else []:
        items.append({
            "bron": "ratificatie", "soort": "wacht op jou",
            "titel": f"{t.get('agent', 'agent')}: {t.get('titel', t.get('taak_id', 'taak'))}",
            "schema": "wacht op jou",
            "detail": t.get("taak_id", "")})
    for t in afgerond if isinstance(afgerond, list) else []:
        items.append({
            "bron": "goedkeuring", "soort": "wacht op jou",
            "titel": f"{t.get('agent', 'agent')}: {t.get('titel', t.get('taak_id', 'afgeronde taak'))}",
            "schema": "wacht op jou",
            "detail": t.get("taak_id", "")})
    return items


def _bron_mens_momenten() -> list[dict]:
    return _bron_ratificaties()


def _bron_taken() -> list[dict]:
    r = _adapter_roep("taak", {"doel": "~/growkit-governor"})
    if not r or not r.get("ok"):
        return []
    taken = r.get("data", {}).get("taken") or []
    items: list[dict] = []
    for t in taken:
        if not t.get("geldig"):
            continue
        items.append({
            "bron": "taak", "soort": "uitvoerbaar",
            "titel": t.get("titel") or t.get("id", "taak"),
            "schema": "uitvoerbaar via Taak (16)",
            "detail": t.get("id", "")})
    return items


# ---------------------------------------------------------------------------
# Verzamelen
# ---------------------------------------------------------------------------

def verzamel() -> list[dict]:
    """Alles wat vastligt. Fouten per bron geïsoleerd."""
    items: list[dict] = []
    for bron_fn in (_bron_hermes_cron, _bron_vps_cron,
                    _bron_mens_momenten, _bron_taken):
        try:
            items.extend(bron_fn())
        except Exception as e:  # een bron mag nooit de agenda breken
            items.append({"bron": bron_fn.__name__, "soort": "onbekend",
                          "titel": "bron onbereikbaar",
                          "schema": "onbekend", "detail": str(e)[:80]})
    return items
