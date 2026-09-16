"""GrowKit Skills-beheer fase A1 (ZT-6) — skills-kern: lezen, schrijven,
valideren over twee bronnen (Mac-lokaal + VPS-profiel).

Append-only geest: vóór elk overschrijven eerst een backup
`SKILL.backup-<timestamp>.md` naast het bestand. Niets wordt gewist.

Secrets-regel: `valideer()` weigert inhoud met API-key-patronen —
keys horen niet in skills, en nooit in de app.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any

# Standaardbronnen — overschrijfbaar via de bronnen-parameter (tests)
STANDAARD_BRONNEN: dict[str, dict[str, str]] = {
    # 13 sept: pad gecorrigeerd — skills leven in ~/.hermes/skills, niet ~/hermes/skills
    "mac": {"pad": os.path.expanduser("~/.hermes/skills")},
    "vps": {"pad": os.path.join("~", ".hermes", "profiles", "zero-trust", "skills")},
}

_KEY_PATRONEN = re.compile(
    r"sk-[A-Za-z0-9]{16,}"          # OpenAI-stijl
    r"|ghp_[A-Za-z0-9]{20,}"        # GitHub-token
    r"|AKIA[0-9A-Z]{16}"            # AWS access key
    r"|xox[baprs]-[0-9A-Za-z-]{10,}"  # Slack-token
    r"|AIza[0-9A-Za-z\-_]{30,}",    # Google API key
)


def lijst_bron(*, bronnen: dict | None = None) -> list[dict]:
    """De beschikbare skill-bronnen (id + pad + of de map bestaat)."""
    uit: list[dict] = []
    for bron_id, spec in (bronnen or STANDAARD_BRONNEN).items():
        pad = spec["pad"]
        uit.append({
            "id": bron_id,
            "pad": pad,
            "bestaat": os.path.isdir(pad),
        })
    return uit


def _skillpad(bron: str, naam: str, bronnen: dict | None) -> str:
    spec = (bronnen or STANDAARD_BRONNEN)[bron]
    return os.path.join(spec["pad"], naam, "SKILL.md")


def lees(bron: str, naam: str, *, bronnen: dict | None = None) -> str | None:
    """Exacte SKILL.md-inhoud van <bron>/<naam>; None als hij niet bestaat."""
    pad = _skillpad(bron, naam, bronnen)
    try:
        with open(pad, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def schrijf(bron: str, naam: str, inhoud: str, *,
            bronnen: dict | None = None,
            tijd: datetime | None = None) -> dict:
    """Schrijf SKILL.md; bij overschrijven eerst een timestamped backup."""
    pad = _skillpad(bron, naam, bronnen)
    mapnaam = os.path.dirname(pad)
    os.makedirs(mapnaam, exist_ok=True)
    backup = None
    if os.path.exists(pad):
        with open(pad, encoding="utf-8") as f:
            oud = f.read()
        ts = (tijd or datetime.now()).strftime("%Y%m%d-%H%M%S")
        backup = os.path.join(mapnaam, f"SKILL.backup-{ts}.md")
        n = 1
        while os.path.exists(backup):  # geen backup overschrijven, ooit
            n += 1
            backup = os.path.join(mapnaam, f"SKILL.backup-{ts}-{n}.md")
        with open(backup, "w", encoding="utf-8") as f:
            f.write(oud)
    with open(pad, "w", encoding="utf-8") as f:
        f.write(inhoud)
    return {"pad": pad, "backup": backup}


def valideer(inhoud: str) -> tuple[bool, str]:
    """Verplicht: frontmatter, minstens één kop, geen secrets."""
    if not isinstance(inhoud, str):
        return False, "inhoud is geen tekst"
    if not inhoud.lstrip().startswith("---"):
        return False, "frontmatter ontbreekt (moet beginnen met '---')"
    if not re.search(r"^#{1,6}\s+\S", inhoud.split("---", 2)[-1], re.M):
        return False, "geen kop (# …) gevonden"
    if _KEY_PATRONEN.search(inhoud):
        return False, "secret/api-key-patroon gevonden — geweigerd"
    return True, "ok"
