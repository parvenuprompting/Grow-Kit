#!/usr/bin/env bash
# Test 5 — het oerwoud op een schone plek (fase-5-plan taak 7).
# Protocol vóór de run vastgesteld in docs/superpowers/plans/2026-09-03-growkit-fase-5.md.
# Alleen bash + python3: geen enkele agent is betrokken (criterium 6).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"

PY=""
for kandidaat in python3.14 python3.13 python3.12 python3.11 python3; do
  if command -v "$kandidaat" >/dev/null 2>&1; then
    if "$kandidaat" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
      PY="$kandidaat"; break
    fi
  fi
done
test -n "$PY" || { echo "FAIL: geen Python 3.11+ gevonden"; exit 1; }

TMP="$(mktemp -d)"
export GROWKIT_OERWOUD_STAAT="$TMP/growkit-home/oerwoud.json"
trap 'rm -rf "$TMP"; rm -f "$REPO/reviewconfig.json"' EXIT

FAIL() { echo "$1"; exit 1; }

CHECK() { # $1 = pad naar json-bestand, daarna python-asserties over `entries`
  "$PY" - "$@" <<'PYEOF'
import json, sys
from pathlib import Path
entries = json.loads(open(sys.argv[1], encoding="utf-8").read())
for expr in sys.argv[2:]:
    assert eval(expr), f"CHECK-FAAL: {expr}"
PYEOF
}

# ——— Criterium 1: boom A wordt op een schone plek het brein ———
DOEL_A="$TMP/boom-a"
printf '1\n1\n%s\nja\n\n' "$DOEL_A" | "$PY" "$REPO/loop.py" > "$TMP/plant-a.log" 2>&1
CHECK "$DOEL_A/geboortebewijs.json" \
  "'{{' not in json.dumps(entries)" \
  "all(entries.get(v) for v in ('boom_id','profiel','machine','locatie','geplant_op'))"
CHECK "$DOEL_A/register/bomen.json" \
  "len(entries) == 1" \
  "entries[0].get('is_brein') is True" \
  "entries[0]['boom_id'] == json.loads(open('$DOEL_A/geboortebewijs.json').read())['boom_id']"
CHECK "$DOEL_A/logboek.json" \
  "len([e for e in entries if e.get('type') == 'geboorte']) == 1"
"$PY" -c "import uuid, json; uuid.UUID(json.load(open('$DOEL_A/geboortebewijs.json'))['boom_id'])"
echo "OK 1: boom A geplant, geboortebewijs volwaardig, geregistreerd als brein"

# ——— Criterium 2: boom B registreert zonder vraag ———
DOEL_B="$TMP/boom-b"
printf '1\n1\n%s\nja\n' "$DOEL_B" | "$PY" "$REPO/loop.py" > "$TMP/plant-b.log" 2>&1
CHECK "$DOEL_A/register/bomen.json" \
  "len(entries) == 2" \
  "len({e['boom_id'] for e in entries}) == 2" \
  "sum(1 for e in entries if e.get('is_brein')) == 1" \
  "all(Path(e['locatie']).exists() for e in entries)"
echo "OK 2: boom B geregistreerd zonder brein-vraag; geen dubbele boom-ids; locaties bestaan"

# ——— Criterium 3: VOORSTEL-doorstroom met drift-guard ———
mkdir -p "$DOEL_B/inbox"
printf 'het brein voedt de opties — het vliegwiel draait' > "$DOEL_B/inbox/VOORSTEL-test-inzicht.md"
BOOM_ID_B="$("$PY" -c "import json; print(json.load(open('$DOEL_B/geboortebewijs.json'))['boom_id'])")"
RC=0
printf '5\n%s\nja\n' "$DOEL_B" | "$PY" "$REPO/loop.py" > "$TMP/status-b.log" 2>&1 || RC=$?
[ "$RC" -eq 0 ] || { echo "FAIL 3: status-exit $RC"; tail -5 "$TMP/status-b.log"; exit 1; }
test -f "$DOEL_A/inbox/VOORSTEL-$BOOM_ID_B-test-inzicht.md" || FAIL "FAIL 3: VOORSTEL niet aangekomen in de brein-inbox"
grep -q "vliegwiel" "$DOEL_A/inbox/VOORSTEL-$BOOM_ID_B-test-inzicht.md" || FAIL "FAIL 3: inhoud beschadigd"
head -1 "$DOEL_A/inbox/REGELS.md" | grep -q "# Regels voor de inbox" || FAIL "FAIL 3: REGELS.md is overschreven — drift-guard gefaald"
grep -q "vliegwiel" "$DOEL_A/inbox/REGELS.md" && FAIL "FAIL 3: VOORSTEL-inhoud lekte in REGELS.md"
test "$(ls "$DOEL_A/inbox" | grep -c '^VOORSTEL-')" -eq 1 || FAIL "FAIL 3: onverwachte extra bestanden in de brein-inbox"
CHECK "$DOEL_B/logboek.json" \
  "len([e for e in entries if e.get('type') == 'doorstroom']) == 1"
echo "OK 3: VOORSTEL met boom-id-prefix aangekomen; REGELS.md niet meegenomen (drift-guard)"

# ——— Criterium 4: status toont identiteit, register en tellers ———
RC=0
printf '5\n%s\n' "$DOEL_A" | "$PY" "$REPO/loop.py" > "$TMP/status-a.log" 2>&1 || RC=$?
[ "$RC" -eq 0 ] || { echo "FAIL 4: status A exit $RC"; tail -5 "$TMP/status-a.log"; exit 1; }
grep -q "geboorte" "$TMP/status-a.log" || FAIL "FAIL 4: register-status ontbreekt in status A"
grep -q "0 wachtend" "$TMP/status-b.log" || FAIL "FAIL 4: teller na doorstroom klopt niet"
grep -q "1 verzonden" "$TMP/status-b.log" || FAIL "FAIL 4: verzonden-teller klopt niet"
echo "OK 4: status voor beide bomen — identiteit, register en tellers kloppen"

# ——— Criterium 5: corrupt register → mens, geen crash ———
printf '{geen json' > "$DOEL_A/register/bomen.json"
RC=0
printf '5\n%s\n' "$DOEL_A" | "$PY" "$REPO/loop.py" > "$TMP/status-corrupt.log" 2>&1 || RC=$?
[ "$RC" -eq 1 ] || FAIL "FAIL 5: corrupt register moet exit 1 zijn (mens, geen crash)"
grep -q "corrupt" "$TMP/status-corrupt.log" || FAIL "FAIL 5: corrupt-melding ontbreekt"
if grep -q "Traceback" "$TMP/status-corrupt.log"; then FAIL "FAIL 5: traceback naar de gebruiker"; fi
echo "OK 5: corrupt register → mens-boodschap, nette exit, geen traceback"

echo "TEST 5 OK: oerwoud — 6/6 criteria geslaagd (register, doorstroom, drift-guard, status, corrupt-pad)"
