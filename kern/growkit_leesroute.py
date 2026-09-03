"""GrowKit leesroute-afdwinging — per fase alleen de content die de agent mag zien.

De leesroute is geen gedragsadvies maar een grens (spec §5): wat het script
niet vrijgeeft, kan de agent niet lezen. Voorkeursimplementatie: directe
content-injectie, geen pad-verwijzing.
"""
import json
from pathlib import Path


def _lees(pad: Path) -> str:
    return pad.read_text(encoding="utf-8")


def fase_content(fase: int, context: dict) -> str:
    """Geef uitsluitend de inhoud terug die bij deze fase hoort.

    context:
      fase 0: {"repo": Path}
      fase 1: {"repo": Path}
      fase 2: {"repo": Path, "profiel": str, "stap_index": int}
      fase 3: {"repo": Path}
    """
    repo = context["repo"]
    if fase == 0:
        return _lees(repo / "SEED.md")
    if fase == 1:
        return _lees(repo / "profielen" / "INDEX.md")
    if fase == 2:
        profiel_pad = repo / "profielen" / context["profiel"] / "profiel.json"
        profiel = json.loads(_lees(profiel_pad))
        stap = profiel["stappen"][context["stap_index"]]
        return json.dumps(stap, indent=2, ensure_ascii=False)
    if fase == 3:
        return _lees(repo / "groei" / "SETUP.md")
    raise ValueError(f"onbekende fase: {fase!r} (geldige fasen: 0, 1, 2, 3)")
