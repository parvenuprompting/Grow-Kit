#!/usr/bin/env python3
"""GrowKit adapter — machine-leesbare bedienaar over de kern (fase 6, §5-geest).

De adapter is een bedienaar, nooit een machthebber: hij roept uitsluitend de
bestaande kern-functies aan (poort, motor, faalcontract blijven de bewakers)
en voert niets uit zonder expliciete bevestiging in de invoer-JSON.

Contract:
- `python3 adapter.py <commando>` — JSON in via stdin, precies één
  JSON-document uit op stdout; mens-leesbare tekst naar stderr.
- Fouten: {"ok": false, "fout": "<NL>"} met exit 1 — nooit een traceback.
- Stateless: geen sessie-staat tussen aanroepen.
"""
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).parent.resolve()
sys.path.insert(0, str(REPO))

from kern import growkit_oerwoud  # noqa: E402
from seed import laad_profielen  # noqa: E402


class AdapterFout(Exception):
    """Nette adapter-fout: landt als {"ok": false, "fout": ...} met exit 1."""


def _lees_invoer() -> dict:
    ruw = sys.stdin.read().strip()
    if not ruw:
        return {}
    try:
        invoer = json.loads(ruw)
    except json.JSONDecodeError as e:
        raise AdapterFout(f"stdin is geen geldige JSON: {e}") from e
    if not isinstance(invoer, dict):
        raise AdapterFout("stdin-JSON moet een object zijn")
    return invoer


def _doel_uit(invoer: dict) -> Path:
    doel = str(invoer.get("doel", "")).strip()
    if not doel:
        raise AdapterFout("verplicht veld ontbreekt: doel")
    return Path(doel).expanduser().resolve()


def cmd_status(invoer: dict) -> dict:
    data = growkit_oerwoud.status_data(_doel_uit(invoer))
    if data.get("fout"):
        raise AdapterFout(data["fout"])
    return {"ok": True, "data": data}


def cmd_hervat(invoer: dict) -> dict:
    import contextlib

    from kern import growkit_hervat, growkit_motor

    doel = _doel_uit(invoer)
    logboek = doel / "logboek.json"
    bewijs_pad = doel / "geboortebewijs.json"
    naam = str(invoer.get("profiel", "")).strip()
    if not naam:
        if not bewijs_pad.exists():
            raise AdapterFout("geen geboortebewijs in deze boom — geef 'profiel' expliciet "
                              "in de invoer (de app vraagt het aan de mens)")
        try:
            naam = json.loads(bewijs_pad.read_text(encoding="utf-8"))["profiel"]
        except (json.JSONDecodeError, KeyError) as e:
            raise AdapterFout(f"geboortebewijs onleesbaar ({e}) — geef 'profiel' expliciet") from e
    profiel = growkit_motor.vervang_growkit_pad(_laad_profiel(naam), REPO)
    resultaat = growkit_hervat.reconstructie(logboek, profiel)
    if resultaat.get("fout") == "corrupt_logboek":
        raise AdapterFout("boom-logboek is corrupt — roep de mens, nooit auto-repareren")
    restdraai = [s for s in profiel.get("stappen", [])
                 if resultaat["stappen"][s["id"]]["beslissing"] in ("heraanbieden", "uitvoeren")]
    if not invoer.get("bevestig"):
        return {"ok": True, "data": {"herstartpunt": resultaat["herstartpunt"],
                                     "stappen": resultaat["stappen"],
                                     "restdraai": [s["id"] for s in restdraai],
                                     "bevestiging_vereist": True}}
    if not restdraai:
        return {"ok": True, "data": {"melding": "Niets te hervatten — alle stappen zijn "
                                                "geslaagd of wachten op ratificatie."}}
    with contextlib.redirect_stdout(sys.stderr):
        from kern.growkit_review import laad_reviewconfig
        reviewconfig = laad_reviewconfig(REPO / "reviewconfig.json")
        geslaagd = growkit_motor.voer_uit({**profiel, "stappen": restdraai}, doel, logboek,
                                          Path(__file__).parent / "profielen" / naam / "sjablonen",
                                          reviewconfig=reviewconfig)
        if geslaagd:
            growkit_oerwoud.volmaak_na_plant(doel, logboek)
    stappen = [{"id": e["stap"], "status": e["status"], "bewijs": e["bewijs"],
                "review_rol": e.get("review_rol"), "review_oordeel": e.get("review_oordeel")}
               for e in json.loads(logboek.read_text(encoding="utf-8"))
               if e.get("stap", "").startswith("stap-")]
    if not geslaagd:
        raise AdapterFaal("restdraai faalde na alternatief — roep de mens", stappen)
    return {"ok": True, "data": {"stappen": stappen,
                                 "herstartpunt": resultaat["herstartpunt"]}}


def cmd_taak(invoer: dict) -> dict:
    from kern.growkit_taken import laad_taken, valideer_taak, voer_taak_uit

    doel = _doel_uit(invoer)
    taken = laad_taken(doel / "takenlijst.json")
    if not taken:
        return {"ok": True, "data": {"taken": []}}
    lijst = [{"id": t.get("id", "onbekend"), "titel": t.get("titel", ""),
              "geldig": not valideer_taak(t)} for t in taken]
    if not invoer.get("bevestig"):
        return {"ok": True, "data": {"taken": lijst, "bevestiging_vereist": True}}
    taak_id = str(invoer.get("taak_id", "")).strip()
    if not taak_id:
        raise AdapterFout("bevestigde taak-uitvoering vereist taak_id")
    taak = next((t for t in taken if t.get("id") == taak_id), None)
    if taak is None:
        raise AdapterFout(f"taak '{taak_id}' bestaat niet in de takenlijst")
    import contextlib

    from kern.growkit_review import laad_reviewconfig
    reviewconfig = laad_reviewconfig(REPO / "reviewconfig.json")
    governor_pad = doel / "governor.json"
    agent = str(invoer.get("agent", "")).strip() or None
    growkit_oerwoud.log_run_latch(doel / "logboek.json", "gestart")
    with contextlib.redirect_stdout(sys.stderr):
        geslaagd, bevindingen = voer_taak_uit(
            doel, taak, reviewconfig=reviewconfig,
            governor_pad=governor_pad if agent else None,
            agent=agent)
    growkit_oerwoud.log_run_latch(doel / "logboek.json", "beeindigd")
    if bevindingen:
        raise AdapterFout("deze taak bestaat niet: " + "; ".join(bevindingen))
    if not geslaagd:
        raise AdapterFaal(f"taak {taak_id} faalde na alternatief — roep de mens",
                          [{"id": taak_id, "status": "gefaald"}])
    return {"ok": True, "data": {"taak": taak_id, "status": "geslaagd"}}


