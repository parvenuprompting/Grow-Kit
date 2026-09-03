"""GrowKit oerwoud — geboortebewijs, boom-register, doorstroom (spec §13).

Eén brein, vele bomen: elke boom meldt zich aan in het register van het
brein, stuurt VOORSTELLEN append-only door en leest het brein alleen-lezen.
De drift-guard (§13) is hard: omgevings-specifieke staat reist nooit mee.
"""
import datetime
import json
import os
import platform
import re
import uuid
from pathlib import Path

_VERPLICHTE_VELDEN = ("boom_id", "profiel", "machine", "locatie", "geplant_op")
_ONTVANGEN_VOORSTEL = re.compile(
    r"^VOORSTEL-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-")


def _nu() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def oerwoud_staat_pad() -> Path:
    """Per-machine staat (waar groeit het brein): ~/.growkit/oerwoud.json.
    Tests overschrijven de home via GROWKIT_OERWOUD_STAAT — nooit de echte."""
    omgeving = os.environ.get("GROWKIT_OERWOUD_STAAT")
    if omgeving:
        return Path(omgeving)
    return Path.home() / ".growkit" / "oerwoud.json"


def laad_oerwoud_staat() -> dict:
    """{'brein_pad': Path | None, 'fout': None | 'brein_onbereikbaar'}.

    Wijst de staat naar een brein dat niet (meer) bestaat, dan is dat een
    expliciete foutstatus: de mens wordt geroepen — er is géén fallback naar
    'nieuw brein', dat zou een bestaand oerwoud onbedoeld splitsen.
    """
    pad = oerwoud_staat_pad()
    if not pad.exists():
        return {"brein_pad": None, "fout": None}
    try:
        staat = json.loads(pad.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"oerwoud-staat {pad} is corrupt — roep de mens: {e}") from e
    brein_pad = Path(staat["brein_pad"]) if staat.get("brein_pad") else None
    fout = "brein_onbereikbaar" if brein_pad and not brein_pad.exists() else None
    return {"brein_pad": brein_pad, "fout": fout}


def sla_brein_pad(brein_pad: Path) -> None:
    pad = oerwoud_staat_pad()
    pad.parent.mkdir(parents=True, exist_ok=True)
    pad.write_text(json.dumps({"brein_pad": str(brein_pad)}, indent=2) + "\n", encoding="utf-8")


def _eerste_logboek_tijdstip(logboek: Path) -> str:
    """Het oudste logboek-tijdstip — bij migratie de werkelijke geboortedatum."""
    if not logboek.exists():
        raise ValueError("geen logboek — migratie kan de geboortedatum niet terugrekenen")
    try:
        entries = json.loads(logboek.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"boom-logboek is corrupt — migratie gestopt, roep de mens: {e}") from e
    if not entries or not entries[0].get("tijdstip"):
        raise ValueError("logboek bevat geen tijdstip — migratie kan de geboortedatum niet vaststellen")
    return entries[0]["tijdstip"]


def migratie_en_registratie(doel: Path, logboek: Path, brein_pad: Path | None = None,
                            invoer_fn=input) -> int:
    """Migratie van een oude boom (fase 1-4): geboortebewijs volmaken met
    geplant_op teruggerekend uit de eerste logboek-entry, daarna registreren
    bij het bekende brein. Weigering of een kapot logboek → geen registratie,
    geen overschrijven."""
    antwoord = invoer_fn(
        "  Geboortebewijs is van vóór fase 5 — volmaken met de oorspronkelijke geboortedatum? (ja / nee): "
    ).strip().lower()
    if antwoord != "ja":
        print("  Geen migratie — geen registratie.")
        return 1
    try:
        geboorte_tijdstip = _eerste_logboek_tijdstip(logboek)
        vul_geboortebewijs(doel / "geboortebewijs.json", geplant_op=geboorte_tijdstip)
        log_geboorte_entry(logboek, "geboortebewijs gemigreerd: volgemaakt met de "
                                    "oorspronkelijke geboortedatum uit het logboek")
    except ValueError as e:
        print(f"  {e}")
        return 1
    if brein_pad is None:
        brein_pad = laad_oerwoud_staat()["brein_pad"]
        if brein_pad is None:
            return 0
    return _registreer_in_brein(doel, brein_pad)


