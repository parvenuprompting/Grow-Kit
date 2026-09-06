"""CyberSeed Sprout v0.5 — het lokale model met een zelfbijgewerkte SOUL.

Basis: Ollama op localhost:11434 (OpenAI-compatibel HTTP). Alles draait
op deze Mac; niets verlaat het huis.

- SOUL-snapshot: ≤ SOUL_MAX_TEKENS tekens uit bestaande GrowKit-bronnen
  (profiel, ratificaties, saldo, audit, bomen) in vaste volgorde.
- chat(): system = SOUL-inhoud; keep_alive 24h; append-only chatlog
  (JSONL, zonder SOUL-inhoud).
- wissen alleen met bevestig=True (faalcontract).
"""
from __future__ import annotations

import datetime as _dt
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
MODEL_NAAM = "cyberseed-sprout-v0.5"
BASIS_MODEL_DEFAULT = "qwen3:8b"
SOUL_MAX_TEKENS = 16_000  # ≈ 4k tokens

_DAGEN = ("maandag", "dinsdag", "woensdag", "donderdag",
          "vrijdag", "zaterdag", "zondag")


# ---------------------------------------------------------------------------
# Pad-injectie (tests overschrijven _basis_pad)
# ---------------------------------------------------------------------------

def _basis_pad() -> Path:
    return Path.home() / ".growkit" / "cyberseed"


# ---------------------------------------------------------------------------
# HTTP-hulpjes (klein bewust zonder requests-dependency)
# ---------------------------------------------------------------------------

def _http_get(url: str, timeout: int = 4) -> tuple[int, bytes]:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.status, r.read()


def _http_post(url: str, body: dict, timeout: int = 120) -> tuple[int, bytes]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


# ---------------------------------------------------------------------------
# Ollama-status
# ---------------------------------------------------------------------------

def ollama_status() -> dict:
    """{draait, modellen, sprout_basis_aanwezig} — fout = draait False."""
    try:
        code, body = _http_get(f"{OLLAMA_URL}/api/tags")
    except (OSError, urllib.error.URLError):
        return {"draait": False, "modellen": [], "sprout_basis_aanwezig": False}
    if code != 200:
        return {"draait": False, "modellen": [], "sprout_basis_aanwezig": False}
    try:
        tags = [m.get("name", "") for m in json.loads(body).get("models", [])]
    except (json.JSONDecodeError, AttributeError):
        tags = []
    basis = BASIS_MODEL_DEFAULT.split(":")[0]
    aanwezig = any(t == BASIS_MODEL_DEFAULT or t.startswith(basis + ":")
                   for t in tags)
    return {"draait": True, "modellen": tags, "sprout_basis_aanwezig": aanwezig}


# ---------------------------------------------------------------------------
# Bronnen voor de SOUL-snapshot (bestaande GrowKit-kern, geen nieuwe backend)
# ---------------------------------------------------------------------------

def _profiel_tekst() -> str:
    try:
        import adapter  # laat-import: kern mag adapter niet top-level importeren
        r = adapter.COMMANDOS["profiel"]({"actie": "lees"})
        if r.get("ok"):
            d = r.get("data", {})
            delen = [str(d.get(k, "")) for k in ("naam", "rol", "omgeving") if d.get(k)]
            return " · ".join(delen) if delen else json.dumps(d, ensure_ascii=False)[:400]
    except Exception:
        pass
    return "(profiel onbereikbaar)"


def _saldo_tekst() -> str:
    try:
        import adapter
        r = adapter.COMMANDOS["saldo"]({})
        if r.get("ok"):
            rest = r["data"].get("resterend")
            return f"€ {rest:.2f}" if isinstance(rest, (int, float)) else "(onbekend)"
    except Exception:
        pass
    return "(onbereikbaar)"


def _audit_regels(n: int = 10) -> list[str]:
    try:
        import adapter
        r = adapter.COMMANDOS["audit"]({"actie": "staart", "aantal": n})
        if r.get("ok"):
            return [str(x)[:120] for x in r.get("data", {}).get("regels", [])][:n]
    except Exception:
        pass
    return []


def _bomen_tekst() -> list[str]:
    try:
        import adapter
        r = adapter.COMMANDOS["bomen"]({})
        if r.get("ok"):
            return [str(b.get("naam", "?"))[:60]
                    for b in r.get("data", {}).get("bomen", [])][:10]
    except Exception:
        pass
    return []


def _ratificaties_tekst() -> list[str]:
    try:
        import adapter
        r = adapter.COMMANDOS["agentcontrole"]({"doel": "~/growkit-governor"})
        if r.get("ok"):
            wacht = r.get("data", {}).get("wachtend") or []
            return [f"{t.get('agent', '?')}: {t.get('titel', '')}"[:120]
                    for t in wacht][:5]
    except Exception:
        pass
    return []


def _verzamel_bronnen() -> dict:
    """Eén plek die alle SOUL-bronnen levert (tests mocken deze)."""
    return {
        "profiel": _profiel_tekst(),
        "ratificaties": _ratificaties_tekst(),
        "saldo": _saldo_tekst(),
        "audit": _audit_regels(),
        "bomen": _bomen_tekst(),
    }


# ---------------------------------------------------------------------------
# SOUL-snapshot
# ---------------------------------------------------------------------------