def cmd_profielen(invoer: dict) -> dict:
    profielen = [{"naam": p["profiel"], "beschrijving": p.get("beschrijving", "")}
                 for p in laad_profielen() if p.get("status") == "bewezen-vorm"]
    staat = growkit_oerwoud.laad_oerwoud_staat()
    opties = []
    if staat["brein_pad"] and not staat["fout"]:
        opties = [{"naam": n, "bron": "uit je brein"}
                  for n in growkit_oerwoud.brein_opties(staat["brein_pad"])]
    return {"ok": True, "data": {"profielen": profielen, "brein_opties": opties}}


class AdapterFaal(Exception):
    """Motor-faal: {"ok": false, "fout", "stappen"} met exit 2 (faalcontract)."""

    def __init__(self, fout: str, stappen: list[dict]):
        super().__init__(fout)
        self.stappen = stappen


def _laad_profiel(naam: str) -> dict:
    for p in laad_profielen():
        if p["profiel"] == naam:
            return p
    bekenden = ", ".join(p["profiel"] for p in laad_profielen())
    raise AdapterFout(f"onbekend profiel '{naam}' — kies uit: {bekenden}")


def cmd_plant(invoer: dict) -> dict:
    import contextlib

    from kern import growkit_motor, growkit_poort

    naam = str(invoer.get("profiel", "")).strip()
    if not naam:
        raise AdapterFout("verplicht veld ontbreekt: profiel")
    doel = _doel_uit(invoer)
    profiel = _laad_profiel(naam)
    ok, tekst, _ = growkit_poort.beoordeel_invoer({"profiel": naam, "doel": str(doel)},
                                                  "kiemkeuze")
    if not ok:
        raise AdapterFout(tekst)
    if not invoer.get("bevestig"):
        return {"ok": True, "data": {"concept": tekst, "bevestiging_vereist": True}}
    if growkit_poort.mijlpaal_nodig(profiel) and not invoer.get("mijlpaal_bevestigd"):
        # beslissing 7a (fase 6.1): het §11.4-blok retourneren, niets uitvoeren —
        # de app toont het en her-vraagt met mijlpaal_bevestigd: true
        from seed import mijlpaal_blok
        blok = mijlpaal_blok(profiel, doel, doel / "logboek.json")
        return {"ok": True, "data": {"mijlpaal_blok": blok,
                                     "status": "wacht_op_mijlpaal_bevestiging",
                                     "uitgevoerd": False},
                "bevestiging_vereist": True}

    brein_keuze = str(invoer.get("brein", "auto"))
    if brein_keuze not in ("auto", "pad", "geen"):
        raise AdapterFout("brein moet 'auto', 'pad' of 'geen' zijn")
    brein_pad = None
    registratie = "geen"
    if brein_keuze == "auto":
        staat = growkit_oerwoud.laad_oerwoud_staat()
        if staat["fout"] == "brein_onbereikbaar":
            raise AdapterFout(f"het brein op {staat['brein_pad']} is niet bereikbaar — roep de mens")
        if staat["brein_pad"] is None:
            return {"ok": True, "data": {"concept": tekst, "uitgevoerd": False},
                    "vragen": [{"vraag": "waar groeit je brein?",
                                "opties": ["deze boom wordt het brein", "pad opgeven",
                                           "niet registreren"]}]}
        brein_pad = staat["brein_pad"]
        registratie = "geregistreerd"
    elif brein_keuze == "pad":
        raw = str(invoer.get("brein_pad", "")).strip()
        if not raw:
            raise AdapterFout("brein 'pad' vereist brein_pad")
        brein_pad = Path(raw).expanduser().resolve()
        if not brein_pad.exists():
            raise AdapterFout(f"brein-pad {brein_pad} bestaat niet")
        growkit_oerwoud.sla_brein_pad(brein_pad)
        registratie = "geregistreerd"

    with contextlib.redirect_stdout(sys.stderr):           # mens-leesbare tekst uit stdout
        from kern.growkit_review import laad_reviewconfig
        reviewconfig = laad_reviewconfig(REPO / "reviewconfig.json")
        doel.mkdir(parents=True, exist_ok=True)
        logboek = doel / "logboek.json"
        if not logboek.exists():
            logboek.write_text("[]", encoding="utf-8")
        profiel = growkit_motor.vervang_growkit_pad(profiel, REPO)
        geslaagd = growkit_motor.voer_uit(profiel, doel, logboek,
                                          Path(__file__).parent / "profielen" / naam / "sjablonen",
                                          reviewconfig=reviewconfig)
        if geslaagd:
            growkit_oerwoud.volmaak_na_plant(doel, logboek)
            if brein_pad:
                try:
                    growkit_oerwoud.meld_geboorte(brein_pad / "register" / "bomen.json",
                                                  doel / "geboortebewijs.json")
                except ValueError as e:
                    registratie = f"mislukt: {e}"
    stappen = [{"id": e["stap"], "status": e["status"], "bewijs": e["bewijs"],
                "review_rol": e.get("review_rol"), "review_oordeel": e.get("review_oordeel")}
               for e in json.loads(logboek.read_text(encoding="utf-8"))
               if e.get("stap", "").startswith("stap-")]
    if not geslaagd:
        raise AdapterFaal("motor-faal na alternatief — roep de mens", stappen)
    return {"ok": True, "data": {"stappen": stappen, "registratie": registratie,
                                 "brein_pad": str(brein_pad) if brein_pad else None}}


