#!/usr/bin/env bash
# Slice 3 — E2E: acties met poortjes, end-to-end via de adapter.
# Protocol (per uitvoerende actie): zonder bevestiging niets uitgevoerd;
# met bevestiging uitvoering; zonder bewijs bestaat de actie niet; het
# actie-menu toont alleen wat er mag, met expliciete mens-momenten.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="python3"
TMP="$(mktemp -d)"
export GROWKIT_OERWOUD_STAAT="$TMP/growkit-home/oerwoud.json"

FAIL() { echo "$1"; exit 1; }

BOOM() { # $1=naam → maakt een geplante boom met logboek
  mkdir -p "$TMP/$1"
  "$PY" - "$TMP/$1" <<'PYEOF'
import json, sys
from pathlib import Path
doel = Path(sys.argv[1])
(doel / "geboortebewijs.json").write_text(json.dumps({
    "boom_id": doel.name, "profiel": "dev-werkplaats", "machine": "e2e",
    "locatie": str(doel), "geplant_op": "2026-09-04T09:00:00+00:00"}), encoding="utf-8")
(doel / "logboek.json").write_text(json.dumps([
    {"stap": "taak-001", "status": "geslaagd", "bewijs": "ok",
     "tijdstip": "2026-09-04T09:05:00+00:00"}]), encoding="utf-8")
PYEOF
}

# ——— 1: planten zonder bevestiging → concept, map bestaat niet ———
UIT="$(printf '{"profiel":"dev-werkplaats","doel":"%s/nieuw"}' "$TMP" | "$PY" "$REPO/adapter.py" plant)"
echo "$UIT" | grep -q '"bevestiging_vereist": true' || FAIL "FAIL 1: geen bevestigingsvlag"
test ! -d "$TMP/nieuw" || FAIL "FAIL 1: concept-modus heeft uitgevoerd — poort geschonden"
echo "OK 1: planten zonder bevestiging → concept alleen, poort dicht"

# ——— 2: taak zonder bevestiging → lijst, niets uitgevoerd ———
BOOM boom-taak
"$PY" - "$TMP/boom-taak" <<'PYEOF'
import json, sys
from pathlib import Path
doel = Path(sys.argv[1])
(doel / "takenlijst.json").write_text(json.dumps([{
    "id": "taak-002", "titel": "kweekbestand",
    "commando": "printf x > kweek2.txt && echo KWEEK-OK",
    "bewijs": {"type": "shell_check", "commando": "test -f kweek2.txt && echo KWEEK-OK",
               "verwacht_substr": "KWEEK-OK"}}]), encoding="utf-8")
PYEOF
UIT="$(printf '{"doel":"%s/boom-taak"}' "$TMP" | "$PY" "$REPO/adapter.py" taak)"
echo "$UIT" | grep -q '"bevestiging_vereist": true' || FAIL "FAIL 2: geen bevestigingsvlag"
test ! -f "$TMP/boom-taak/kweek2.txt" || FAIL "FAIL 2: uitgevoerd zonder bevestiging"
echo "OK 2: taak zonder bevestiging → lijst alleen, niets uitgevoerd"

# ——— 3: taak mét bevestiging → uitgevoerd, bewijs aanwezig ———
UIT="$(printf '{"doel":"%s/boom-taak","taak_id":"taak-002","bevestig":true}' "$TMP" \
  | "$PY" "$REPO/adapter.py" taak)" || FAIL "FAIL 3: bevestigde taak faalde"
test -f "$TMP/boom-taak/kweek2.txt" || FAIL "FAIL 3: bewijsbestand ontbreekt"
"$PY" - "$TMP/boom-taak" <<'PYEOF'
import json, sys
from pathlib import Path
entries = json.loads((Path(sys.argv[1]) / "logboek.json").read_text(encoding="utf-8"))
runs = [e["status"] for e in entries if e.get("type") == "run"]
assert "gestart" in runs and "beeindigd" in runs, f"latch incompleet: {runs}"
PYEOF
echo "OK 3: bevestigde taak → uitgevoerd + run-latch gestart/beeindigd"

# ——— 4: taak zonder bewijs bestaat niet — ook mét bevestiging ———
BOOM boom-onbewezen
"$PY" - "$TMP/boom-onbewezen" <<'PYEOF'
import json, sys
from pathlib import Path
doel = Path(sys.argv[1])
(doel / "takenlijst.json").write_text(json.dumps([
    {"id": "taak-003", "titel": "zonder bewijs"}]), encoding="utf-8")
PYEOF
UIT="$(printf '{"doel":"%s/boom-onbewezen","taak_id":"taak-003","bevestig":true}' "$TMP" \
  | "$PY" "$REPO/adapter.py" taak 2>/dev/null)" && FAIL "FAIL 4: onbewezen taak gaf exit 0"
echo "$UIT" | grep -q '"ok": false' || FAIL "FAIL 4: geen nette fout"
echo "OK 4: taak zonder bewijs bestaat niet (poort-regel §11)"

# ——— 5: actie-menu van een gezonde boom ———
UIT="$(printf '{"doel":"%s/boom-taak"}' "$TMP" | "$PY" "$REPO/adapter.py" acties)"
echo "$UIT" | grep -q '"taak"' || FAIL "FAIL 5: taak mist in het menu"
echo "$UIT" | grep -q '"hervat"' || FAIL "FAIL 5: hervat mist in het menu"
echo "$UIT" | grep -qv '"planten"' || FAIL "FAIL 5: planten hoort niet bij een geplante boom"
echo "OK 5: actie-menu toont mogelijkheden zonder planten-dubbel"

# ——— 6: mens-moment zichtbaar bij ratificatie-wachter ———
"$PY" - "$TMP/boom-taak" <<'PYEOF'
import json, sys
from pathlib import Path
doel = Path(sys.argv[1])
logboek = doel / "logboek.json"
entries = json.loads(logboek.read_text(encoding="utf-8"))
entries.append({"stap": "stap-review", "status": "review_ok_wacht_ratificatie",
                "bewijs": "reviewer akkoord", "tijdstip": "2026-09-04T09:20:00+00:00"})
logboek.write_text(json.dumps(entries), encoding="utf-8")
PYEOF
UIT="$(printf '{"doel":"%s/boom-taak"}' "$TMP" | "$PY" "$REPO/adapter.py" acties)"
echo "$UIT" | grep -q '"soort": "ratificatie"' || FAIL "FAIL 6: mens-moment niet gerapporteerd"
echo "OK 6: ratificatie-wachter → expliciet mens-moment in het menu"

# ——— 7: corrupt logboek → actie-menu weigert netjes ———
BOOM boom-kapot
echo "{kapot" > "$TMP/boom-kapot/logboek.json"
UIT="$(printf '{"doel":"%s/boom-kapot"}' "$TMP" | "$PY" "$REPO/adapter.py" acties 2>/dev/null)" \
  && FAIL "FAIL 7: corrupt logboek gaf exit 0"
echo "$UIT" | grep -q 'corrupt' || FAIL "FAIL 7: geen nette fout"
echo "OK 7: corrupt logboek → nette fout, nooit auto-repareren"

rm -rf "$TMP"
echo ""
echo "SLICE 3 E2E: ALLE 7 CRITERIA GROEN"
