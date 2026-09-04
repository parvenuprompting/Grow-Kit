#!/usr/bin/env bash
# Slice 1 — E2E: het `bomen`-commando end-to-end via de adapter.
# Protocol: brein met register op een schone plek; geboorte registreren;
# lijst ophalen met én zonder expliciet register_pad; corrupt register faalt
# netjes; geen brein → lege lijst met melding.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="python3"
TMP="$(mktemp -d)"
export GROWKIT_OERWOUD_STAAT="$TMP/growkit-home/oerwoud.json"

FAIL() { echo "$1"; exit 1; }

# ——— 1: geen brein bekend → lege lijst + melding, exit 0 ———
UIT="$(printf '{}' | "$PY" "$REPO/adapter.py" bomen)" || FAIL "FAIL 1: bomen faalde zonder brein"
echo "$UIT" | grep -q '"bomen": \[\]' || FAIL "FAIL 1: lijst niet leeg"
echo "$UIT" | grep -q 'geen brein gekoppeld' || FAIL "FAIL 1: melding mist"
echo "OK 1: geen brein → lege lijst + melding"

# ——— 2: brein + geboorte registreren, lijst toont de boom ———
BREIN="$TMP/brein"
mkdir -p "$BREIN"
"$PY" - "$BREIN" <<'PYEOF'
import json, sys
from pathlib import Path
brein = Path(sys.argv[1])
(brein / "geboortebewijs.json").write_text(json.dumps({
    "boom_id": "brein-e2e-0001", "profiel": "tweede-brein",
    "machine": "e2e", "locatie": str(brein),
    "geplant_op": "2026-09-04T08:00:00+00:00"}), encoding="utf-8")
PYEOF
"$PY" -c "from kern import growkit_oerwoud; growkit_oerwoud.sla_brein_pad(__import__('pathlib').Path('$BREIN'))" || FAIL "FAIL 2: oerwoud-staat schrijven faalde"

BOOM="$TMP/boom-a"
UIT="$("$PY" - "$BOOM" "$BREIN" <<'PYEOF'
import json, sys
from pathlib import Path
doel, brein = Path(sys.argv[1]), Path(sys.argv[2])
doel.mkdir(parents=True)
bewijs = {"boom_id": "boom-e2e-0002", "profiel": "dev-werkplaats",
          "machine": "e2e", "locatie": str(doel),
          "geplant_op": "2026-09-04T09:00:00+00:00"}
(doel / "geboortebewijs.json").write_text(json.dumps(bewijs), encoding="utf-8")
(doel / "logboek.json").write_text(json.dumps(
    [{"tijdstip": "2026-09-04T09:00:00+00:00", "type": "geboorte", "tekst": "geplant"}]),
    encoding="utf-8")
from kern import growkit_oerwoud
growkit_oerwoud.meld_geboorte(brein / "register" / "bomen.json",
                              brein / "geboortebewijs.json", is_brein=True)
growkit_oerwoud.meld_geboorte(brein / "register" / "bomen.json",
                              doel / "geboortebewijs.json")
print(json.dumps({"ok": True}))
PYEOF
)" || FAIL "FAIL 2: registratie faalde"

UIT="$(printf '{}' | "$PY" "$REPO/adapter.py" bomen)" || FAIL "FAIL 2: bomen faalde met bekend brein"
echo "$UIT" | grep -q 'boom-e2e-0002' || FAIL "FAIL 2: geplante boom mist in de lijst"
echo "$UIT" | grep -q '"status": "geboorte"' || FAIL "FAIL 2: status mist"
N="$("$PY" -c "import json,sys; print(len(json.loads('''$UIT''')['data']['bomen']))")"
[ "$N" = "2" ] || FAIL "FAIL 2: verwacht 2 bomen (brein + boom), kreeg $N"
echo "OK 2: register via bekend brein → 2 bomen met status"

# ——— 3: expliciet register_pad ———
UIT="$(printf '{"register_pad":"%s"}' "$BREIN/register/bomen.json" | "$PY" "$REPO/adapter.py" bomen)" \
  || FAIL "FAIL 3: bomen met expliciet register_pad faalde"
echo "$UIT" | grep -q 'brein-e2e-0001' || FAIL "FAIL 3: brein mist (is_brein-vlag)"
echo "$UIT" | grep -q '"is_brein": true' || FAIL "FAIL 3: is_brein-vlag mist"
echo "OK 3: expliciet register_pad → brein-vlag zichtbaar"

# ——— 4: corrupt register → nette fout, exit 1 ———
mkdir -p "$BREIN/kaput-register"
echo "{kapot" > "$BREIN/kaput-register/bomen.json"
UIT="$(printf '{"register_pad":"%s"}' "$BREIN/kaput-register/bomen.json" | "$PY" "$REPO/adapter.py" bomen 2>/dev/null)" \
  && FAIL "FAIL 4: corrupt register gaf exit 0"
echo "$UIT" | grep -q '"ok": false' || FAIL "FAIL 4: geen nette fout"
echo "$UIT" | grep -q 'corrupt' || FAIL "FAIL 4: fouttekst noemt corrupt niet"
echo "OK 4: corrupt register → nette fout (mens), nooit auto-repareren"

# ——— 5: onbereikbaar brein → nette fout ———
export GROWKIT_OERWOUD_STAAT="$TMP/growkit-home/weg.json"
"$PY" -c "from kern import growkit_oerwoud; growkit_oerwoud.sla_brein_pad(__import__('pathlib').Path('$TMP/verdwenen'))" \
  || FAIL "FAIL 5: staat schrijven faalde"
UIT="$(printf '{}' | "$PY" "$REPO/adapter.py" bomen 2>/dev/null)" \
  && FAIL "FAIL 5: onbereikbaar brein gaf exit 0"
echo "$UIT" | grep -q 'niet bereikbaar' || FAIL "FAIL 5: fouttekst mist 'niet bereikbaar'"
echo "OK 5: onbereikbaar brein → nette fout"

rm -rf "$TMP"
echo ""
echo "SLICE 1 E2E: ALLE 5 CRITERIA GROEN"