def _nu() -> _dt.datetime:
    return _dt.datetime.now()


def soul_snapshot() -> str:
    """Vaste-opbouw snapshot; deterministisch behalve de kop-tijdstempel."""
    b = _verzamel_bronnen()
    nu = _nu()
    dag = _DAGEN[nu.weekday()]
    kop = (f"# CyberSeed SOUL · snapshot {nu:%Y-%m-%d %H:%M} "
           f"({dag}) · model {MODEL_NAAM}")

    lijnen = [kop, "", f"## Wie ik dien", b["profiel"] or "(leeg)", ""]
    lijnen += ["## Wacht op de mens"]
    if b["ratificaties"]:
        lijnen += [f"- {x}" for x in b["ratificaties"]]
    else:
        lijns = ["- niets — geen open ratificaties"]
        lijnen += lijns
    lijnen += ["", f"## Saldo", str(b["saldo"]), ""]
    lijnen += ["## Laatste werk"]
    if b["audit"]:
        lijnen += [f"- {x}" for x in b["audit"]]
    else:
        lijnen += ["- (nog geen audit-regels)"]
    lijnen += ["", "## Actieve projecten"]
    if b["bomen"]:
        lijnen += [f"- {x}" for x in b["bomen"]]
    else:
        lijnen += ["- (geen actieve bomen)"]
    lijnen += ["", "## Houding",
               "- Behulpzaam altijd, meegaand nooit. Stuur met een concrete",
               "  vervolgstap. Noem de gebruiker bij naam (zie Wie ik dien)."]

    tekst = "\n".join(lijnen)
    if len(tekst) > SOUL_MAX_TEKENS:
        tekst = tekst[:SOUL_MAX_TEKENS - 3].rstrip() + "…"
    return tekst


def soul_lees() -> str | None:
    pad = _basis_pad() / "SOUL.md"
    if not pad.exists():
        return None
    try:
        return pad.read_text()
    except OSError:
        return None


def soul_bewaar(tekst: str) -> Path:
    pad = _basis_pad()
    pad.mkdir(parents=True, exist_ok=True)
    (pad / "SOUL.md").write_text(tekst)
    meta = {"model": MODEL_NAAM,
            "gegenereerd": _nu().isoformat(timespec="seconds")}
    (pad / "meta.json").write_text(json.dumps(meta, ensure_ascii=False))
    return pad / "SOUL.md"


def soul_leeftijd_uren() -> float | None:
    pad = _basis_pad() / "SOUL.md"
    if not pad.exists():
        return None
    leeftijd = _nu() - _dt.datetime.fromtimestamp(pad.stat().st_mtime)
    return leeftijd.total_seconds() / 3600


def verfris_soul() -> float:
    """Genereer + bewaar; retourneert nieuwe leeftijd (0.0)."""
    soul_bewaar(soul_snapshot())
    return soul_leeftijd_uren() or 0.0


# ---------------------------------------------------------------------------
# Chat (Ollama /api/chat, system = SOUL)
# ---------------------------------------------------------------------------

def _log_regel(rol: str, tekst: str) -> None:
    pad = _basis_pad()
    pad.mkdir(parents=True, exist_ok=True)
    regel = {"ts": _nu().isoformat(timespec="seconds"),
             "rol": rol, "tekst": tekst[:2000]}
    with (pad / "chatlog.jsonl").open("a") as f:
        f.write(json.dumps(regel, ensure_ascii=False) + "\n")


def chat(bericht: str, *, van: str = "", model: str = "") -> str:
    """Eén beurt: SOUL als system, bericht erin, antwoord terug + gelogd."""
    soul = soul_lees()
    if not soul:
        soul = verfris_soul() and soul_lees() or soul_snapshot()
    body = {
        "model": model or BASIS_MODEL_DEFAULT,
        "keep_alive": "24h",
        "stream": False,
        "messages": [
            {"role": "system", "content": soul},
            {"role": "user",
             "content": f"[van: {van or 'onbekend'}] {bericht}"},
        ],
    }
    try:
        code, data = _http_post(f"{OLLAMA_URL}/api/chat", body)
    except OSError as e:
        raise ConnectionError(f"Ollama onbereikbaar: {e}")
    if code != 200:
        raise ConnectionError(f"Ollama antwoordde {code}")
    try:
        antw = json.loads(data)["message"]["content"]
    except (json.JSONDecodeError, KeyError) as e:
        raise ConnectionError(f"Ongeldig Ollama-antwoord: {e}")
    _log_regel("gebruiker", bericht)
    _log_regel("assistent", antw)
    return antw


# ---------------------------------------------------------------------------
# Chatlog
# ---------------------------------------------------------------------------

def chatlog_lees(n: int = 20) -> list[dict]:
    pad = _basis_pad() / "chatlog.jsonl"
    if not pad.exists():
        return []
    regels = pad.read_text().strip().splitlines()
    uit = []
    for r in regels[-n:]:
        try:
            uit.append(json.loads(r))
        except json.JSONDecodeError:
            continue
    return uit


def chatlog_wis(bevestig: bool = False) -> None:
    """Definitief wissen — weigert zonder bevestig=True (faalcontract)."""
    if not bevestig:
        raise PermissionError("wis vereist bevestig=True")
    pad = _basis_pad() / "chatlog.jsonl"
    if pad.exists():
        pad.unlink()