def cmd_ratificeer(invoer: dict) -> dict:
    from kern import growkit_ratificatie

    doel = _doel_uit(invoer)
    logboek = doel / "logboek.json"
    wacht = growkit_ratificatie.wacht_ratificatie_stappen(logboek)
    if not invoer.get("bevestig"):
        return {"ok": True, "data": {"stappen": wacht, "bevestiging_vereist": True}}
    afkeur = []
    for afkeuring in (invoer.get("afkeur") or []):
        sid = str(afkeuring.get("stap_id", "")).strip()
        reden = str(afkeuring.get("reden", "")).strip()
        if not sid or not reden:
            raise AdapterFout("afkeur vereist stap_id én reden — zonder reden bestaat de afkeur niet")
        if sid not in wacht:
            raise AdapterFout(f"stap {sid} wacht niet op ratificatie — afkeur bestaat niet")
        afkeur.append({"stap_id": sid, "reden": reden})
    geratificeer = [] if afkeur else wacht
    geschreven = growkit_ratificatie.ratificeer_bulk(logboek, geratificeer, afkeur)
    return {"ok": True, "data": {"verwerkt": [{"stap": e["stap"], "status": e["status"]}
                                              for e in geschreven]}}


def cmd_slijp(invoer: dict) -> dict:
    """Slice 1: Dialoog-basics — vage prompt → Scope-poort → slijp-concept.

    Bedienaar, geen machthebber: alle interpretatie blijft in de poort
    (growkit_poort.beoordeel_invoer); de adapter voegt niets toe.
    De slijper-schuring wordt append-only gelogd (§11.1).
    """
    from kern import growkit_poort

    tekst = str(invoer.get("tekst", "")).strip()
    if not tekst:
        raise AdapterFout("verplicht veld ontbreekt: tekst")

    omgeving = invoer.get("omgeving")
    formulier = {"einddoel": tekst, "tekst": tekst}
    for veld in ("omgeving", "slaag_criterium"):
        waarde = invoer.get(veld)
        if isinstance(waarde, str) and waarde.strip():
            formulier[veld] = waarde.strip()
    ok, tekst_uit, vragen = growkit_poort.beoordeel_invoer(formulier, "vrije_beschrijving")

    # Append-only slijper-logboek (§11.1), zelfs bij een weigering.
    try:
        from seed import _log_slijper
        _log_slijper(tekst, tekst_uit, "geaccepteerd_concept" if ok else "geweigerd")
    except Exception:
        pass  # logboek mag de chat nooit breken; de poort-uitspraak is leidend

    if not ok:
        return {"ok": True, "data": {"geaccepteerd": False,
                                     "weigering": tekst_uit,
                                     "vragen": vragen}}
    try:
        concept = json.loads(tekst_uit)
    except json.JSONDecodeError:
        concept = {"concept": tekst_uit}
    return {"ok": True, "data": {"geaccepteerd": True, "concept": concept,
                                 "vragen": vragen}}




def cmd_bomen(invoer: dict) -> dict:
    """Boom-lijst (Slice 1): recentste register-status per boom.

    register_pad expliciet → dat register. Anders de per-machine oerwoud-
    staat: geen bekend brein → ok met een lege lijst + melding; onbereikbaar
    brein → nette fout (mens)."""
    pad = invoer.get("register_pad")
    if pad:
        register_pad = Path(pad).expanduser().resolve()
    else:
        staat = growkit_oerwoud.laad_oerwoud_staat()
        if staat["fout"] == "brein_onbereikbaar":
            raise AdapterFout(
                f"het brein op {staat['brein_pad']} is niet bereikbaar — "
                "roep de mens: pad corrigeren in Instellingen")
        if staat["brein_pad"] is None:
            return {"ok": True, "data": {"bomen": [],
                    "melding": "geen brein gekoppeld — koppel een brein in Instellingen"}}
        register_pad = staat["brein_pad"] / "register" / "bomen.json"
    try:
        data = growkit_oerwoud.bomen_overzicht(register_pad)
    except ValueError as e:
        raise AdapterFout(str(e))
    return {"ok": True, "data": data}




def cmd_levensignaal(invoer: dict) -> dict:
    """Levende status van één boom (Slice 2) uit groei/logboek.json.

    Geen zelf-rapportage: faalcontract en run-latch komen uit append-only
    entries. Ontbrekend of fout doel → nette fout; corrupt logboek → nette
    fout (mens)."""
    doel = _doel_uit(invoer)
    if not doel.exists():
        raise AdapterFout(f"boom {doel} bestaat niet — levensignaal werkt alleen op een geplante boom")
    try:
        data = growkit_oerwoud.levensignaal(doel)
    except ValueError as e:
        raise AdapterFout(str(e))
    return {"ok": True, "data": {"levensignaal": data}}




def cmd_acties(invoer: dict) -> dict:
    """Actie-menu voor de app (Slice 3): wat mag er, en waar wordt de mens
    nodig geacht? Puur lezend — de uitvoerende commando's bewaken hun eigen
    poort; dit overzicht is nooit een machtsbron."""
    doel = _doel_uit(invoer)
    if not doel.exists():
        raise AdapterFout(f"boom {doel} bestaat niet")
    try:
        data = growkit_oerwoud.acties_overzicht(doel)
    except ValueError as e:
        raise AdapterFout(str(e))
    return {"ok": True, "data": data}