def _registreer_in_brein(doel: Path, brein_pad: Path, is_brein: bool = False) -> int:
    meld_geboorte(brein_pad / "register" / "bomen.json", doel / "geboortebewijs.json",
                  is_brein=is_brein)
    return 0


def registreer_nieuwe_boom(doel: Path, invoer_fn=input) -> int:
    """Post-plant (§13): de geboorte aanmelden bij het oerwoud.

    Brein onbekend → één vraag (pad / leeg = deze boom wordt het brein /
    nee = niet registreren). Brein bekend → direct registreren (machine-feit).
    Brein onbereikbaar → de mens kiest: pad corrigeren of afbreken.
    """
    staat = laad_oerwoud_staat()
    if staat["fout"] == "brein_onbereikbaar":
        print(f"  Het brein op {staat['brein_pad']} is niet bereikbaar (verplaatst of weg?)")
        keuze = invoer_fn("  Brein-pad corrigeren (c) of afbreken (a)? ").strip().lower()
        if keuze == "c":
            nieuw = invoer_fn("  Waar groeit het brein nu? (pad): ").strip()
            brein_pad = Path(nieuw).expanduser().resolve()
            if not brein_pad.exists():
                print("  Dit pad bestaat niet — geen registratie.")
                return 1
            sla_brein_pad(brein_pad)
            return _registreer_in_brein(doel, brein_pad)
        print("  Afgebroken — het bestaande oerwoud blijft staan.")
        return 1
    brein_pad = staat["brein_pad"]
    if brein_pad is None:
        antwoord = invoer_fn(
            "  Waar groeit je brein? (pad / leeg = deze boom wordt het brein / nee = niet registreren): "
        ).strip()
        if antwoord.lower() == "nee":
            print("  Niet geregistreerd — niets opgeslagen.")
            return 1
        if antwoord == "":
            brein_pad = doel.resolve()
            sla_brein_pad(brein_pad)
            return _registreer_in_brein(doel, brein_pad, is_brein=True)
        brein_pad = Path(antwoord).expanduser().resolve()
        if not brein_pad.exists():
            print("  Dit brein-pad bestaat niet — geen registratie, niets opgeslagen.")
            return 1
        sla_brein_pad(brein_pad)
        return _registreer_in_brein(doel, brein_pad)
    return _registreer_in_brein(doel, brein_pad)


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
    if not bewijs_pad.exists() or not is_voor_fase5(bewijs_pad):
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


def stuur_voorstellen(boom_doel: Path, brein_pad: Path) -> tuple[int, list[str]]:
    """Stuur gemarkeerde VOORSTELLEN append-only naar de brein-inbox (§13).

    Drift-guard: uitsluitend bestanden met de prefix `VOORSTEL-` reizen —
    logboeken, geboortebewijzen en willekeurige bestanden blijven thuis.
    Reeds verzonden bestanden (logboek-check) worden overgeslagen; een
    naam-collisie in de brein-inbox wordt geweigerd, nooit overschreven.
    """
    boom_doel = boom_doel.resolve()
    brein_pad = brein_pad.resolve()
    if not brein_pad.exists() or not (brein_pad / "inbox").exists():
        raise ValueError(f"brein {brein_pad} is onbereikbaar of heeft geen inbox — roep de mens")
    inbox = boom_doel / "inbox"
    if brein_pad == boom_doel:
        return 0, []
    if not inbox.exists():
        return 0, []
    bewijs_pad = boom_doel / "geboortebewijs.json"
    bevindingen = controleer_geboortebewijs(bewijs_pad)
    if bevindingen:
        raise ValueError("geboortebewijs ongeldig — " + "; ".join(bevindingen))
    boom_id = json.loads(bewijs_pad.read_text(encoding="utf-8"))["boom_id"]

    verzonden = set()
    logboek = boom_doel / "logboek.json"
    if logboek.exists():
        for entry in json.loads(logboek.read_text(encoding="utf-8")):
            if entry.get("type") == "doorstroom":
                verzonden.add(entry.get("bewijs", "").split(" → ")[0])

    namen = []
    for bestand in sorted(inbox.iterdir()):
        naam = bestand.name
        if not naam.startswith("VOORSTEL-") or not bestand.is_file():
            continue
        if naam in verzonden:
            continue
        doel_naam = f"VOORSTEL-{boom_id}-{naam.removeprefix('VOORSTEL-')}"
        doel_bestand = brein_pad / "inbox" / doel_naam
        if doel_bestand.exists():
            raise ValueError(f"collisie in de brein-inbox: {doel_naam} bestaat — nooit overschrijven")
        doel_bestand.write_text(bestand.read_text(encoding="utf-8"), encoding="utf-8")
        log_gebeurtenis(logboek, f"{naam} → {doel_bestand.name}")
        namen.append(doel_bestand.name)
    return len(namen), namen


