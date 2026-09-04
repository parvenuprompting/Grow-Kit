"""OpenRouter API-kern voor de Saldo-bridge (Slice A1).

Gebruikt door de adapter; kan via GROWKIT_TEST_OPENROUTER_URL naar een
testserver wijzen (E2E), anders naar de echte API. De sleutel-waarde komt
nooit in een antwoord, uitzondering of logboek-regel.
"""
import datetime
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

_BASIS_LIVE = "https://openrouter.ai/api/v1"
_MAX_DAYS = 31
_STANDAARD_DAYS = 7


def _nu() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def basis_url() -> str:
    return os.environ.get("GROWKIT_TEST_OPENROUTER_URL", _BASIS_LIVE).rstrip("/")


def los_sleutel_op(sleutel_pad: str | None) -> str:
    """Sleutel-resolutie: expliciet pad → ~/.growkit/openrouter_key → omgeving.
    Ontbreekt alles → ValueError (nette fout voor de mens)."""
    kandidaten: list[Path] = []
    if sleutel_pad:
        kandidaten.append(Path(sleutel_pad).expanduser())
    kandidaten.append(Path.home() / ".growkit" / "openrouter_key")
    for pad in kandidaten:
        if pad.exists():
            waarde = pad.read_text(encoding="utf-8").strip()
            if waarde:
                return waarde
    omgeving = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if omgeving:
        return omgeving
    raise ValueError(
        "geen OpenRouter-sleutel gevonden — zet ~/.growkit/openrouter_key "
        "(op de doelmachine, nooit in de repo of chat) of geef sleutel_pad")


def _vraag(pad: str, sleutel: str) -> dict:
    url = f"{basis_url()}{pad}"
    verzoek = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {sleutel}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(verzoek, timeout=30) as antwoord:
            return json.loads(antwoord.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ValueError("OpenRouter weigerde de sleutel (401/403) — controleer de key op de doelmachine")
        raise ValueError(f"OpenRouter API-fout (HTTP {e.code}) — probeer later opnieuw of roep de mens") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise ValueError(f"OpenRouter is niet bereikbaar — controleer de verbinding: {e}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"OpenRouter gaf geen geldig JSON — nooit gokken: {e}") from e


def saldo(sleutel: str) -> dict:
    """Actueel saldo via /credits: {total_credits, total_usage}."""
    data = _vraag("/credits", sleutel).get("data") or {}
    totaal = data.get("total_credits")
    gebruikt = data.get("total_usage")
    if totaal is None or gebruikt is None:
        raise ValueError("OpenRouter /credits gaf onverwachte velden — nooit gokken")
    return {"totaal": float(totaal), "gebruikt": float(gebruikt),
            "resterend": round(float(totaal) - float(gebruikt), 6),
            "bron": "openrouter", "opgevraagd": _nu()}


def verbruik(sleutel: str, dagen: int | None = None) -> dict:
    """Per-model tokenverbruik. Probeer eerst /activity (per-model); bij een
    niet-provisioning key: eerlijk terugvallen op het sleuteltotaal (/key) —
    nooit verzonnen cijfers."""
    if dagen is None:
        dagen = _STANDAARD_DAYS
    dagen = int(dagen)
    if dagen < 1 or dagen > _MAX_DAYS:
        raise ValueError(f"dagen moet tussen 1 en {_MAX_DAYS} liggen")
    datum = (datetime.datetime.now(datetime.timezone.utc)
             - datetime.timedelta(days=dagen)).strftime("%Y-%m-%d")
    try:
        return verbruik_activity(sleutel, datum, dagen)
    except ValueError as e:
        if "401/403" in str(e):
            key_info = _vraag("/key", sleutel).get("data") or {}
            totaal_gebruik = key_info.get("usage")
            if totaal_gebruik is None:
                raise ValueError("OpenRouter gaf geen usage-veld — nooit gokken")
            return {"periode_dagen": dagen, "vanaf": datum,
                    "modellen": [],
                    "totaal_kosten": round(float(totaal_gebruik), 6),
                    "detail": "per-model verbruik vereist een OpenRouter provisioning key; dit is het sleuteltotaal",
                    "bron": "openrouter", "opgevraagd": _nu()}
        raise


def verbruik_activity(sleutel: str, datum: str, dagen: int) -> dict:
    """Intern: /activity pagineren tot de oudste pagina binnen de periode."""
    per_model: dict[str, dict] = {}
    cursor = None
    for _ in range(20):                                   # paginatie-begrenzing
        vraag = f"/activity?date={datum}" + (f"&cursor={cursor}" if cursor else "")
        antwoord = _vraag(vraag, sleutel)
        rijen = antwoord.get("data") or []
        for rij in rijen:
            model = rij.get("model") or "onbekend"
            token = int(rij.get("tokens_prompt", 0) or 0) + int(rij.get("tokens_completion", 0) or 0)
            kosten = float(rij.get("cost", 0) or 0)
            if model not in per_model:
                per_model[model] = {"model": model, "tokens": 0, "kosten": 0.0}
            per_model[model]["tokens"] += token
            per_model[model]["kosten"] = round(per_model[model]["kosten"] + kosten, 6)
        cursor = antwoord.get("next_cursor")
        if not cursor:
            break
    modellen = sorted(per_model.values(), key=lambda m: m["kosten"], reverse=True)
    totaal = round(sum(m["kosten"] for m in modellen), 6)
    return {"periode_dagen": dagen, "vanaf": datum, "modellen": modellen,
            "totaal_kosten": totaal, "bron": "openrouter", "opgevraagd": _nu()}
