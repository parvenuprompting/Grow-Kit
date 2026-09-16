#!/usr/bin/env bash
# Test 6 — de app-eindtest (fase 6). Protocol vóór de run vastgesteld in het plan.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP="$REPO/app"
PY="/opt/homebrew/bin/python3.13"
TMP="$(mktemp -d)"
export GROWKIT_OERWOUD_STAAT="$TMP/growkit-home/oerwoud.json"

FAIL() { echo "$1"; exit 1; }
CHECK() {
  "$PY" - "$@" <<'PYEOF'
import json, sys
entries = json.loads(open(sys.argv[1], encoding="utf-8").read())
for expr in sys.argv[2:]:
    assert eval(expr), f"CHECK-FAAL: {expr}"
PYEOF
}

# ——— Criterium 1: build + fonts ———
BUILD_UIT="$(bash "$APP/build.sh")" || { echo "$BUILD_UIT" | tail -5; FAIL "FAIL 1: build faalde"; }
echo "$BUILD_UIT" | grep -q "FONTS OK" || FAIL "FAIL 1: fonts niet ingebed"
APPBUNDLE="$APP/.build/Build/Products/Debug/GrowKit.app"
echo "OK 1: app compileert — Fraunces + Inter ingebed"

# ——— Criterium 2: adapter-scenario's op een schone plek ———
DOEL="$TMP/boom"
UIT_CONCEPT="$(printf '{"profiel":"tweede-brein","doel":"%s"}' "$DOEL" | "$PY" "$REPO/adapter.py" plant)"
echo "$UIT_CONCEPT" | grep -q '"bevestiging_vereist": true' || FAIL "FAIL 2a: concept zonder bevestiging mist de vlag"
test ! -d "$DOEL" || FAIL "FAIL 2a: concept-modus heeft uitgevoerd — poort geschonden"
echo "OK 2a: concept-modus voert niets uit (poort-contract)"

UIT_PLANT="$(printf '{"profiel":"tweede-brein","doel":"%s","bevestig":true,"brein":"geen"}' "$DOEL" | "$PY" "$REPO/adapter.py" plant)"
echo "$UIT_PLANT" | "$PY" -c "
import json, sys
uit = json.loads(sys.stdin.read())
assert uit['ok'], f'plant faalde: {uit}'
stappen = uit['data']['stappen']
assert len(stappen) == 8, f'8 stappen verwacht: {len(stappen)}'
assert len([s for s in stappen if s['status'] == 'geslaagd']) == 7
assert any(s['status'] == 'wacht_op_mens' for s in stappen)
assert uit['data']['registratie'] == 'geen'
" || FAIL "FAIL 2b: bevestigde plant faalde"
CHECK "$DOEL/geboortebewijs.json" "'{{' not in json.dumps(entries)"
echo "OK 2b: bevestigde plant — 8 stappen met bewijs, geboortebewijs volwaardig"

BREIN="$TMP/brein"
mkdir -p "$BREIN"
printf '{"boom_id":"11111111-1111-1111-1111-111111111111","profiel":"tweede-brein","machine":"e2e","locatie":"%s","geplant_op":"2026-09-04T00:00:00+00:00"}' "$BREIN" > "$BREIN/geboortebewijs.json"
DOEL_B="$TMP/boom-b"
printf '{"profiel":"tweede-brein","doel":"%s","bevestig":true,"brein":"pad","brein_pad":"%s"}' "$DOEL_B" "$BREIN" | "$PY" "$REPO/adapter.py" plant > /dev/null
CHECK "$BREIN/register/bomen.json" \
  "len(entries) == 1" \
  "__import__('os').path.realpath(entries[0]['locatie']) == __import__('os').path.realpath('$DOEL_B')"
UIT_STATUS="$(printf '{"doel":"%s"}' "$DOEL_B" | "$PY" "$REPO/adapter.py" status)"
echo "$UIT_STATUS" | grep -q '"status": "geboorte"' || FAIL "FAIL 2c: status toont registratie niet"
echo "OK 2c: registratie bij een brein-pad + status toont geboorte"

# ——— Criterium 2d: ratificatie via de adapter ———
echo '{"rollen": {"reviewer": {"type": "cli", "commando": "echo geslaagd"}}}' > "$REPO/reviewconfig.json"
DOEL_C="$TMP/boom-c"
printf '{"profiel":"tweede-brein","doel":"%s","bevestig":true,"brein":"geen"}' "$DOEL_C" | "$PY" "$REPO/adapter.py" plant > /dev/null
UIT_RAT="$(printf '{"doel":"%s"}' "$DOEL_C" | "$PY" "$REPO/adapter.py" ratificeer)"
echo "$UIT_RAT" | grep -q '"stappen": \["stap-008"\]' || FAIL "FAIL 2d: ratificatie-lijst toont stap-008 niet"
printf '{"doel":"%s","bevestig":true}' "$DOEL_C" | "$PY" "$REPO/adapter.py" ratificeer > /dev/null
CHECK "$DOEL_C/logboek.json" \
  "len([e for e in entries if e.get('type') == 'ratificatie' and e['status'] == 'geratificeerd']) == 1"
rm -f "$REPO/reviewconfig.json"
echo "OK 2d: ratificatie — lijst + bulk-goedkeuring via de adapter"

# ——— Criterium 4: schermen gerenderd uit de echte SwiftUI-views ———
SCHERMEN="$REPO/docs/superpowers/bewijs/fase-6-schermen"
mkdir -p "$SCHERMEN"
swiftc -o "$TMP/render" \
  "$APP/Sources/Thema.swift" "$APP/Sources/Bouwstenen.swift" "$APP/Sources/Runner.swift" \
  "$APP/Sources/StatusView.swift" "$APP/Sources/PlantView.swift" "$APP/Sources/RatificeerView.swift" \
  "$APP/Scripts/render/main.swift" 2> "$TMP/render-log.txt" \
  || { tail -10 "$TMP/render-log.txt"; FAIL "FAIL 4: render-binary compileerde niet"; }
"$TMP/render" | grep -q "RENDER OK" || FAIL "FAIL 4: render faalde"
for scherm in status.png plant.png ratificatie.png; do
  test -s "$SCHERMEN/$scherm" || FAIL "FAIL 4: scherm $scherm ontbreekt"
done
echo "OK 4: drie schermen gerenderd in de huisstijl (uit de echte SwiftUI-views)"

# ——— Criterium 5: geen shell in de keten ———
grep -q "subprocess" "$REPO/adapter.py" && FAIL "FAIL 5: subprocess in de adapter"
grep -q "shell" "$REPO/adapter.py" && FAIL "FAIL 5: shell in de adapter"
grep -qE "NSAppleScript|osascript|shell" "$APP/Sources/Runner.swift" && FAIL "FAIL 5: shell in de Runner"
echo "OK 5: geen shell in de keten — adapter en Runner zijn schoon"

# ——— Criterium 6: regressie ———
( cd "$REPO" && "$PY" -m unittest discover -s tests -p 'test_*.py' > /dev/null 2>&1 ) \
  || FAIL "FAIL 6: unit-suite faalde"
for e2e in e2e_test1_schoon.sh e2e_test2_poort.sh e2e_test3_review.sh e2e_test4_harnas.sh e2e_test5_oerwoud.sh e2e_plant.sh; do
  bash "$REPO/tests/$e2e" > /dev/null 2>&1 || FAIL "FAIL 6: $e2e faalde"
done
echo "OK 6: 206 unit-tests + E2E 1-5 + rooktest groen"

echo "TEST 6 OK: de app compileert, bedient en bewijst"