def cmd_inbox(invoer: dict) -> dict:
    """VOORSTEL-items in de brein-inbox (Slice 4) — puur lezend."""
    try:
        brein_pad = growkit_oerwoud._brein_pad_van(invoer)
        data = growkit_oerwoud.inbox_items(brein_pad)
    except ValueError as e:
        raise AdapterFout(str(e))
    return {"ok": True, "data": data}





def cmd_curate(invoer: dict) -> dict:
    """Besluiten over VOORSTEL-items (Slice 4) — append-only, nooit overschrijven."""
    items = invoer.get("items")
    if not isinstance(items, list) or not items:
        raise AdapterFout("verplicht veld ontbreekt: items (lijst met besluiten)")
    try:
        brein_pad = growkit_oerwoud._brein_pad_van(invoer)
        resultaten = growkit_oerwoud.curate_items(brein_pad, items)
    except ValueError as e:
        raise AdapterFout(str(e))
    return {"ok": True, "data": {"resultaten": resultaten}}


def cmd_koppel(invoer: dict) -> dict:
    """Registreer een boom bij het gedeelde brein (Slice 5) — app-ingang voor
    meld_geboorte + sla_brein_pad. Weigeringen → nette fout (mens)."""
    doel = _doel_uit(invoer)
    if not doel.exists():
        raise AdapterFout(f"boom {doel} bestaat niet")
    brein_pad = invoer.get("brein_pad")
    try:
        data = growkit_oerwoud.koppel_boom(
            doel, Path(brein_pad).expanduser().resolve() if brein_pad else None)
    except ValueError as e:
        raise AdapterFout(str(e))
    return {"ok": True, "data": data}


def cmd_driftguard(invoer: dict) -> dict:
    """Drift-guard-rapport (Slice 5) — wat reist tussen bomen en brein,
    wat blijft per boom lokaal. Puur lezend."""
    brein_pad = invoer.get("brein_pad")
    try:
        if brein_pad:
            pad = Path(brein_pad).expanduser().resolve()
        else:
            pad = growkit_oerwoud._brein_pad_van(invoer)
            if pad is None:
                raise AdapterFout("geen brein gekoppeld — geef brein_pad of koppel eerst")
        data = growkit_oerwoud.driftguard_rapport(pad)
    except ValueError as e:
        raise AdapterFout(str(e))
    return {"ok": True, "data": data}


def cmd_stuur(invoer: dict) -> dict:
    """Stuur gemarkeerde VOORSTELLEN van een boom naar de brein-inbox (§13)
    — app-ingang voor stuur_voorstellen, drift-guard staat in de kern."""
    doel = _doel_uit(invoer)
    if not doel.exists():
        raise AdapterFout(f"boom {doel} bestaat niet")
    brein_pad = invoer.get("brein_pad")
    try:
        if brein_pad:
            pad = Path(brein_pad).expanduser().resolve()
        else:
            pad = growkit_oerwoud._brein_pad_van(invoer)
            if pad is None:
                raise AdapterFout("geen brein gekoppeld — koppel eerst een brein")
        aantal, namen = growkit_oerwoud.stuur_voorstellen(doel, pad)
    except ValueError as e:
        raise AdapterFout(str(e))
    return {"ok": True, "data": {"verzonden": aantal, "namen": namen}}


def cmd_nachtplan(invoer: dict) -> dict:
    """Nachtplan samenstellen (Slice 6). Zonder bevestiging: concept. Met
    bevestiging: append-only weggeschreven; bestaand plan → geweigerd."""
    doel = _doel_uit(invoer)
    if not doel.exists():
        raise AdapterFout(f"boom {doel} bestaat niet")
    taken_ids = invoer.get("taken")
    if not isinstance(taken_ids, list) or not taken_ids:
        raise AdapterFout("verplicht veld ontbreekt: taken (lijst met taak-ids)")
    from kern.growkit_taken import laad_taken, valideer_taak
    taken = {t.get("id"): t for t in laad_taken(doel / "takenlijst.json")}
    ontbrekend = [tid for tid in taken_ids if tid not in taken]
    if ontbrekend:
        raise AdapterFout(f"taak(s) bestaan niet in de takenlijst: {', '.join(ontbrekend)}")
    ongeldig = [taken[tid]["id"] for tid in taken_ids if valideer_taak(taken[tid])]
    if ongeldig:
        raise AdapterFout(
            f"taak(s) zonder bewijs bestaan niet en kunnen niet in het plan: {', '.join(ongeldig)}")
    if not invoer.get("bevestig"):
        return {"ok": True, "data": {
            "concept": f"nachtronde voor {doel.name} met {len(taken_ids)} taak/taken",
            "bevestiging_vereist": True,
            "plan": {"taken": taken_ids}}}
    try:
        plan = growkit_oerwoud.nachtplan_wegschrijven(doel, taken_ids)
    except ValueError as e:
        raise AdapterFout(str(e))
    return {"ok": True, "data": {"plan": plan}}


