#!/usr/bin/env bash
# Test 1 — "Schone-pleg-plant": verse kloon, geen voorkennis, plant een tweede-brein.
# Controleert alle 7 criteria uit docs/superpowers/testprotocol-fase-2.md.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Zoek een Python 3.11+
PY=""
for kandidaat in python3.14 python3.13 python3.12 python3.11 python3; do
  if command -v "$kandidaat" >/dev/null 2>&1; then
    if "$kandidaat" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
      PY="$kandidaat"
      break
    fi
  fi
done
test -n "$PY" || { echo "FAIL 1.7: geen Python 3.11+ gevonden"; exit 1; }

# ——— Criterium 1.1: verse kloon plant zonder fout ———
git clone -q "$REPO" "$TMP/kloon"
VOOR="$(cd "$TMP/kloon" && git status --porcelain)"
test -z "$VOOR" || { echo "FAIL 1.5: kloon is niet schoon vóór de run"; exit 1; }

if ! "$PY" "$TMP/kloon/seed.py" --profiel tweede-brein --doel "$TMP/plant"; then
  echo "FAIL 1.1: seed.py faalde in de schone kloon"
  exit 1
fi
echo "OK 1.1: verse kloon plant zonder fout"
echo "OK 1.7: draait op $PY, geen pip-install"

# ——— Criterium 1.5: geen schrijfactie buiten de doelmap ———
NA="$(cd "$TMP/kloon" && git status --porcelain)"
test -z "$NA" || { echo "FAIL 1.5: kloon veranderd tijdens de run:"; echo "$NA"; exit 1; }
echo "OK 1.5: geen schrijfactie buiten de doelmap (kloon nog schoon)"

# ——— Criterium 1.2 + 1.3 + 1.4: logboek, structuur, byte-gelijkheid ———
"$PY" - "$TMP" "$TMP/kloon" <<'PYEOF'
import hashlib, json, sys
from pathlib import Path

tmp, kloon = Path(sys.argv[1]), Path(sys.argv[2])
plant = tmp / "plant"

# Criterium 1.2: 8 stappen (7 geslaagd + 1 wacht_op_mens) + 1 geboorte-systeem-entry
# Protocol-uitbreiding fase 5 taak 1, vastgelegd vóór de run: seed.py maakt het
# geboortebewijs vol en logt dat append-only als negende entry.
entries = json.loads((plant / "logboek.json").read_text(encoding="utf-8"))
assert len(entries) == 9, f"1.2 FAIL: {len(entries)} entries, verwacht 9 (8 stappen + 1 geboorte)"
assert all(e["status"] in ("geslaagd", "wacht_op_mens") for e in entries), \
    f"1.2 FAIL: niet-geslaagde stappen: {[e for e in entries if e['status'] not in ('geslaagd', 'wacht_op_mens')]}"
assert sum(e["status"] == "wacht_op_mens" for e in entries) == 1, "1.2 FAIL: verwacht precies 1 wacht_op_mens"
print("OK 1.2: 8 stappen — 7 geslaagd, 1 wacht_op_mens")

# Criterium 1.3: vijf kernmappen + INDEX.md + geboortebewijs
for map_ in ("identiteit", "kennis", "projecten", "inbox", "logboek"):
    assert (plant / map_).is_dir(), f"1.3 FAIL: map {map_} ontbreekt"
assert (plant / "INDEX.md").is_file(), "1.3 FAIL: INDEX.md ontbreekt"
assert (plant / "geboortebewijs.json").is_file(), "1.3 FAIL: geboortebewijs.json ontbreekt"
print("OK 1.3: vijf kernmappen + INDEX.md + geboortebewijs bestaan")

# Criterium 1.4: byte-voor-byte gelijk aan sjablonen
sjablonen = kloon / "profielen" / "tweede-brein" / "sjablonen"
for sjabloon, doel in (
    ("INDEX.md", "INDEX.md"),
    ("AGENT-ROL.md", "identiteit/AGENT-ROL.md"),
    ("REGELS.md", "inbox/REGELS.md"),
    ("geboortebewijs.json.template", "geboortebewijs.json"),
):
    h1 = hashlib.sha256((sjablonen / sjabloon).read_bytes()).hexdigest()
    h2 = hashlib.sha256((plant / doel).read_bytes()).hexdigest()
    assert h1 == h2, f"1.4 FAIL: {doel} != sjabloon {sjabloon}"
print("OK 1.4: alle gekopieerde bestanden byte-voor-byte gelijk aan sjablonen")
PYEOF

# ——— Criterium 1.6: herstart-gedrag (niet-idempotente stap dynamisch gevonden) ———
"$PY" - "$TMP" "$TMP/kloon" <<'PYEOF'
import json, subprocess, sys
from pathlib import Path

tmp, kloon = Path(sys.argv[1]), Path(sys.argv[2])
profiel = json.loads((kloon / "profielen/tweede-brein/profiel.json").read_text(encoding="utf-8"))
niet_idem = [s["id"] for s in profiel["stappen"] if s.get("idempotent") is False]
assert niet_idem, "1.6 FAIL: geen niet-idempotente stap gevonden in profiel"
print(f"OK 1.6a: niet-idempotente stap dynamisch gevonden: {niet_idem[0]} (geen hardcode)")

# tweede run op dezelfde doelmap
r = subprocess.run(["python3.13", str(kloon / "seed.py"), "--profiel", "tweede-brein",
                    "--doel", str(tmp / "plant")], capture_output=True, text=True)
entries = json.loads((tmp / "plant" / "logboek.json").read_text(encoding="utf-8"))
gefaald = [e for e in entries if e["status"] == "gefaald"]
assert not gefaald, f"1.6 FAIL: herstart produceerde gefaalde stappen: {gefaald}"
print(f"OK 1.6b: herstart faalt niet onnodig; logboek ({len(entries)} entries) bevat nul 'gefaald'")
PYEOF

echo ""
echo "TEST 1 OK: schone-pleg-plant — 7/7 criteria geslaagd"
