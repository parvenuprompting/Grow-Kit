#!/usr/bin/env bash
# Slice 6 — E2E: nachtfabriek-modus end-to-end via de adapter.
# Protocol: plan samenstellen (concept → bevestiging) → ronde uitvoeren via
# het harnas (faalcontract actief) → ochtendstatus lezen.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="python3"
TMP="$(mktemp -d)"
export GROWKIT_OERWOUD_STAAT="$TMP/growkit-home/oerwoud.json"

FAIL() { echo "$1"; exit 1; }

BOOM="$TMP/boom-nacht"
mkdir -p "$BOOM"
"$PY" - "$BOOM" <<'PYEOF'
import json, sys
from pathlib import Path
doel = Path(sys.argv[1])
(doel / "geboortebewijs.json").write_text(json.dumps({
    "boom_id": "boom-nacht", "profiel": "dev-werkplaats", "machine": "e2e",
    "locatie": str(doel), "geplant_op": "2026-09-04T09:00:00+00:00"}), encoding="utf-8")
(doel / "logboek.json").write_text("[]", encoding="utf-8")
(doel / "takenlijst.json").write_text(json.dumps([
    {"id": "nacht-1", "titel": "kweekbestand",
     "commando": "printf x > kweek-nacht.txt && echo KWEEK-OK",
     "bewijs": {"type": "shell_check", "commando": "test -f kweek-nacht.txt && echo KWEEK-OK",
                "verwacht_substr": "KWEEK-OK"}},
    {"id": "nacht-2", "titel": "faalt bewust",
     "commando": "exit 1",
     "bewijs": {"type": "shell_check", "commando": "test -f nooit-bestaand.txt",
                "verwacht_substr": "X"}}]), encoding="utf-8")
PYEOF

# ——— 1: plan-concept zonder bevestiging → niets weggeschreven ———
UIT="$(printf '{"doel":"%s","taken":["nacht-1"]}' "$BOOM" | "$PY" "$REPO/adapter.py" nachtplan)"
echo "$UIT" | grep -q '"bevestiging_vereist": true' || FAIL "FAIL 1: geen bevestigingsvlag"
test ! -f "$BOOM/nachtplan.json" || FAIL "FAIL 1: concept schreef al weg"
echo "OK 1: nachtplan-concept zonder bevestiging → niets weggeschreven"

# ——— 2: plan mét bevestiging → append-only weggeschreven ———
printf '{"doel":"%s","taken":["nacht-1"],"bevestig":true}' "$BOOM" \
  | "$PY" "$REPO/adapter.py" nachtplan >/dev/null || FAIL "FAIL 2: plan faalde"
test -f "$BOOM/nachtplan.json" || FAIL "FAIL 2: plan ontbreekt"
echo "OK 2: nachtplan weggeschreven"

# ——— 3: herschrijven geweigerd — nooit overschrijven ———
UIT="$(printf '{"doel":"%s","taken":["nacht-1"],"bevestig":true}' "$BOOM" \
  | "$PY" "$REPO/adapter.py" nachtplan 2>/dev/null)" && FAIL "FAIL 3: herschrijven gaf exit 0"
echo "$UIT" | grep -qi 'overschrij' || FAIL "FAIL 3: fouttekst noemt overschrijven niet"
echo "OK 3: bestaand plan → geweigerd (append-only)"

# ——— 4: ronde zonder bevestiging → concept, niets uitgevoerd ———
UIT="$(printf '{"doel":"%s"}' "$BOOM" | "$PY" "$REPO/adapter.py" nachtronde)"
echo "$UIT" | grep -q '"bevestiging_vereist": true' || FAIL "FAIL 4: geen bevestigingsvlag"
test ! -f "$BOOM/kweek-nacht.txt" || FAIL "FAIL 4: ronde draaide zonder bevestiging"
echo "OK 4: nachtronde zonder bevestiging → concept alleen"

# ——— 5: ronde mét bevestiging → taak uitgevoerd, verslag append-only ———
UIT="$(printf '{"doel":"%s","bevestig":true}' "$BOOM" | "$PY" "$REPO/adapter.py" nachtronde)" \
  || FAIL "FAIL 5: nachtronde faalde onverwacht"
