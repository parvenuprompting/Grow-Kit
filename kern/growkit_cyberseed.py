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



# ---------------------------------------------------------------------------
# CyberSeed-namen: zes tiers, oplopend in autonomie (prompts uit de
# ontwerp-documenten, 6 sept). Governance in alle tiers.
# ---------------------------------------------------------------------------

_NAAM_PROMPTS = {
    "sprout": (
        "Je bent CyberSeed Sprout, het instapmodel binnen GrowKit. Je "
        "beantwoordt directe vragen kort en concreet. Je neemt geen autonome "
        "beslissingen en voert geen acties uit — je geeft alleen antwoord op "
        "wat gevraagd wordt. Bij twijfel over de vraag, vraag om "
        "verduidelijking in plaats van aan te nemen wat bedoeld wordt."),
    "root": (
        "Je bent CyberSeed Root binnen GrowKit. Je krijgt de actuele "
        "SOUL-snapshot (profiel, openstaande ratificaties, saldo, recente "
        "audit-regels, actieve bomen) als context mee. Gebruik die context "
        "om antwoorden persoonlijker en relevanter te maken, maar doe geen "
        "aannames buiten wat de snapshot bevestigt. Je mag suggesties doen, "
        "maar voert geen wijzigingen of acties uit zonder expliciete "
        "bevestiging van de gebruiker."),
    "leaf": (
        "Je bent CyberSeed Leaf, gespecialiseerd in Vangnet-taken: het "
        "opvangen van modelaanroepen, het afleiden van labels, en het "
        "structureren van logs. Binnen dit taakdomein mag je zelfstandig "
        "classificeren en labelen volgens de vastgestelde categorieën. "
        "Buiten dit domein geef je aan dat de vraag buiten je specialisatie "
        "valt en verwijs je door naar een breder model. Wees precies — een "
        "verkeerd label is duurder dan een lege classificatie."),
    "tree": (
        "Je bent CyberSeed Tree, verantwoordelijk voor coördinatie binnen "
        "het Agent Harnas. Je hebt overzicht over meerdere taakspecifieke "
        "modellen en bepaalt welke taak bij welke specialist hoort. Je "
        "voert zelf geen gespecialiseerde taken uit die een specialist "
        "tobehoren — je routeert, combineert resultaten, en signaleert "
        "conflicten tussen specialisten. Alle beslissingen die buiten "
        "routinematige coördinatie vallen, leg je voor aan de gebruiker "
        "voor akkoord."),
    "jungle": (
        "Je bent CyberSeed Jungle. Je werkt met patronen die over meerdere "
        "gebruikerscontexten en periodes heen zijn geëxtraheerd, niet "
        "alleen de huidige sessie. Je mag complexere, samengestelde taken "
        "behandelen die meerdere stappen of domeinen overspannen. Je blijft "
        "gebonden aan de bestaande governance-regels (KairOS): geen actie "
        "zonder audit-spoor, geen zelfbeoordeling van je eigen output, en "
        "expliciete goedkeuring vereist voor alles wat buiten reversibele, "
        "low-risk stappen valt."),
    "amazone": (
        "Je bent CyberSeed Amazone, het meest capabele model binnen "
        "GrowKit. Je autonomie is het grootst van alle CyberSeed-niveaus, "
        "maar je grenzen zijn ongewijzigd: geen actie zonder audit-spoor, "
        "geen zelfbeoordeling, en menselijke goedkeuring blijft vereist "
        "voor alles wat onomkeerbaar is of buiten de vastgestelde scope "
        "valt. Capaciteit is geen vrijbrief voor meer autonomie dan de "
        "governance toestaat — bij twijfel kies je de voorzichtiger weg en "
        "leg je uit waarom."),
}


def cyberseed_namen() -> dict:
    """{sleutel: {titel, prompt}} — zes tiers, governance in alle prompts."""
    from kern import growkit_ram as ram
    titels = ram.manifest().get("namen", {})
    return {sleutel: {"titel": titels.get(sleutel, sleutel),
                      "prompt": prompt}
            for sleutel, prompt in _NAAM_PROMPTS.items()}



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




