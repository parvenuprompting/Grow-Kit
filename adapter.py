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
    stappen = [{"id": e["stap"], "status": e["status"], "bewijs": e["bewijs"]}
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
    growkit_oerwoud.log_run_latch(doel / "logboek.json", "gestart")
    with contextlib.redirect_stdout(sys.stderr):
        geslaagd, bevindingen = voer_taak_uit(doel, taak, reviewconfig=reviewconfig)
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
    stappen = [{"id": e["stap"], "status": e["status"], "bewijs": e["bewijs"]}
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



COMMANDOS = {
    "status": cmd_status,
    "profielen": cmd_profielen,
    "plant": cmd_plant,
    "ratificeer": cmd_ratificeer,
    "hervat": cmd_hervat,
    "taak": cmd_taak,
    "bomen": cmd_bomen,
    "levensignaal": cmd_levensignaal,
    "acties": cmd_acties,
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