test -f "$BOOM/kweek-nacht.txt" || FAIL "FAIL 5: bewijsbestand ontbreekt"
"$PY" - "$BOOM" <<'PYEOF'
import json, sys
from pathlib import Path
doel = Path(sys.argv[1])
rondes = json.loads((doel / "nachtrondes.json").read_text(encoding="utf-8"))
assert len(rondes) == 1 and rondes[0]["geslaagd"] is True, f"ronde-verslag: {rondes}"
logboek = json.loads((doel / "logboek.json").read_text(encoding="utf-8"))
runs = [e["status"] for e in logboek if e.get("type") == "run"]
assert "gestart" in runs and "beeindigd" in runs, f"latch incompleet: {runs}"
PYEOF
echo "OK 5: ronde uitgevoerd — verslag + run-latch (gestart/beeindigd)"

# ——— 6: faalcontract — ronde met faal stopt, geen retries ———
printf '{"doel":"%s","taken":["nacht-1","nacht-2"],"bevestig":true}' "$BOOM" \
  | "$PY" "$REPO/adapter.py" nachtplan >/dev/null && FAIL "FAIL 6: tweede plan werd geaccepteerd — overschrijven"
# nieuw plan kan niet; gebruik dezelfde boom met alleen een faal-plan via een tweede boom
BOOM2="$TMP/boom-faal"
mkdir -p "$BOOM2"
"$PY" - "$BOOM2" <<'PYEOF'
import json, sys
from pathlib import Path
doel = Path(sys.argv[1])
(doel / "geboortebewijs.json").write_text(json.dumps({
    "boom_id": "boom-faal", "profiel": "dev-werkplaats", "machine": "e2e",
    "locatie": str(doel), "geplant_op": "2026-09-04T09:00:00+00:00"}), encoding="utf-8")
(doel / "logboek.json").write_text("[]", encoding="utf-8")
(doel / "takenlijst.json").write_text(json.dumps([
    {"id": "faal-1", "titel": "faalt bewust",
     "commando": "exit 1",
     "bewijs": {"type": "shell_check", "commando": "test -f nooit-bestaand.txt",
                "verwacht_substr": "X"}},
    {"id": "na-faal", "titel": "mag niet draaien",
     "commando": "printf x > na-faal.txt && echo OK",
     "bewijs": {"type": "shell_check", "commando": "test -f na-faal.txt && echo OK",
                "verwacht_substr": "OK"}}]), encoding="utf-8")
PYEOF
printf '{"doel":"%s","taken":["faal-1","na-faal"],"bevestig":true}' "$BOOM2" \
  | "$PY" "$REPO/adapter.py" nachtplan >/dev/null
UIT="$(printf '{"doel":"%s","bevestig":true}' "$BOOM2" | "$PY" "$REPO/adapter.py" nachtronde 2>/dev/null)" \
  && FAIL "FAIL 6: ronde met faal gaf exit 0"
echo "$UIT" | grep -q '"ok": false' || FAIL "FAIL 6: geen faalcontract-antwoord"
test ! -f "$BOOM2/na-faal.txt" || FAIL "FAIL 6: taak ná de faal is alsnog uitgevoerd"
"$PY" - "$BOOM2" <<'PYEOF'
import json, sys
from pathlib import Path
doel = Path(sys.argv[1])
rondes = json.loads((doel / "nachtrondes.json").read_text(encoding="utf-8"))
assert rondes[0]["geslaagd"] is False, "ronde-verslag zegt geslaagd"
pogingen = [t for t in rondes[0]["taken"] if t["taak"] == "faal-1"]
assert len(pogingen) == 1, f"retry gedetecteerd: {len(pogingen)} pogingen"
PYEOF
echo "OK 6: faalcontract — ronde gestopt bij eerste faal, geen retries"

# ——— 7: ochtendstatus — plan + rondes + levensignaal in één antwoord ———
UIT="$(printf '{"doel":"%s"}' "$BOOM" | "$PY" "$REPO/adapter.py" nachtstatus)"
echo "$UIT" | grep -q '"plan"' || FAIL "FAIL 7: plan mist in de status"
echo "$UIT" | grep -q '"rondes"' || FAIL "FAIL 7: rondes missen in de status"
echo "$UIT" | grep -q '"levensignaal"' || FAIL "FAIL 7: levensignaal mist in de status"
echo "$UIT" | grep -q '"faalcontract": "groen"' || FAIL "FAIL 7: levensignaal niet groen na geslaagde ronde"
echo "OK 7: nachtstatus — plan + rondes + levensignaal, één bron"

rm -rf "$TMP"
echo ""
echo "SLICE 6 E2E: ALLE 7 CRITERIA GROEN"
