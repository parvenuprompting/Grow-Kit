#!/usr/bin/env bash
# Test 3 — Review-laag in de praktijk (fase-3-plan task 4).
# Controleert de 5 criteria; bewijs in docs/superpowers/bewijs/fase-3-test3.md
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"

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

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PLANT() {
  # $1 = pad naar reviewconfig (of "-"), $2 = submap-naam voor verse doelmap
  "$PY" - "$REPO" "$TMP" "$1" "$2" <<'PYEOF'
import json
import sys
from pathlib import Path

repo, tmp, rc_pad, naam = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
repo, tmp = Path(repo), Path(tmp)
sys.path.insert(0, str(repo))
from kern.growkit_motor import voer_uit  # noqa: E402

doel = tmp / f"plant-{naam}"
doel.mkdir(parents=True)
logboek = doel / "logboek.json"
logboek.write_text("[]", encoding="utf-8")
from kern.growkit_motor import vervang_growkit_pad
profiel = json.loads((repo / "profielen/tweede-brein/profiel.json").read_text(encoding="utf-8"))
profiel = vervang_growkit_pad(profiel, repo)
sjablonen = repo / "profielen" / "tweede-brein" / "sjablonen"
reviewconfig = None if rc_pad == "-" else json.loads(Path(rc_pad).read_text(encoding="utf-8"))
ok = voer_uit(profiel, doel, logboek, sjablonen, reviewconfig=reviewconfig)
print("PLANT-EXIT", 0 if ok else 2)
sys.exit(0 if ok else 2)
PYEOF
}

CHECK_LOG() {
  # $1 = plant-submap, $2 = verwachte status stap-008; $3/$4 optioneel: rol + oordeel
  "$PY" - "$TMP/plant-$1/logboek.json" "$2" "$3" "$4" <<'PYEOF'
import json
import sys
from pathlib import Path

entries = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert len(entries) == 8, f"verwacht 8 entries, kreeg {len(entries)}"
stap8 = [e for e in entries if e["stap"] == "stap-008"][0]
assert stap8["status"] == sys.argv[2], f"stap-008 status={stap8['status']}, verwacht {sys.argv[2]}"
machine = [e for e in entries if e["stap"] != "stap-008"]
assert all(e["status"] == "geslaagd" for e in machine), \
    f"machine-stap niet geslaagd: {[e['stap'] for e in machine if e['status'] != 'geslaagd']}"
if sys.argv[3] != "-":
    assert stap8.get("review_rol") == sys.argv[3], f"review_rol={stap8.get('review_rol')}"
    assert stap8.get("review_oordeel") == sys.argv[4], f"review_oordeel={stap8.get('review_oordeel')}"
else:
    assert "review_rol" not in stap8, "zonder reviewer mag er geen review_rol in het log staan"
print("LOG-OK")
PYEOF
}

# ——— Criterium 1: reviewer "geslaagd" → ratificatie, motor door, exit 0 ———
cat > "$TMP/rc-geslaagd.json" <<'JSON'
{"rollen": {"reviewer": {"type": "cli", "commando": "echo geslaagd"}}}
JSON
PLANT "$TMP/rc-geslaagd.json" geslaagd >/dev/null
CHECK_LOG geslaagd review_ok_wacht_ratificatie reviewer geslaagd
echo "OK 1: reviewer-geslaagd → review_ok_wacht_ratificatie, exit 0, motor door"

# ——— Criterium 2: reviewer "onduidelijk" → klassiek mens-moment ———
cat > "$TMP/rc-onduidelijk.json" <<'JSON'
{"rollen": {"reviewer": {"type": "cli", "commando": "echo misschien"}}}
JSON
PLANT "$TMP/rc-onduidelijk.json" onduidelijk >/dev/null
CHECK_LOG onduidelijk wacht_op_mens reviewer onduidelijk
echo "OK 2: reviewer-onduidelijk → wacht_op_mens (klassiek mens-moment)"

# ——— Criterium 3: zonder reviewconfig → identiek aan fase-2 (regressie) ———
PLANT - geen-config >/dev/null
CHECK_LOG geen-config wacht_op_mens - -
echo "OK 3: geen reviewconfig → identiek fase-2-gedrag; géén review-velden in log"

# ——— Criteria 4+5 zijn in elke CHECK_LOG hard gecheckt:
# 4: de 7 machine-stappen zijn in alle drie runs geslaagd (reviewer raakt ze nooit);
# 5: bij 1+2 vermeldt het log de rol én het oordeel ———
echo "OK 4+5: machine-stappen onaangetast; log vermeldt rol + oordeel"

echo ""
echo "TEST 3 OK: review-laag in de praktijk — 5/5 criteria geslaagd"