def cmd_nachtronde(invoer: dict) -> dict:
    """Voer één geplande nachtronde uit (Slice 6). Poort eerst per taak;
    append-only rondverslag; faalcontract: eerste faal eindigt de ronde
    (exit 2), geen retries."""
    doel = _doel_uit(invoer)
    if not doel.exists():
        raise AdapterFout(f"boom {doel} bestaat niet")
    plan = growkit_oerwoud.nachtplan_lezen(doel)
    if plan is None:
        raise AdapterFout("geen nachtplan — stel er eerst een samen (nachtplan)")
    if not invoer.get("bevestig"):
        return {"ok": True, "data": {"bevestiging_vereist": True,
                                     "plan": plan}}
    from kern.growkit_review import laad_reviewconfig
    from kern.growkit_taken import laad_taken, valideer_taak, voer_taak_uit
    import contextlib

    # Slice 11: nachtronde óók onder de governor — één agent draagt alle
    # nachtelijke taken binnen de gouverneursregels; zonder 'agent' verandert
    # het gedrag niet.
    nacht_agent = str(invoer.get("agent", "")).strip() or None
    governor_pad = doel / "governor.json" if nacht_agent else None

    taken = {t.get("id"): t for t in laad_taken(doel / "takenlijst.json")}
    reviewconfig = laad_reviewconfig(REPO / "reviewconfig.json")
    logboek = doel / "logboek.json"
    groei_oerwoud = growkit_oerwoud
    groei_oerwoud.log_run_latch(logboek, "gestart")
    verslag_taken = []
    ronde_geslaagd = True
    try:
        for tid in plan["taken"]:
            taak = taken.get(tid)
            if taak is None:
                verslag_taken.append({"taak": tid, "status": "gefaald",
                                      "bewijs": "taak verdwenen uit de takenlijst"})
                ronde_geslaagd = False
                break
            if valideer_taak(taak):
                verslag_taken.append({"taak": tid, "status": "gefaald",
                                      "bewijs": "poort-weigering: taak zonder bewijs bestaat niet"})
                ronde_geslaagd = False
                break
            with contextlib.redirect_stdout(sys.stderr):
                geslaagd, bevindingen = voer_taak_uit(
                    doel, taak, reviewconfig=reviewconfig,
                    governor_pad=governor_pad, agent=nacht_agent)
            status = "geslaagd" if geslaagd else "gefaald"
            verslag_taken.append({"taak": tid, "status": status,
                                  "bewijs": "; ".join(bevindingen) or "bewijs gecontroleerd"})
            if not geslaagd:
                ronde_geslaagd = False
                break
    finally:
        groei_oerwoud.log_run_latch(logboek, "beeindigd")
    groei_oerwoud.nachtronde_verslag(doel, ronde_geslaagd, verslag_taken)
    resultaat = {"geslaagd": ronde_geslaagd, "taken": verslag_taken}
    if not ronde_geslaagd:
        raise AdapterFaal("nachtronde gestopt door het faalcontract — roep de mens", [resultaat])
    return {"ok": True, "data": resultaat}


def cmd_nachtstatus(invoer: dict) -> dict:
    """Plan + rondgeschiedenis + levensignaal (Slice 6) — puur lezend,
    één bron met Slices 2 en het plan-bestand."""
    doel = _doel_uit(invoer)
    if not doel.exists():
        raise AdapterFout(f"boom {doel} bestaat niet")
    try:
        plan = growkit_oerwoud.nachtplan_lezen(doel)
        rondes_pad = doel / "nachtrondes.json"
        rondes = None
        if rondes_pad.exists():
            rondes = json.loads(rondes_pad.read_text(encoding="utf-8"))
        signaal = growkit_oerwoud.levensignaal(doel)
    except ValueError as e:
        raise AdapterFout(str(e))
    # Slice 11: ochtendrapport bevat de governor-uitslag van de nacht —
    # welke taken wachten op controle, welke zijn goedgekeurd.
    governor_pad = doel / "governor.json"
    governor = None
    if governor_pad.exists():
        try:
            reg = json.loads(governor_pad.read_text(encoding="utf-8"))
            wachtend = [{"taak": tid, "agent": t.get("agent", "?")}
                        for tid, t in reg.get("taken", {}).items()
                        if t.get("status") == "wacht_op_controle"]
            goedgekeurd = sum(1 for t in reg.get("taken", {}).values()
                              if t.get("status") == "goedgekeurd")
            meldingen = reg.get("observer_meldingen", [])[-5:]
            governor = {"wacht_op_controle": wachtend,
                        "goedgekeurd_totaal": goedgekeurd,
                        "observer_meldingen": meldingen}
        except Exception:
            governor = None
    return {"ok": True, "data": {"plan": plan, "rondes": rondes,
                                 "levensignaal": signaal, "governor": governor}}


def cmd_saldo(invoer: dict) -> dict:
    """Actueel OpenRouter-saldo (Slice A1). Sleutel via sleutel_pad,
    ~/.growkit/openrouter_key of omgeving — waarde lekt nooit."""
    from kern import growkit_openrouter
    try:
        sleutel = growkit_openrouter.los_sleutel_op(invoer.get("sleutel_pad"))
        data = growkit_openrouter.saldo(sleutel)
    except ValueError as e:
        raise AdapterFout(str(e))
    return {"ok": True, "data": data}


def cmd_verbruik(invoer: dict) -> dict:
    """Tokenverbruik per model (Slice A1), gesorteerd op kosten."""
    from kern import growkit_openrouter
    try:
        sleutel = growkit_openrouter.los_sleutel_op(invoer.get("sleutel_pad"))
        data = growkit_openrouter.verbruik(sleutel, invoer.get("dagen"))
    except ValueError as e:
        raise AdapterFout(str(e))
    return {"ok": True, "data": data}

