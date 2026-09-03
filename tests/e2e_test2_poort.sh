#!/usr/bin/env bash
# Test 2 — "Vrije beschrijving": de poort weigert ruis en vraagt scherp.
# Controleert alle 5 criteria uit docs/superpowers/testprotocol-fase-2.md.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PY=""
for kandidaat in python3.14 python3.13 python3.12 python3.11 python3; do
  if command -v "$kandidaat" >/dev/null 2>&1; then
    if "$kandidaat" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
      PY="$kandidaat"
      break
    fi
  fi
done
test -n "$PY" || { echo "FAIL: geen Python 3.11+ gevonden"; exit 1; }

# ——— Criterium 2.1: vage invoer geweigerd zonder enige uitvoering ———
VAGE="maak me iets om m'n notities te ordenen of zo"
UIT="$("$PY" "$REPO/seed.py" --vrij "$VAGE" 2>&1)" && CODE=0 || CODE=$?
test "$CODE" -ne 0 || { echo "FAIL 2.1: vage invoer gaf exit 0 (moet weigeren)"; exit 1; }
echo "OK 2.1a: vage invoer geweigerd (exit $CODE), geen map aangemaakt"

# ——— Criterium 2.2: weigering bevat vragen + §11.3-vragenlijst-JSON ———
"$PY" - "$UIT" <<'PYEOF'
import json, sys
uit = sys.argv[1]
assert "bui" in uit, "2.2 FAIL: vaste weigeringstekst (bui) ontbreekt"
start = uit.find("{")
assert start >= 0, "2.2 FAIL: geen vragenlijst-JSON gevonden"
data = json.loads(uit[start:uit.rfind("}") + 1])
vragen = data["vragen"]
assert len(vragen) == 3, f"2.2 FAIL: {len(vragen)} vragen, verwacht 3"
for v in vragen:
    assert "vraag" in v and "opties" in v, "2.2 FAIL: §11.3-vorm geweldaan"
    assert v["opties"][-1] == "iets anders (beschrijf)", "2.2 FAIL: laatste optie hoort 'iets anders (beschrijf)' te zijn"
print("OK 2.2: weigering + 3 vragen in §11.3-JSON-vorm (elk met 'iets anders')")
PYEOF

# ——— Criterium 2.4: append-only slijper-logging (ruw + concept + beslissing) ———
"$PY" - "$REPO" <<'PYEOF'
import json, sys
from pathlib import Path
repo = Path(sys.argv[1])
log = repo / "groei" / "slijper-logboek.json"
entries = json.loads(log.read_text(encoding="utf-8"))
assert entries, "2.4 FAIL: slijper-logboek leeg"
e = entries[-1]
assert e["type"] == "slijper", "2.4 FAIL: type != slijper"
assert e["ruw"] and e["concept"] is not None and e["beslissing"], "2.4 FAIL: ruw/concept/beslissing onvolledig"
assert e["beslissing"] == "geweigerd", f"2.4 FAIL: beslissing={e['beslissing']}, verwacht geweigerd"
print("OK 2.4: append-only logging — ruw + concept + beslissing ('geweigerd') aanwezig")
PYEOF

# ——— Criterium 2.3: complete invoer → concept dat wacht op mens, niet uitvoert ———
VOLLEDIG="einddoel: een tweede brein voor mijn notities omgeving: lokaal slaag-criterium: vijf mappen bestaan en logboek is leeg"
DOEL="$TMP/plant"
UIT2="$("$PY" "$REPO/seed.py" --vrij "$VOLLEDIG" 2>&1)"
test ! -d "$DOEL" || { echo "FAIL 2.3: er is een plant-map aangemaakt"; exit 1; }
echo "$UIT2" | grep -q "wacht_op_mens" || { echo "FAIL 2.3: concept bevat geen wacht_op_mens"; exit 1; }
echo "$UIT2" | grep -q "Klopt dit" || { echo "FAIL 2.3: mens-bevestigingsvraag ontbreekt"; exit 1; }
echo "OK 2.3: complete invoer → concept wacht op mens; niets uitgevoerd, geen map"

# ——— Criterium 2.5: vaste weigeringsteksten conform spec §11 ———
"$PY" - "$REPO" <<'PYEOF'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from kern.growkit_poort import WEIGERING_BUI, WEIGERING_TUINIER
assert "bui" in WEIGERING_BUI and "Dan plant ik" in WEIGERING_BUI, "2.5 FAIL: WEIGERING_BUI niet conform §11"
assert "tuinier" in WEIGERING_TUINIER and "helderziende" in WEIGERING_TUINIER, "2.5 FAIL: WEIGERING_TUINIER niet conform §11"
print("OK 2.5: weigeringsteksten zijn vaste constanten conform spec §11")
PYEOF

echo ""
echo "TEST 2 OK: poort weigert ruis en vraagt scherp — 5/5 criteria geslaagd"