def log_gebeurtenis(logboek: Path, bewijstekst: str) -> None:
    """Append-only gebeurtenis in het boom-logboek (doorstroom e.d.)."""
    entries = json.loads(logboek.read_text(encoding="utf-8")) if logboek.exists() else []
    entries.append({
        "type": "doorstroom",
        "stap": "oerwoud",
        "status": "geslaagd",
        "bewijs": bewijstekst,
        "tijdstip": _nu(),
    })
    logboek.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def status_data(doel: Path) -> dict:
    """Puwe status-gegevens van een boom (§13) — één bron voor loop.py én de
    adapter. Retourneert identiteit, register, tellers en de laatste
    mijlpaal/faal; problemen komen als 'fout' (nette tekst) of 'melding'
    terug, nooit als exceptie."""
    doel = doel.resolve()
    bewijs_pad = doel / "geboortebewijs.json"
    logboek = doel / "logboek.json"
    data = {"identiteit": None, "voor_fase5": False, "melding": None, "fout": None,
            "register": {"brein_pad": None, "status": None, "fout": None},
            "tellers": {"wachtend": 0, "verzonden": 0},
            "laatste_mijlpaal_faal": None}
    if not bewijs_pad.exists():
        data["melding"] = "geen geboortebewijs in deze boom — de status kan de identiteit niet tonen"
        return data
    data["voor_fase5"] = is_voor_fase5(bewijs_pad)
    if not data["voor_fase5"]:
        data["identiteit"] = json.loads(bewijs_pad.read_text(encoding="utf-8"))

    try:
        entries = json.loads(logboek.read_text(encoding="utf-8")) if logboek.exists() else []
    except (json.JSONDecodeError, OSError) as e:
        data["fout"] = f"boom-logboek {logboek} is corrupt — roep de mens, nooit auto-repareren: {e}"
        return data
    verzonden = {entry.get("bewijs", "").split(" → ")[0]
                 for entry in entries if entry.get("type") == "doorstroom"}
    inbox = doel / "inbox"
    bestanden = [p.name for p in inbox.iterdir()
                 if p.name.startswith("VOORSTEL-") and p.is_file()] if inbox.exists() else []
    eigen = [n for n in bestanden if not _ONTVANGEN_VOORSTEL.match(n)]
    data["tellers"] = {"wachtend": len([n for n in eigen if n not in verzonden]),
                       "verzonden": len(verzonden)}
    for entry in reversed(entries):
        if entry.get("type") == "mijlpaal" or entry.get("status") == "gefaald":
            data["laatste_mijlpaal_faal"] = {"stap": entry.get("stap", "?"),
                                             "status": entry.get("status", "?"),
                                             "tijdstip": entry.get("tijdstip", "?")}
            break

    try:
        staat = laad_oerwoud_staat()
    except ValueError as e:
        data["fout"] = str(e)
        return data
    brein_pad = staat["brein_pad"]
    data["register"] = {"brein_pad": str(brein_pad) if brein_pad else None,
                        "status": None, "fout": staat["fout"]}
    if staat["fout"] == "brein_onbereikbaar":
        return data
    if brein_pad:
        try:
            register = lees_register(brein_pad / "register" / "bomen.json")
        except ValueError as e:
            data["fout"] = str(e)
            return data
        boom_id = data["identiteit"]["boom_id"] if data["identiteit"] else None
        data["register"]["status"] = recentste_status(register, boom_id) if boom_id else None
    return data


