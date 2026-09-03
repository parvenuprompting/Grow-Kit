"""GrowKit oerwoud — geboortebewijs, boom-register, doorstroom (spec §13).

Eén brein, vele bomen: elke boom meldt zich aan in het register van het
brein, stuurt VOORSTELLEN append-only door en leest het brein alleen-lezen.
De drift-guard (§13) is hard: omgevings-specifieke staat reist nooit mee.
"""
import datetime
import json
import platform
import uuid
from pathlib import Path

_VERPLICHTE_VELDEN = ("boom_id", "profiel", "machine", "locatie", "geplant_op")


def _nu() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def is_voor_fase5(bestand: Path) -> bool:
    """True als het geboortebewijs ontbreekt of nog placeholders heeft
    (bomen geplant vóór fase 5) — migreerbaar via het migratie-pad (taak 3)."""
    if not bestand.exists():
        return True
    try:
        bewijs = json.loads(bestand.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return True
    return "{{" in json.dumps(bewijs)


def vul_geboortebewijs(bestand: Path, geplant_op: str | None = None) -> dict:
    """Vul de placeholders met feiten. geplant_op is expliciet mee te geven
    voor migratie van oude bomen (teruggerekend uit de eerste logboek-entry);
    standaard is het plant-moment nu."""
    bewijs = json.loads(bestand.read_text(encoding="utf-8"))
    bewijs["boom_id"] = str(uuid.uuid4())
    bewijs["machine"] = platform.node()
    bewijs["locatie"] = str(bestand.parent.resolve())
    bewijs["geplant_op"] = geplant_op or _nu()
    bestand.write_text(json.dumps(bewijs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return bewijs


def controleer_geboortebewijs(bestand: Path) -> list[str]:
    """Machine-controle: valide JSON, verplichte velden, geen placeholders.
    Leeg resultaat = geldig."""
    bevindingen = []
    try:
        bewijs = json.loads(bestand.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return [f"geboortebewijs {bestand} is corrupt of onleesbaar: {e}"]
    tekst = json.dumps(bewijs)
    if "{{" in tekst:
        bevindingen.append("geboortebewijs bevat nog placeholders ({{...}})")
    for veld in _VERPLICHTE_VELDEN:
        if not bewijs.get(veld):
            bevindingen.append(f"verplicht veld ontbreekt: {veld}")
    return bevindingen


def log_geboorte_entry(logboek: Path, bewijstekst: str) -> None:
    """Append-only systeem-entry over het geboortebewijs (patroon: mijlpaal)."""
    entries = json.loads(logboek.read_text(encoding="utf-8")) if logboek.exists() else []
    entries.append({
        "type": "geboorte",
        "stap": "geboortebewijs",
        "status": "geslaagd",
        "bewijs": bewijstekst,
        "tijdstip": _nu(),
    })
    logboek.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def volmaak_na_plant(doel: Path, logboek: Path) -> bool:
    """Post-plant: volgemaakt het geboortebewijs en log het bewijs.

    Idempotent: al geldig → niets doen (False, geen dubbele entry).
    Kapot logboek → de volmaking wél doen (bewijs niet weggooien) maar
    niets loggen; de mens ziet de situatie bij de volgende controle.
    """
    bewijs_pad = doel / "geboortebewijs.json"
    if not is_voor_fase5(bewijs_pad):
        return False
    vul_geboortebewijs(bewijs_pad)
    bevindingen = controleer_geboortebewijs(bewijs_pad)
    if bevindingen:
        return False
    try:
        log_geboorte_entry(logboek, "geboortebewijs volgemaakt: JSON geldig, "
                                    "verplichte velden aanwezig, geen placeholders")
    except (json.JSONDecodeError, OSError):
        return False
    return True
