#!/usr/bin/env bash
# Slice 5 — E2E: breinkoppeling end-to-end via de adapter.
# Protocol: twee bomen koppelen aan één brein → drift-guard-rapport →
# VOORSTEL-doorstroom (alleen gemarkeerde bestanden reizen) → bomen-lijst
# toont beide bomen onder hetzelfde brein.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="python3"
TMP="$(mktemp -d)"
export GROWKIT_OERWOUD_STAAT="$TMP/growkit-home/oerwoud.json"

FAIL() { echo "$1"; exit 1; }

BREIN="$TMP/brein"
mkdir -p "$BREIN/inbox"
"$PY" - "$BREIN" <<'PYEOF'
import json, sys
from pathlib import Path
brein = Path(sys.argv[1])
(brein / "geboortebewijs.json").write_text(json.dumps({
    "boom_id": "brein-s5", "profiel": "tweede-brein", "machine": "e2e",
    "locatie": str(brein), "geplant_op": "2026-09-04T09:00:00+00:00"}), encoding="utf-8")
PYEOF

Boom() {
  mkdir -p "$TMP/$1"
  "$PY" - "$TMP/$1" <<'PYEOF'
import json, sys
from pathlib import Path
doel = Path(sys.argv[1])
(doel / "geboortebewijs.json").write_text(json.dumps({
    "boom_id": doel.name, "profiel": "dev-werkplaats", "machine": "e2e",
    "locatie": str(doel), "geplant_op": "2026-09-04T09:00:00+00:00"}), encoding="utf-8")
(doel / "logboek.json").write_text("[]", encoding="utf-8")
PYEOF
}

# ——— 1: boom A koppelen ———
Boom boom-a
UIT="$(printf '{"doel":"%s/boom-a","brein_pad":"%s"}' "$TMP" "$BREIN" | "$PY" "$REPO/adapter.py" koppel)" \
  || FAIL "FAIL 1: koppeling boom-a faalde"
echo "$UIT" | grep -q '"status": "geboorte"' || FAIL "FAIL 1: status geen geboorte"
echo "OK 1: boom-a geregistreerd in het brein-register"

# ——— 2: boom B koppelen (tweede boom, zelfde brein) ———
Boom boom-b
printf '{"doel":"%s/boom-b","brein_pad":"%s"}' "$TMP" "$BREIN" | "$PY" "$REPO/adapter.py" koppel >/dev/null \
  || FAIL "FAIL 2: koppeling boom-b faalde"
echo "OK 2: boom-b geregistreerd — twee bomen, één brein"

# ——— 3: drift-guard-rapport ———
UIT="$(printf '{"brein_pad":"%s"}' "$BREIN" | "$PY" "$REPO/adapter.py" driftguard)"
echo "$UIT" | grep -q '"bomen": 2' || FAIL "FAIL 3: rapport telt niet 2 bomen"
echo "$UIT" | grep -q 'VOORSTEL' || FAIL "FAIL 3: reist_mee noemt VOORSTEL niet"
echo "$UIT" | grep -qi 'sleutels' || FAIL "FAIL 3: blijft_lokaal noemt sleutels niet"
echo "OK 3: drift-guard-rapport toont regels + 2 actieve bomen"

# ——— 4: VOORSTEL-doorstroom met drift-guard ———
mkdir -p "$TMP/boom-a/inbox"
printf 'inzicht uit boom-a' > "$TMP/boom-a/inbox/VOORSTEL-inzicht-1.md"
printf 'blijft thuis' > "$TMP/boom-a/geheim.txt"
UIT="$(printf '{"doel":"%s/boom-a","brein_pad":"%s"}' "$TMP" "$BREIN" | "$PY" "$REPO/adapter.py" stuur)" \
  || FAIL "FAIL 4: doorstroom faalde"
echo "$UIT" | grep -q '"verzonden": 1' || FAIL "FAIL 4: niet precies 1 verstuurd"
test -f "$BREIN/inbox/VOORSTEL-boom-a-inzicht-1.md" || FAIL "FAIL 4: VOORSTEL niet aangekomen"
grep -q 'boom-a' "$BREIN/inbox/VOORSTEL-boom-a-inzicht-1.md" || FAIL "FAIL 4: inhoud beschadigd"
test ! -e "$BREIN/geheim.txt" || FAIL "FAIL 4: geheim.txt reisde mee — drift-guard geschonden"
echo "OK 4: VOORSTEL reisde met boom-id-prefix; geheim.txt bleef thuis"

# ——— 5: dubbele koppeling geweigerd ———
N_VOOR="$("$PY" -c "import json; print(len(json.load(open('$BREIN/register/bomen.json'))))")"
UIT="$(printf '{"doel":"%s/boom-a","brein_pad":"%s"}' "$TMP" "$BREIN" | "$PY" "$REPO/adapter.py" koppel 2>/dev/null)" \
  && FAIL "FAIL 5: dubbele koppeling gaf exit 0"
N_NA="$("$PY" -c "import json; print(len(json.load(open('$BREIN/register/bomen.json'))))")"
[ "$N_VOOR" = "$N_NA" ] || FAIL "FAIL 5: register is gegroeid bij geweigerde koppeling"
echo "OK 5: dubbele geboorte geweigerd — register append-only intact"

# ——— 6: bomen-lijst toont beide bomen onder het bekende brein ———
UIT="$(printf '{}' | "$PY" "$REPO/adapter.py" bomen)"
N="$(printf '%s' "$UIT" | "$PY" -c "import json,sys; print(len(json.loads(sys.stdin.read())['data']['bomen']))")"
[ "$N" = "2" ] || FAIL "FAIL 6: verwacht 2 bomen via bekend brein, kreeg $N"
echo "OK 6: bomen-lijst leest het gekoppelde brein (2 bomen)"

rm -rf "$TMP"
echo ""
echo "SLICE 5 E2E: ALLE 6 CRITERIA GROEN"