def brein_opties(brein_pad: Path) -> list[str]:
    """Alleen-lezen vliegwiel (§11.2): mapnamen uit projecten/ van het brein,
    max. 5, alfabetisch. Geen brein of lege map → lege lijst. Opties zijn
    advies voor de formulieren — nooit uitvoer."""
    projecten = brein_pad / "projecten"
    if not projecten.exists():
        return []
    return sorted(p.name for p in projecten.iterdir() if p.is_dir())[:5]


def lees_register(pad: Path) -> list[dict]:
    """Lees het boom-register; afwezig is een leeg oerwoud."""
    if not pad.exists():
        return []
    try:
        return json.loads(pad.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"boom-register {pad} is corrupt — roep de mens, nooit auto-repareren: {e}") from e


def _schrijf_entry(pad: Path, entry: dict) -> None:
    """Append-only helper: het register krijgt alleen nieuwe entries."""
    pad.parent.mkdir(parents=True, exist_ok=True)
    entries = lees_register(pad)
    entries.append(entry)
    pad.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def meld_geboorte(register_pad: Path, bewijs_pad: Path, is_brein: bool = False) -> dict:
    """Registreer een geboorte in het register van het brein.

    Verwijst naar een geldig, gecontroleerd geboortebewijs; een boom die al
    actief geregistreerd staat wordt geweigerd (na deregistratie mag hij
    terug als type 'registratie')."""
    bevindingen = controleer_geboortebewijs(bewijs_pad)
    if bevindingen:
        raise ValueError("geboortebewijs ongeldig — " + "; ".join(bevindingen))
    bewijs = json.loads(bewijs_pad.read_text(encoding="utf-8"))
    boom_id = bewijs["boom_id"]
    vorige = recentste_status(lees_register(register_pad), boom_id)
    if vorige in ("geboorte", "registratie"):
        raise ValueError(f"boom {boom_id} staat al in het register — geen dubbele geboorte")
    entry = {
        "type": "registratie" if vorige == "gederegistreerd" else "geboorte",
        "boom_id": boom_id,
        "profiel": bewijs["profiel"],
        "machine": bewijs["machine"],
        "locatie": bewijs["locatie"],
        "geplant_op": bewijs["geplant_op"],
        "tijdstip": _nu(),
    }
    if is_brein:
        entry["is_brein"] = True
    _schrijf_entry(register_pad, entry)
    return entry


def meld_deregistratie(register_pad: Path, boom_id: str, reden: str) -> dict:
    """Vervolg-entry door de mens: de boom telt niet meer als actief —
    niets wordt verwijderd, de geschiedenis blijft intact."""
    if recentste_status(lees_register(register_pad), boom_id) is None:
        raise ValueError(f"boom {boom_id} staat niet in het register — deregistratie bestaat niet")
    entry = {
        "type": "deregistratie",
        "boom_id": boom_id,
        "bewijs": reden,
        "tijdstip": _nu(),
    }
    _schrijf_entry(register_pad, entry)
    return entry


def recentste_status(register: list[dict], boom_id: str) -> str | None:
    """Laatste status van een boom: 'geboorte'/'registratie' (actief),
    'gederegistreerd', of None als de boom onbekend is."""
    laatste = None
    for entry in register:
        if entry.get("boom_id") == boom_id:
            laatste = entry.get("type")
    if laatste in ("geboorte", "registratie"):
        return laatste
    if laatste == "deregistratie":
        return "gederegistreerd"
    return None
