"""GrowKit prompt-bibliotheek (roadmap 5 sept) — lees-laag over de gecureerde
prompts uit de privé-repo audit-prompt-bibliotheek.

Letterlijk overgenomen (kern/data/prompt_bibliotheek.json); deze module
leest, filtert en zoekt — ze genereert of herschrijft niets. Curation
blijft bij de mens in de bron-repo; hier komt een nieuwe export binnen
als nieuw data-bestand (append van inhoud, nooit herschrijven van prompts).
"""
import json
from pathlib import Path

DATA_PAD = Path(__file__).resolve().parent / "data" / "prompt_bibliotheek.json"

_SECTIES = {"public", "custom_infra"}


def _laad() -> dict:
    try:
        return json.loads(DATA_PAD.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ValueError(
            f"prompt-bibliotheek ontbreekt: {DATA_PAD}") from e
    except json.JSONDecodeError as e:
        raise ValueError(
            "prompt-bibliotheek is geen geldige JSON — herstel het "
            "data-bestand uit de bron-repo") from e


def bibliotheek(*, domein: int | None = None, sectie: str | None = None,
                zoek: str | None = None, prompt_id: str | None = None) -> dict:
    """Geef domeinen + gefilterde prompts; filtert op domein, sectie, zoek-
    tekst (titel/tags/scope/role/content) of een enkel prompt-id."""
    data = _laad()
    prompts = data["prompts"]

    if prompt_id is not None:
        gevonden = [p for p in prompts if p.get("id") == prompt_id]
        if not gevonden:
            raise ValueError(
                f"onbekend prompt-id: {prompt_id!r} — kies uit de lijst "
                "(commando prompts zonder filters)")
        return {"domains": data["domains"], "prompts": gevonden}

    if sectie is not None:
        if sectie not in _SECTIES:
            raise ValueError(
                f"onbekende sectie: {sectie!r} — kies uit: "
                + ", ".join(sorted(_SECTIES)))
        prompts = [p for p in prompts if p.get("section") == sectie]

    if domein is not None:
        domein_ids = {d["id"] for d in data["domains"]}
        if domein not in domein_ids:
            raise ValueError(
                f"onbekend domein: {domein!r} — kies uit: "
                + ", ".join(str(i) for i in sorted(domein_ids)))
        prompts = [p for p in prompts if p.get("domainId") == domein]

    if zoek:
        naald = zoek.lower().strip()
        if naald:
            prompts = [
                p for p in prompts
                if naald in " ".join(str(p.get(k, "")) for k in
                                     ("title", "tags", "scope", "role",
                                      "content")).lower()]

    return {"domains": data["domains"], "prompts": prompts}
