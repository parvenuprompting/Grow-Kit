#!/usr/bin/env bash
# Test 4 — harnas zonder agent + crash-herstart (fase-4-plan taak 8).
# Protocol vóór de run vastgesteld in docs/superpowers/plans/2026-09-03-growkit-fase-4.md.
# Alleen bash + python3: geen enkele agent is betrokken (criterium 1, §8).
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

# cli-test-reviewer (localhost-vrij, zoals Test 3): stap-008 → review_ok_wacht_ratificatie
echo '{"rollen": {"reviewer": {"type": "cli", "commando": "echo geslaagd"}}}' > "$REPO/reviewconfig.json"

FAIL() { echo "$1"; exit 1; }

CHECK() { # $1 = logboekpad, daarna python-expressies als asserties
  "$PY" - "$@" <<'PYEOF'
import json, sys
entries = json.loads(open(sys.argv[1], encoding="utf-8").read())
for expr in sys.argv[2:]:
    assert eval(expr), f"CHECK-FAAL: {expr}"
PYEOF
}

# ——— Criterium 1: plant met uitsluitend python3 + gepijpte antwoorden ———
DOEL="$TMP/boom-crash"
printf '1\n1\n%s\nja\n' "$DOEL" | "$PY" "$REPO/loop.py" > "$TMP/crash-uit.log" 2>&1 &
PID=$!
echo "OK 1: loop.py gestart met alleen python3 + gepijpte antwoorden (geen agent)"

# ——— Criterium 2: kill -9 zodra stap-005 in het logboek staat ———
LOG="$DOEL/logboek.json"
for _ in $(seq 1 5000); do
  if [ -f "$LOG" ] && grep -q '"stap-005"' "$LOG" 2>/dev/null; then break; fi
  if ! kill -0 "$PID" 2>/dev/null; then break; fi
done
kill -9 "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true
[ -f "$LOG" ] || FAIL "FAIL 2: geen logboek — plant kwam niet op gang"
grep -q '"stap-005"' "$LOG" || FAIL "FAIL 2: crash-concurrentie verloren — stap-005 niet bereikt; herhaal de test"
if grep -q '"stap-006"' "$LOG"; then FAIL "FAIL 2: crash te laat — stap-006 was al gelogd"; fi
echo "OK 2: plant gedood (kill -9) vóór stap-006; logboek bewaart de geslaagde stappen"

# ——— Criterium 3: herstart — geen herdraai van geslaagde stappen ———
HERSTART="$TMP/herstart-uit.log"
RC=0
printf '2\n%s\ntweede-brein\nja\n' "$DOEL" | "$PY" "$REPO/loop.py" > "$HERSTART" 2>&1 || RC=$?
[ "$RC" -eq 0 ] || { echo "FAIL 3: herstart-exit $RC"; tail -5 "$HERSTART"; exit 1; }
CHECK "$LOG" \
  "len([e for e in entries if e['stap']=='stap-001']) == 1" \
  "len([e for e in entries if e['stap']=='stap-005']) == 1" \
  "len([e for e in entries if e['stap']=='stap-005' and e['status']=='geslaagd']) == 1" \
  "len([e for e in entries if e['stap']=='stap-006' and e['status']=='geslaagd']) == 1" \
  "len([e for e in entries if e['stap']=='stap-007' and e['status']=='geslaagd']) == 1" \
  "[e for e in entries if e['stap']=='stap-008'][0]['status'] == 'review_ok_wacht_ratificatie'"
grep -q "nooit herdraaien" "$HERSTART" || FAIL "FAIL 3: niet-idempotent-noot ontbreekt in de herstart-uitvoer"
grep -q "Herstartpunt" "$HERSTART" || FAIL "FAIL 3: herstartpunt niet getoond"
echo "OK 3: herstart — stap-001..005 exact één geslaagd-entry (niet-idempotent stap-005 nooit herdraaid); 006-008 draaiden"

# ——— Criterium 4a: bulk-ratificatie 'ja' — append-only, geen her-review ———
RC=0
printf '4\n%s\nja\n' "$DOEL" | "$PY" "$REPO/loop.py" > "$TMP/rat-uit.log" 2>&1 || RC=$?
[ "$RC" -eq 0 ] || { echo "FAIL 4a: ratificatie-exit $RC"; tail -5 "$TMP/rat-uit.log"; exit 1; }
CHECK "$LOG" \
  "len([e for e in entries if e.get('type')=='ratificatie' and e['stap']=='stap-008' and e['status']=='geratificeerd']) == 1" \
  "len([e for e in entries if e['stap']=='stap-008']) == 2"
