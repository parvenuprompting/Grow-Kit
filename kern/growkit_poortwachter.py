#!/usr/bin/env python3
"""GrowKit Poortwachter — getypeerde beslisser vóór de LLM (1 okt 2026).

Ontwerp: de review van Claude op Genius' voorstel (1 okt 2026). Twee trappen
werden drie:

1. REGELS EERST — gratis en 100% voorspelbaar. Een @naam-mention hoort bij
   die agent; een machine-alert van een eigen script draagt zijn ernst zelf.
   Dit dekt naar verwachting het grootste deel van het interne verkeer.
2. CLASSIFIER — alleen voor vrije tekst van buiten (e-mail, leads, chat van
   mensen). Een klein getypeerd model (bijv. Laya multilingual) levert een
   klasse plus confidence.
3. LLM — bij twijfel.

Harde regels (beleid, geen configuratie):

- Machine-alerts en security-meldingen gaan NOOIT door een probabilistisch
  filter. De handhaver is deze router zelf: bron=script slaat trap 2 over.
- Ruis wordt nooit weggegooid, alleen gedegradeerd en gelogd (append-only).
  "Iets belangrijks als ruis" is de dure fout, niet "ruis als belangrijk".
- Drempel per klasse, niet één drempel: ruis vraagt meer zekerheid dan
  urgent, want urgent-als-ruis is veel erger dan ruis-als-urgent.
- Een vast percentage van de zekere gevallen gaat alsnog naar de LLM
  (audit). Anders ziet niemand de zelfverzekerde fouten van de filter.
- Zonder classifier: nooit stil gokken. Alles naar de LLM.

Deze module beslist alleen WAAR iets heen gaat, nooit WAT er gebeurt. Hij
vervangt geen agent, geen review en geen poort: hij is een verkeersregelaar.
"""
import json
import re
from datetime import datetime, timezone

# --- trappen ---
LAAG_REGEL = 1
LAAG_CLASSIFIER = 2
LAAG_LLM = 3

KLASSEN = ("urgent", "normaal", "ruis")

# --- drempels: confidence die nodig is om een klasse te vertrouwen ---
# urgent laag (snel door), ruis hoog (nooit achteloos weggooien)
STANDAARD_DREMPELS = {"urgent": 0.60, "normaal": 0.75, "ruis": 0.90}

# --- audit-steekproef ---
AUDIT_ELKE = 20          # 1 op 20 zekere gevallen (5%) alsnog naar de LLM

# bekende familieleden — gelijk aan het familie-register
_AGENTEN = ("kairos", "riri", "vigil", "libra", "memoria", "codex", "genius")

_MENTION = re.compile(r"@([a-z0-9_]+)", re.IGNORECASE)


def _nu() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _besluit(laag: int, route: str, klasse: str, confidence,
             reden: str, *, audit: bool = False,
             gedegradeerd: bool = False) -> dict:
    return {
        "laag": laag,
        "route": route,
        "klasse": klasse,
        "confidence": confidence,
        "reden": reden,
        "audit": audit,
        "gedegradeerd": gedegradeerd,
        "tijdstip": _nu(),
    }


def _log_weg(logboek, besluit: dict, bericht: dict) -> None:
    """Append-only spoor. Nooit overschrijven, nooit opruimen."""
    if logboek is None:
        return
    regel = dict(besluit)
    regel["tekst"] = (bericht.get("tekst") or "")[:280]
    regel["bron"] = bericht.get("bron", "")
    with open(logboek, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(regel, ensure_ascii=False) + "\n")


def poort(bericht: dict, *, bron: str = "mens", classificeerder=None,
          drempels: dict | None = None, audit_teller: int | None = None,
          audit_elke: int = AUDIT_ELKE, logboek=None) -> dict:
    """Bepaal de route van één bericht. Geeft altijd een besluit terug.

    bericht      dict met minimaal "tekst"; mag "ernst" dragen (script-alerts)
    bron         "mens" (vrije tekst) of "script" (machine-alert, eigen bron)
    classificeerder  callable(tekst) -> (klasse, confidence). None = geen model.
    audit_teller  doorlopende teller; waarde deelbaar door audit_elke = audit
    logboek      pad naar een JSONL-bestand (append-only spoor)
    """
    tekst = (bericht.get("tekst") or "").strip()
    drempels = {**STANDAARD_DREMPELS, **(drempels or {})}

    # --- trap 1: regels ---
    if bron == "script":
        ernst = str(bericht.get("ernst", "urgent")).lower()
        klasse = ernst if ernst in KLASSEN else "urgent"
        b = _besluit(LAAG_REGEL, "direct", klasse, None,
                     "machine-alert: eigen bron zet de ernst zelf; nooit door "
                     "een probabilistisch filter", gedegradeerd=False)
        _log_weg(logboek, b, bericht)
        return b

    for naam in _MENTION.findall(tekst):
        if naam.lower() in _AGENTEN:
            b = _besluit(LAAG_REGEL, naam.lower(), "normaal", None,
                         f"@-mention van {naam.lower()}: regel, geen model")
            _log_weg(logboek, b, bericht)
            return b

    # --- trap 2: classifier ---
    if classificeerder is None:
        b = _besluit(LAAG_LLM, "llm", "onbekend", None,
                     "geen classifier beschikbaar — nooit stil gokken")
        _log_weg(logboek, b, bericht)
        return b

    klasse, confidence = classificeerder(tekst)
    klasse = str(klasse).lower()
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    if klasse not in KLASSEN:
        b = _besluit(LAAG_LLM, "llm", "onbekend", confidence,
                     f"classifier gaf onbekende klasse '{klasse}'")
        _log_weg(logboek, b, bericht)
        return b

    # twijfel of audit -> LLM
    if confidence < drempels[klasse]:
        b = _besluit(LAAG_LLM, "llm", klasse, confidence,
                     f"confidence {confidence:.2f} onder drempel "
                     f"{drempels[klasse]:.2f} voor '{klasse}'")
        _log_weg(logboek, b, bericht)
        return b

    if audit_teller is not None and audit_teller % audit_elke == 0:
        b = _besluit(LAAG_LLM, "llm", klasse, confidence,
                     "audit-steekproef: vast aandeel zekere gevallen gaat "
                     "alsnog naar de LLM", audit=True)
        _log_weg(logboek, b, bericht)
        return b

    if klasse == "ruis":
        b = _besluit(LAAG_CLASSIFIER, "gedegradeerd", klasse, confidence,
                     "ruis met voldoende zekerheid: gedegradeerd maar bewaard "
                     "(append-only), nooit weggegooid", gedegradeerd=True)
        _log_weg(logboek, b, bericht)
        return b

    b = _besluit(LAAG_CLASSIFIER, "afgehandeld", klasse, confidence,
                 f"klasse '{klasse}' met confidence {confidence:.2f}: "
                 f"geen LLM nodig, bespaart een call")
    _log_weg(logboek, b, bericht)
    return b