def cmd_governor(invoer: dict) -> dict:
    """Agent-governor via de adapter: status, aanmelden, afronden, controle,
    subagent vormen, observer-melding. Bedienaar — de governor-kern beslist.

    Register: <doel>/governor.json (of expliciet register_pad)."""
    from kern import growkit_agents as ag

    doel = _doel_uit(invoer)
    pad = Path(str(invoer.get("register_pad", "")).strip() or doel / "governor.json")
    actie = str(invoer.get("actie", "status")).strip()

    if pad.exists():
        try:
            register = json.loads(pad.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise AdapterFout(f"governor-register {pad} is geen geldige JSON: {e}")
    else:
        register = ag.nieuw_register()

    def bewaar(nieuw: dict) -> None:
        pad.parent.mkdir(parents=True, exist_ok=True)
        pad.write_text(json.dumps(nieuw, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")

    def _agents_weergave(reg: dict) -> list[dict]:
        return [{"agent": naam, **{k: v for k, v in info.items()}}
                for naam, info in reg["agents"].items()]

    if actie == "status":
        return {"ok": True, "data": {
            "limieten": {"taken_per_agent": ag.MAX_TAKEN_PER_AGENT,
                         "max_agents": ag.MAX_AGENTS,
                         "max_taken_totaal": ag.MAX_TAKEN_TOTAAL},
            "agents": _agents_weergave(register),
            "taken": register["taken"],
            "observer_meldingen": register.get("observer_meldingen", []),
            "register_pad": str(pad)}}

    if actie == "aanmelden":
        agent = str(invoer.get("agent", "")).strip()
        taak_id = str(invoer.get("taak_id", "")).strip()
        if not agent or not taak_id:
            raise AdapterFout("aanmelden vereist agent en taak_id")
        nieuw, ok, reden = ag.meld_taak_aan(register, agent, taak_id)
        if ok:
            bewaar(nieuw)
        return {"ok": True, "data": {"resultaat": {"ok": ok, "reden": reden}}}

    if actie == "afronden":
        agent = str(invoer.get("agent", "")).strip()
        taak_id = str(invoer.get("taak_id", "")).strip()
        if not agent or not taak_id:
            raise AdapterFout("afronden vereist agent en taak_id")
        nieuw, ok, reden = ag.taak_afgerond(register, agent, taak_id,
                                            bewijs=str(invoer.get("bewijs", "")))
        if ok:
            bewaar(nieuw)
        return {"ok": True, "data": {"resultaat": {"ok": ok, "reden": reden}}}

    if actie == "controle":
        taak_id = str(invoer.get("taak_id", "")).strip()
        if not taak_id or not isinstance(invoer.get("goed"), bool):
            raise AdapterFout("controle vereist taak_id en goed (true/false)")
        nieuw, ok, reden = ag.keur_taak(register, taak_id, goed=invoer["goed"],
                                        reden=str(invoer.get("reden", "") or "") or None)
        if ok:
            bewaar(nieuw)
        return {"ok": True, "data": {"resultaat": {"ok": ok, "reden": reden}}}

    if actie == "subagent":
        ouder = str(invoer.get("agent", "")).strip()
        if not ouder:
            raise AdapterFout("subagent vereist agent (de ouder)")
        nieuw, ok, reden = ag.vorm_subagent(register, ouder)
        if ok:
            bewaar(nieuw)
        return {"ok": True, "data": {"resultaat": {"ok": ok, "reden": reden}}}

    if actie == "melding":
        tekst = str(invoer.get("tekst", "")).strip()
        if not tekst:
            raise AdapterFout("melding vereist tekst")
        nieuw, ok, _ = ag.melding_van_observer(register, tekst)
        if ok:
            bewaar(nieuw)
        return {"ok": True, "data": {"resultaat": {"ok": ok,
                                                   "reden": "Bevinding genoteerd voor de gebruiker."}}}

    raise AdapterFout("onbekende governor-actie — kies: status, aanmelden, "
                      "afronden, controle, subagent, melding")


def cmd_models(invoer: dict) -> dict:
    """Actuele modellen voor de dropdown (OpenRouter /models, geen sleutel
    nodig). Live met 15-minuten cache; bij netwerkfalen valt hij terug op
    een verlopen cache en anders een nette melding — de instellingen-open
    mag nooit crashen."""
    from kern import growkit_openrouter as gom
    forceer = bool(invoer.get("vernieuw"))
    if not forceer:
        cache = gom.lees_cache()
        if cache:
            return {"ok": True, "data": {"modellen": cache, "bron": "cache"}}
    try:
        resultaat = gom.haal_modellen_op()
        return {"ok": True, "data": resultaat}
    except Exception as e:
        # fail-open: verlopen cache is beter dan niets
        oude = gom.lees_cache(max_leeftijd_minuten=10_000)
        if oude:
            return {"ok": True, "data": {"modellen": oude, "bron": "cache",
                                         "melding": f"live ophalen faalde ({e}) — verlopen lijst getoond"}}
        return {"ok": True, "data": {"modellen": [], "bron": "onbereikbaar",
                                     "melding": f"modellen niet bereikbaar: {e} — "
                                                "typ de model-id handmatig of probeer Vernieuw later"}}


def cmd_vangnet(invoer: dict) -> dict:
    """Vangnet-status voor de app: totaal, tellingen per bron en de
    recentste vangsten. Alleen lezen — het vangnet vangt vanzelf."""
    doel = _doel_uit(invoer)
    db = doel / "vangnet" / "vangnet.db"
    if not db.exists():
        return {"ok": True, "data": {"bestaat": False, "totaal": 0,
                                     "per_bron": [], "recente": []}}
    con = sqlite3.connect(db, timeout=5)
    try:
        totaal = con.execute("SELECT COUNT(*) FROM vangsten").fetchone()[0]
        per_bron = [{"bron": b, "aantal": n} for b, n in con.execute(
            "SELECT bron, COUNT(*) FROM vangsten GROUP BY bron ORDER BY COUNT(*) DESC")]
        recente = [{"ts": ts, "bron": bron, "taak": taak, "oordeel": oordeel}
                   for ts, bron, taak, oordeel in con.execute(
                       "SELECT ts, bron, taak, oordeel FROM vangsten "
                       "ORDER BY id DESC LIMIT 20")]
    finally:
        con.close()
    return {"ok": True, "data": {"bestaat": True, "totaal": totaal,
                                 "per_bron": per_bron, "recente": recente}}


def cmd_audit(invoer: dict) -> dict:
    """Goedkeurings-audit: wat hebben code-agenten gedaan, in simpele taal.
    Begrensd (max) zodat de app-scan snel opent; kritieke acties apart."""
    from kern import growkit_goedkeuring as gk
    maximum = max(1, min(int(invoer.get("max", 5000)), 20000))
    acties = gk.verzamel(None)[:maximum]
    verrijkt = gk.verrijk(acties)
    kritiek = [a for a in verrijkt if a["kritisch"]][:maximum]
    compact = [{"bron": a["bron"], "tijdstip": (a.get("tijdstip") or "")[:16],
                "soort": a["soort"], "risico": a["risico"],
                "actie": a["actie"][:160], "uitleg": a["uitleg"]}
               for a in kritiek]
    return {"ok": True, "data": {"samenvatting": gk.samenvatting(acties),
                                 "totaal": len(acties),
                                 "kritiek_aantal": len(kritiek),
                                 "kritiek": compact}}


def cmd_familie(invoer: dict) -> dict:
    """Familie-register (slice A): de vaste cast van het harnas.

    Alleen-lezen — de familie verandert via de kernmodule (beleid),
    nooit via een adapter-aanroep."""
    from kern import growkit_familie as fam

    actie = str(invoer.get("actie", "status")).strip()
    if actie != "status":
        raise AdapterFout("onbekende familie-actie — kies: status")
    return {"ok": True, "data": fam.familie_register()}


def cmd_agentstatus(invoer: dict) -> dict:
    """Agentstatus (slice B): leeft de familie? Alleen-lezen SSH-diagnostiek
    naar de VPS — status is geen macht."""
    from kern import growkit_agentstatus as gs

    return gs.verzamel_status()


def cmd_agenttaak(invoer: dict) -> dict:
    """Agenttaak (slice C): taak aanmelden bij de gouverneur en — bij
    groen — in de wachtrij van de agent op de VPS zetten. Eén poort:
    alleen /root/.hermes/agenttaken/<agent>/wachtrij/, alleen JSON via stdin."""
    from kern import growkit_agenttaak as at
    from kern import growkit_agents as ag

    agent = str(invoer.get("agent", "")).strip().lower()
    taak_id = str(invoer.get("taak_id", "")).strip()
    titel = str(invoer.get("titel", "")).strip()
    register_pad = Path(str(invoer.get("register_pad", "")).strip()
                        or Path.home() / "growkit-governor" / "governor.json")

    # 1) gouverneur eerst: het plafond beslist, niet de UI
    register = ag.nieuw_register()
    if register_pad.exists():
        try:
            register = json.loads(register_pad.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise AdapterFout(f"governor-register {register_pad} is geen geldige JSON: {e}")
    nieuw, ok, reden = ag.meld_taak_aan(register, agent, taak_id)
    if not ok:
        return {"ok": False, "fout": f"Gouverneur weigert: {reden}"}
    register_pad.parent.mkdir(parents=True, exist_ok=True)
    register_pad.write_text(json.dumps(nieuw, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")

    # 2) transport naar de wachtrij (met contract als dat er is)
    contract = invoer.get("contract") if isinstance(invoer.get("contract"), dict) else None
    r = at.verstuur(agent, taak_id, titel, contract=contract)
    if not r["ok"]:
        # terugrollen in het register — een aangemelde taak die niet aankomt
        # mag niet blijven hangen als 'open'
        register["taken"].pop(taak_id, None)
        a = register["agents"].get(agent)
        if a and taak_id in a.get("open", []):
            a["open"].remove(taak_id)
        register_pad.write_text(json.dumps(register, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8")
        return r
    return {"ok": True, "data": {"resultaat": {"ok": True,
            "reden": f"Taak {taak_id} staat in de wachtrij van {agent}."}}}


def cmd_agentcontrole(invoer: dict) -> dict:
    """Agentcontrole (slice D): afgeronde taken ophalen (actie 'ophalen')
    of een mens-uitspraak verwerken (actie 'besluit' met agent, taak_id, goed)."""
    from kern import growkit_agentcontrole as ac

    actie = str(invoer.get("actie", "ophalen")).strip()
    if actie == "ophalen":
        return ac.ophalen()
    if actie == "besluit":
        agent = str(invoer.get("agent", ""))
        taak_id = str(invoer.get("taak_id", ""))
        if not isinstance(invoer.get("goed"), bool):
            raise AdapterFout("besluit vereist goed (true/false)")
        r = ac.besluit(agent, taak_id, goed=invoer["goed"])
        if not r["ok"]:
            return r
        # gouverneur op de hoogte: taak echt af (goedgekeurd) of weg (afgekeurd)
        from kern import growkit_agents as ag
        register_pad = Path(str(invoer.get("register_pad", "")).strip()
                            or Path.home() / "growkit-governor" / "governor.json")
        if register_pad.exists():
            try:
                register = json.loads(register_pad.read_text(encoding="utf-8"))
                nieuw, ok, _ = ag.keur_taak(register, taak_id, goed=invoer["goed"])
                if ok:
                    register_pad.write_text(
                        json.dumps(nieuw, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
            except json.JSONDecodeError:
                pass  # registerprobleem blokkeert de archivering niet
        return r
    raise AdapterFout("onbekende agentcontrole-actie — kies: ophalen, besluit")


def cmd_observaties(invoer: dict) -> dict:
    """Observaties (slice E): voorstellen uit de brein-inbox, alleen-lezen."""
    from kern import growkit_observaties as ob

    return ob.lees()


def cmd_profiel(invoer: dict) -> dict:
    """Profiel (slice H): het geboortemoment van het geheugen.
    Acties: lees | concept | bekrachtig | vergeten. Opslag is append-only
    en gebeurt uitsluitend ná ratificatie (regel 6)."""
    from kern import growkit_profiel as pf

    actie = str(invoer.get("actie", "lees")).strip()
    if actie == "lees":
        return pf.lees()
    if actie == "context":
        return {"ok": True, "data": {"context_regel": pf.context_regel()}}
    if actie == "concept":
        r = pf.concept(str(invoer.get("naam", "")),
                       rol=str(invoer.get("rol", "")),
                       doel=str(invoer.get("doel", "")),
                       taal=str(invoer.get("taal", "")),
                       moment=str(invoer.get("moment", "")),
                       agenten=str(invoer.get("agenten", "")))
        if r["ok"]:
            return {"ok": True, "data": {"concept": r["data"]["concept"]}}
        return r
    if actie == "bekrachtig":
        doc = invoer.get("concept")
        if not isinstance(doc, dict):
            raise AdapterFout("bekrachtig vereist concept (document)")
        return pf.bekrachtig(doc)
    if actie == "vergeten":
        veld = str(invoer.get("veld", "")).strip()
        if not veld:
            raise AdapterFout("vergeten vereist veld")
        return pf.vergeten(veld)
    raise AdapterFout("onbekende profiel-actie — kies: lees, concept, "
                      "bekrachtig, vergeten, context")


def cmd_harnas(invoer: dict) -> dict:
    """Harnas (Fase 1, PTS): tests zijn wet. Acties:
    - check: verifieer kadertests tegen het manifest (alleen-lezen)
    - registreer: één test bewust registreren/her-registreren — mens-handeling
    Corrupt manifest = nette fout, nooit auto-herstel."""
    from kern import growkit_pts as pts

    actie = str(invoer.get("actie", "check")).strip()
    basis = Path(str(invoer.get("basis", "")).strip()
                 or Path.home() / "growkit-governor")
    manifest = Path(str(invoer.get("manifest_pad", "")).strip() or basis / "manifest.json")
    if actie == "check":
        r = pts.check_tests(basis, manifest)
        return {"ok": True, "data": r}
    if actie == "registreer":
        test = str(invoer.get("test", "")).strip()
        if not test:
            raise AdapterFout("registreer vereist test (pad t.o.v. basis)")
        try:
            pts.registreer_test(manifest, basis / test, basis)
        except FileNotFoundError:
            raise AdapterFout(f"testbestand niet gevonden: {test}")
        return {"ok": True, "data": {"geregistreerd": test}}
    raise AdapterFout("onbekende harnas-actie — kies: check, registreer")


def cmd_contract(invoer: dict) -> dict:
    """Taak-contract (Fase 3): de zes Automatiek-bouwblokken als compleet
    contract. Acties: maak | markdown. Secrets worden geweigerd —
    authenticatie hoort op de doelmachine."""
    from kern import growkit_contract as gc

    actie = str(invoer.get("actie", "maak")).strip()
    if actie == "maak":
        return gc.maak(doel=str(invoer.get("doel", "")),
                       bronnen=str(invoer.get("bronnen", "")),
                       stappen=str(invoer.get("stappen", "")),
                       verificatie=str(invoer.get("verificatie", "")),
                       planning=str(invoer.get("planning", "")),
                       privacy=str(invoer.get("privacy", "")))
    if actie == "markdown":
        doc = invoer.get("contract")
        if not isinstance(doc, dict):
            raise AdapterFout("markdown vereist contract (document)")
        return {"ok": True, "data": {"markdown": gc.markdown(doc)}}
    raise AdapterFout("onbekende contract-actie — kies: maak, markdown")


def cmd_graaf(invoer: dict) -> dict:
    """Knowledge-graaf (fase A+): het hele brein als kaart.
    Acties: graaf | document (één bestand alleen-lezen)."""
    from kern import growkit_graaf as gg

    actie = str(invoer.get("actie", "graaf")).strip()
    if actie == "graaf":
        return gg.haal_graaf()
    if actie == "document":
        pad = str(invoer.get("pad", "")).strip()
        if not pad:
            raise AdapterFout("document vereist pad")
        return gg.lees_document(pad)
    raise AdapterFout("onbekende graaf-actie — kies: graaf, document")


COMMANDOS = {
    "status": cmd_status,
    "profielen": cmd_profielen,
    "plant": cmd_plant,
    "ratificeer": cmd_ratificeer,
    "hervat": cmd_hervat,
    "taak": cmd_taak,
    "slijp": cmd_slijp,
    "governor": cmd_governor,
    "familie": cmd_familie,
    "agentstatus": cmd_agentstatus,
    "agenttaak": cmd_agenttaak,
    "agentcontrole": cmd_agentcontrole,
    "observaties": cmd_observaties,
    "profiel": cmd_profiel,
    "harnas": cmd_harnas,
    "contract": cmd_contract,
    "graaf": cmd_graaf,
    "models": cmd_models,
    "vangnet": cmd_vangnet,
    "audit": cmd_audit,
    "bomen": cmd_bomen,
    "levensignaal": cmd_levensignaal,
    "acties": cmd_acties,
    "inbox": cmd_inbox,
    "curate": cmd_curate,
    "koppel": cmd_koppel,
    "driftguard": cmd_driftguard,
    "stuur": cmd_stuur,
    "nachtplan": cmd_nachtplan,
    "nachtronde": cmd_nachtronde,
    "nachtstatus": cmd_nachtstatus,
    "saldo": cmd_saldo,
    "verbruik": cmd_verbruik,
}

def main(argv: list[str]) -> int:
    try:
        if not argv:
            raise AdapterFout("geen commando — kies uit: " + ", ".join(sorted(COMMANDOS)))
        commando = argv[0]
        if commando not in COMMANDOS:
            raise AdapterFout(f"onbekend commando '{commando}' — kies uit: "
                              + ", ".join(sorted(COMMANDOS)))
        uit = COMMANDOS[commando](_lees_invoer())
        print(json.dumps(uit, ensure_ascii=False))
        return 0
    except AdapterFaal as e:
        print(json.dumps({"ok": False, "fout": str(e), "stappen": e.stappen},
                         ensure_ascii=False))
        return 2
    except AdapterFout as e:
        print(json.dumps({"ok": False, "fout": str(e)}, ensure_ascii=False))
        print(f"adapter: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except AdapterFout as e:
        print(json.dumps({"ok": False, "fout": str(e)}, ensure_ascii=False))
        print(f"adapter: {e}", file=sys.stderr)
        sys.exit(1)
