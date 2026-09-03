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


def cmd_profielen(invoer: dict) -> dict:
    profielen = [{"naam": p["profiel"], "beschrijving": p.get("beschrijving", "")}
                 for p in laad_profielen() if p.get("status") == "bewezen-vorm"]
    staat = growkit_oerwoud.laad_oerwoud_staat()
    opties = []
    if staat["brein_pad"] and not staat["fout"]:
        opties = [{"naam": n, "bron": "uit je brein"}
                  for n in growkit_oerwoud.brein_opties(staat["brein_pad"])]
    return {"ok": True, "data": {"profielen": profielen, "brein_opties": opties}}


COMMANDOS = {
    "status": cmd_status,
    "profielen": cmd_profielen,
}


def main(argv: list[str]) -> int:
    if not argv:
        raise AdapterFout("geen commando — kies uit: " + ", ".join(sorted(COMMANDOS)))
    commando = argv[0]
    if commando not in COMMANDOS:
        raise AdapterFout(f"onbekend commando '{commando}' — kies uit: "
                          + ", ".join(sorted(COMMANDOS)))
    uit = COMMANDOS[commando](_lees_invoer())
    print(json.dumps(uit, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except AdapterFout as e:
        print(json.dumps({"ok": False, "fout": str(e)}, ensure_ascii=False))
        print(f"adapter: {e}", file=sys.stderr)
        sys.exit(1)