echo "OK 4a: bulk-ratificatie — stap-008 geratificeerd als vervolg-entry; origineel review_ok-entry intact"

# ——— Criterium 4b: afkeur — herziening_nodig, geen rollback, herstart = heraanbieden ———
DOEL2="$TMP/boom-afkeur"
printf '1\n1\n%s\nja\n\n' "$DOEL2" | "$PY" "$REPO/loop.py" > "$TMP/plant2-uit.log" 2>&1
LOG2="$DOEL2/logboek.json"
CHECK "$LOG2" "[e for e in entries if e['stap']=='stap-008'][0]['status'] == 'review_ok_wacht_ratificatie'"
RC=0
printf '4\n%s\n1\n' "$DOEL2" | "$PY" "$REPO/loop.py" > "$TMP/afkeur-uit.log" 2>&1 || RC=$?
[ "$RC" -eq 0 ] || { echo "FAIL 4b: afkeur-exit $RC"; tail -5 "$TMP/afkeur-uit.log"; exit 1; }
CHECK "$LOG2" \
  "[e for e in entries if e.get('type')=='ratificatie'][0]['status'] == 'herziening_nodig'" \
  "len([e for e in entries if e['stap']=='stap-001' and e['status']=='geslaagd']) == 1"
test -f "$DOEL2/INDEX.md" || FAIL "FAIL 4b: rollback-gevoel — INDEX.md verdwenen na afkeuring"
H2="$TMP/herstart2-uit.log"
RC=0
printf '2\n%s\nnee\n' "$DOEL2" | "$PY" "$REPO/loop.py" > "$H2" 2>&1 || RC=$?
[ "$RC" -eq 1 ] || FAIL "FAIL 4b: herstart-na-afkeur zonder bevestiging moet exit 1 zijn"
grep -q "stap-008" "$H2" || FAIL "FAIL 4b: herziening_nodig-stap ontbreekt in de restdraai"
echo "OK 4b: afkeuring → herziening_nodig; bestanden onaangetast (geen rollback); herstart biedt stap-008 opnieuw aan"

# ——— Criterium 5: poort-weigering in de loop → niets uitgevoerd ———
DOEL3="$TMP/boom-geweigerd"
RC=0
printf '1\n1\n%s\nnee\n' "$DOEL3" | "$PY" "$REPO/loop.py" > "$TMP/weiger-uit.log" 2>&1 || RC=$?
[ "$RC" -eq 1 ] || FAIL "FAIL 5: geweigerde plant moet exit 1 zijn"
[ ! -e "$DOEL3" ] || FAIL "FAIL 5: zonder bevestiging mag er niets geplant worden"
RC=0
printf '1\n1\n\n' | "$PY" "$REPO/loop.py" > "$TMP/weiger2-uit.log" 2>&1 || RC=$?
[ "$RC" -eq 1 ] || FAIL "FAIL 5: leeg doel moet door de poort geweigerd worden"
grep -q "helderziende" "$TMP/weiger2-uit.log" || FAIL "FAIL 5: vaste weigeringstekst ontbreekt"
echo "OK 5: poort-weigering — geen bevestiging, geen doel, geen actie"

# ——— Criterium 6: nette paden — corrupt logboek → mens, geen traceback ———
DOEL4="$TMP/boom-corrupt"
mkdir -p "$DOEL4"
echo '{"profiel": "tweede-brein"}' > "$DOEL4/geboortebewijs.json"
printf '{half geschreven' > "$DOEL4/logboek.json"
RC=0
printf '2\n%s\n' "$DOEL4" | "$PY" "$REPO/loop.py" > "$TMP/corrupt-uit.log" 2>&1 || RC=$?
[ "$RC" -eq 1 ] || FAIL "FAIL 6: corrupt logboek moet exit 1 zijn (mens, geen crash)"
grep -q "corrupt" "$TMP/corrupt-uit.log" || FAIL "FAIL 6: corrupt-melding ontbreekt"
if grep -q "Traceback" "$TMP/corrupt-uit.log"; then FAIL "FAIL 6: traceback naar de gebruiker"; fi
echo "OK 6: corrupt logboek → mens-boodschap, nette exit, geen traceback"

echo "TEST 4 OK: harnas zonder agent + crash-herstart — 6/6 criteria geslaagd"