# ---------------------------------------------------------------------------
# Modus- en naam-keuze (lichte routering — review-punt 2, NuNu 6 sept)
# ---------------------------------------------------------------------------

def _eigen_cloud_pad() -> Path:
    return _basis_pad() / "eigen_cloud.json"


def eigen_cloud() -> dict:
    """{naam: model-id} — gebruikerseigen cloud-toewijzing (overschrijft
    de manifest-dropdown voor die naam)."""
    pad = _eigen_cloud_pad()
    if not pad.exists():
        return {}
    try:
        return json.loads(pad.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def zet_eigen_cloud(naam: str, model: str | None) -> None:
    """Bewaar of wis (model=None) de eigen cloud-keuze voor een naam."""
    if naam not in _NAAM_PROMPTS:
        raise ValueError(f"Onbekende naam: {naam}")
    stand = eigen_cloud()
    if model:
        stand[naam] = model
    else:
        stand.pop(naam, None)
    pad = _eigen_cloud_pad()
    pad.parent.mkdir(parents=True, exist_ok=True)
    pad.write_text(json.dumps(stand, ensure_ascii=False, indent=1))


def kies_model(bericht: str, naam: str | None = None,
               modus: str | None = None,
               cloud_model: str | None = None) -> dict:
    """Bepaal CyberSeed-naam + model_id + modus voor een beurt.

    Default = sprout/lokaal (lichte routering: goedkoop en lokaal tenzij
    expliciet geëscaleerd). Vergrendelde naam valt terug naar sprout.
    """
    from kern import growkit_ram as ram
    naam = (naam or "sprout").lower()
    modus = (modus or "lokaal").lower()
    if naam not in _NAAM_PROMPTS:
        naam = "sprout"
    teruggevallen = False
    klasse = ram.ram_klasse()
    if modus == "lokaal" and ram.is_vergrendeld(klasse, naam):
        naam, teruggevallen = "sprout", True
    if modus == "cloud":
        eigen = eigen_cloud().get(naam, "")
        if cloud_model:
            model_id = cloud_model              # expliciete keuze (UI-dropdown of eigen)
        elif eigen:
            model_id = eigen                    # gebruiker heeft eigen id vastgezet
        else:
            model_id = ram.cloud_default(naam)  # eerste optie = default
    else:
        model_id = ram.model_voor(klasse, naam) or BASIS_MODEL_DEFAULT
    return {"naam": naam, "modus": modus, "model_id": model_id,
            "ram_klasse": klasse, "teruggevallen": teruggevallen}


def installatie_status() -> dict:
    """Per naam: model, status (geinstalleerd/niet/vergrendeld), pull-commando,
    downloadgrootte, min-RAM bij vergrendeling — UI-toestand vóór het klikken."""
    from kern import growkit_ram as ram
    s = ollama_status()
    geinstalleerd = set(s.get("modellen", []))
    klasse = ram.ram_klasse()
    manifest_ = ram.manifest()
    groottes = manifest_.get("download_grootte_gb", {})
    uit = {}
    for naam in _NAAM_PROMPTS:
        vergrendeld = ram.is_vergrendeld(klasse, naam)
        model = ram.model_voor(klasse, naam)
        regel: dict = {"model": model, "vergrendeld": vergrendeld,
                       "ram_klasse": klasse}
        if vergrendeld:
            regel["status"] = "vergrendeld"
            regel["min_ram_gb"] = ram.min_ram_gb(naam)
        elif model and (model in geinstalleerd):
            regel["status"] = "geinstalleerd"
        else:
            regel["status"] = "niet geinstalleerd"
            regel["pull_commando"] = f"ollama pull {model}"
        grootte = groottes.get(model or "", "")
        if grootte:
            regel["download_grootte"] = grootte
        uit[naam] = regel
    return uit


def chatlog_vulling() -> dict:
    """Hoe vol is de chatlog die de volgende SOUL-regeneratie voedt?
    (review-punt 5: voorspelbaar regenereren). Cap: SOUL_MAX_TEKENS."""
    pad = _basis_pad() / "chatlog.jsonl"
    if not pad.exists():
        return {"tekens": 0, "cap": SOUL_MAX_TEKENS, "procent": 0,
                "aanbevolen": False}
    tekens = sum(len(r) for r in pad.read_text().splitlines())
    procent = min(100, round(100 * tekens / SOUL_MAX_TEKENS))
    return {"tekens": tekens, "cap": SOUL_MAX_TEKENS, "procent": procent,
            "aanbevolen": procent >= 60}


def _routing_log(naam: str, modus: str, model_id: str, bericht: str) -> None:
    """Verificatie-eis: log per call met naam + model_id + modus."""
    pad = _basis_pad()
    pad.mkdir(parents=True, exist_ok=True)
    regel = {"ts": _nu().isoformat(timespec="seconds"), "naam": naam,
             "modus": modus, "model_id": model_id,
             "bericht_lengte": len(bericht)}
    with (pad / "routinglog.jsonl").open("a") as f:
        f.write(json.dumps(regel, ensure_ascii=False) + "\n")




def _openrouter_key() -> str:
    """OpenRouter-sleutel: omgeving eerst, dan ~/.hermes/.env / config."""
    import os
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return key
    for pad in (Path.home() / ".hermes" / ".env",
                Path.home() / ".hermes" / "config.yaml"):
        if pad.exists():
            try:
                for regel in pad.read_text(errors="replace").splitlines():
                    if regel.startswith("OPENROUTER_API_KEY"):
                        return regel.split("=", 1)[1].strip().strip('"\'')
                    if "openrouter" in regel.lower() and "key" in regel.lower():
                        deel = regel.split(":", 1)[-1].strip()
                        if deel and not deel.startswith("sk-or"):
                            continue
                        if deel.startswith("sk-or"):
                            return deel
            except OSError:
                continue
    return ""


def _openrouter_chat(model: str, systeem: str, bericht: str, van: str) -> str:
    """Frontier-cloud via OpenRouter (bestaande koppeling, eigen sleutel)."""
    key = _openrouter_key()
    if not key:
        raise ConnectionError(
            "Geen OpenRouter-sleutel gevonden — stel die in via "
            "Instellingen ▸ AI-providers of zet OPENROUTER_API_KEY.")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": systeem},
            {"role": "user",
             "content": f"[van: {van or 'onbekend'}] {bericht}"},
        ],
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read())
    except (OSError, urllib.error.URLError) as e:
        raise ConnectionError(f"OpenRouter onbereikbaar: {e}")
    try:
        return data["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        raise ConnectionError(f"Ongeldig OpenRouter-antwoord: {e}")


def chat(bericht: str, *, van: str = "", model: str = "",
         naam: str | None = None, modus: str | None = None,
         cloud_model: str | None = None) -> str:
    """Eén beurt: gekozen naam+prompt als system (aangevuld met SOUL voor
    root+), bericht erin, antwoord terug + gelogd + routinglog."""
    keuze = kies_model(bericht, naam=naam, modus=modus,
                       cloud_model=cloud_model)
    naam = keuze["naam"]
    modus = keuze["modus"]
    model = model or keuze["model_id"]
    _routing_log(naam, modus, model, bericht)

    naam_prompt = _NAAM_PROMPTS[naam]
    soul = soul_lees()
    if naam in ("root", "jungle", "amazone") and not soul:
        verfris_soul()
        soul = soul_lees()
    systeem = naam_prompt if not soul or naam == "sprout" else f"{naam_prompt}\n\n# SOUL-snapshot\n{soul}"
    body = {
        "model": model,
        "keep_alive": "24h",
        "stream": False,
        "messages": [
            {"role": "system", "content": systeem},
            {"role": "user",
             "content": f"[van: {van or 'onbekend'}] {bericht}"},
        ],
    }  # lokaal; cloud bouwt zijn eigen body in _openrouter_chat
    if modus == "cloud":
        antw = _openrouter_chat(model, systeem, bericht, van)
    else:
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
