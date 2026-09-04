#!/usr/bin/env bash
# Slice 2 — E2E: live status per boom (levensignaal) end-to-end.
# Protocol: faalcontract-afleiding uit het logboek (rood/groen/rust/gestopt),
# crash-scenario: run-latch 'gestart' met dood pid → 'gestopt', en de loop
# schrijft een echte latch rond een taak-run.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="python3"
TMP="$(mktemp -d)"
export GROWKIT_OERWOUD_STAAT="$TMP/growkit-home/oerwoud.json"

FAIL() { echo "$1"; exit 1; }

 Boom() {
  local naam="$1"
  mkdir -p "$TMP/$naam"
  "$PY" - "$TMP/$naam" <<'PYEOF'
import json, sys
from pathlib import Path
doel = Path(sys.argv[1])
(doel / "geboortebewijs.json").write_text(json.dumps({
    "boom_id": doel.name, "profiel": "dev-werkplaats", "machine": "e2e",
    "locatie": str(doel), "geplant_op": "2026-09-04T09:00:00+00:00"}),
    encoding="utf-8")
PYEOF
}

LATCH() { # $1=boom $2=status $3=pid(Optioneel)
  "$PY" - "$TMP/$1" "${@:2}" <<'PYEOF'
import json, sys, os, datetime
from pathlib import Path
doel, status = Path(sys.argv[1]), sys.argv[2]
pid = int(sys.argv[3]) if len(sys.argv) > 3 else os.getpid()
logboek = doel / "logboek.json"
entries = json.loads(logboek.read_text(encoding="utf-8")) if logboek.exists() else []
entry = {"type": "run", "status": status,
         "tijdstip": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
if status == "gestart":
    entry["pid"] = pid
entries.append(entry)
logboek.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
PYEOF
}

SIG() { # $1=boom → faalcontract naar stdout
  printf '{"doel":"%s"}' "$TMP/$1" | "$PY" "$REPO/adapter.py" levensignaal \
    | "$PY" -c "import json,sys; print(json.load(sys.stdin)['data']['levensignaal']['faalcontract'])"
}

# ——— 1: lege boom → rust ———
Boom boom-rust
[ "$(SIG boom-rust)" = "rust" ] || FAIL "FAIL 1: lege boom niet 'rust'"
echo "OK 1: lege boom → rust"

# ——— 2: faal als laatste → rood ———
Boom boom-rood
"$PY" - "$TMP/boom-rood" <<'PYEOF'
import json, sys
from pathlib import Path
logboek = Path(sys.argv[1]) / "logboek.json"
logboek.write_text(json.dumps([
    {"stap": "taak-001", "status": "geslaagd", "bewijs": "ok",
     "tijdstip": "2026-09-04T09:05:00+00:00"},
    {"stap": "taak-002", "status": "gefaald", "bewijs": "zocht OK, kreeg ''",
     "tijdstip": "2026-09-04T09:10:00+00:00"}]), encoding="utf-8")
PYEOF
[ "$(SIG boom-rood)" = "rood" ] || FAIL "FAIL 2: faal als laatste niet 'rood'"
echo "OK 2: onopgevolgde faal → rood (faalcontract staat)"

# ——— 3: geslaagd na faal → groen ———
Boom boom-groen
"$PY" - "$TMP/boom-groen" <<'PYEOF'
import json, sys
from pathlib import Path
logboek = Path(sys.argv[1]) / "logboek.json"
logboek.write_text(json.dumps([
    {"stap": "taak-001", "status": "gefaald", "bewijs": "kapot",
     "tijdstip": "2026-09-04T09:05:00+00:00"},
    {"stap": "taak-001", "status": "geslaagd", "bewijs": "hersteld",
     "tijdstip": "2026-09-04T09:20:00+00:00"}]), encoding="utf-8")
PYEOF
[ "$(SIG boom-groen)" = "groen" ] || FAIL "FAIL 3: herstel niet 'groen'"
echo "OK 3: geslaagd ná de faal → groen"

# ——— 4: crash-scenario — latch gestart + dood pid → gestopt ———
Boom boom-crash
LATCH boom-crash gestart 2147483000
"$PY" - "$TMP/boom-crash" <<'PYEOF'
import json, sys
from pathlib import Path
logboek = Path(sys.argv[1]) / "logboek.json"
entries = json.loads(logboek.read_text(encoding="utf-8")) if logboek.exists() else []
entries.append({"stap": "taak-001", "status": "geslaagd", "bewijs": "ok",
                "tijdstip": "2026-09-04T09:01:00+00:00"})
logboek.write_text(json.dumps(entries), encoding="utf-8")
PYEOF
[ "$(SIG boom-crash)" = "gestopt" ] || FAIL "FAIL 4: crash-latch niet 'gestopt'"
UIT="$(printf '{"doel":"%s"}' "$TMP/boom-crash" | "$PY" "$REPO/adapter.py" levensignaal)"
echo "$UIT" | grep -q '"taak_actief": false' || FAIL "FAIL 4: taak_actief niet false na crash"
echo "OK 4: run-latch met dood pid → gestopt (crash zichtbaar, herstart nodig)"

# ——— 5: levende run → taak_actief ———
Boom boom-actief
LATCH boom-actief gestart $$
UIT="$(printf '{"doel":"%s"}' "$TMP/boom-actief" | "$PY" "$REPO/adapter.py" levensignaal)"
echo "$UIT" | grep -q '"taak_actief": true' || FAIL "FAIL 5: levende run niet actief"
[ "$(SIG boom-actief)" = "groen" ] || FAIL "FAIL 5: actieve run niet 'groen'"
echo "OK 5: latch met levend pid → taak_actief"

# ——— 6: loop schrijft een echte latch rond een taak-run ———
Boom boom-loop
"$PY" - "$TMP/boom-loop" <<'PYEOF'
import json, sys
from pathlib import Path
doel = Path(sys.argv[1])
(doel / "takenlijst.json").write_text(json.dumps([{
    "id": "taak-001", "titel": "kweekbestand",
    "commando": "printf x > kweek.txt && echo KWEEK-OK",
    "bewijs": {"type": "shell_check", "commando": "test -f kweek.txt && echo KWEEK-OK",
               "verwacht_substr": "KWEEK-OK"}
}]), encoding="utf-8")
PYEOF
printf '{"doel":"%s","taak_id":"taak-001","bevestig":true}' "$TMP/boom-loop" \
  | "$PY" "$REPO/adapter.py" taak >/dev/null 2>&1 || true
LATCHES="$("$PY" - "$TMP/boom-loop" <<'PYEOF'
import json, sys
from pathlib import Path
logboek = Path(sys.argv[1]) / "logboek.json"
entries = json.loads(logboek.read_text(encoding="utf-8")) if logboek.exists() else []
runs = [e["status"] for e in entries if e.get("type") == "run"]
print(",".join(runs))
PYEOF
)"
echo "$LATCHES" | grep -q "gestart" || FAIL "FAIL 6: loop schreef geen 'gestart'-latch"
echo "$LATCHES" | grep -q "beeindigd" || FAIL "FAIL 6: loop sloot de run niet af"
[ "$(SIG boom-loop)" = "groen" ] || FAIL "FAIL 6: na afgeronde taak-run niet 'groen'"
echo "OK 6: loop-run → latch gestart+beeindigd, levensignaal groen"

# ——— 7: corrupt logboek → nette fout ———
Boom boom-kapot
echo "{kapot" > "$TMP/boom-kapot/logboek.json"
UIT="$(printf '{"doel":"%s"}' "$TMP/boom-kapot" | "$PY" "$REPO/adapter.py" levensignaal 2>/dev/null)" \
  && FAIL "FAIL 7: corrupt logboek gaf exit 0"
echo "$UIT" | grep -q 'corrupt' || FAIL "FAIL 7: geen nette fout"
echo "OK 7: corrupt logboek → nette fout (mens), nooit auto-repareren"

rm -rf "$TMP"
echo ""
echo "SLICE 2 E2E: ALLE 7 CRITERIA GROEN"
