#!/usr/bin/env bash
# E2E: plant het tweede-brein-profiel in een schone tmp-map en bewijst het resultaat.
set -euo pipefail
cd "$(dirname "$0")/.."

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Zoek een Python 3.11+ (de systeem-python op macOS is vaak te oud)
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

"$PY" seed.py --profiel tweede-brein --doel "$TMP/plant"

# Bewijs 1: vijf kernmappen
for map in identiteit kennis projecten inbox logboek; do
  test -d "$TMP/plant/$map" || { echo "FAIL: map $map ontbreekt"; exit 1; }
done

# Bewijs 2: INDEX.md in de root van de plant
test -s "$TMP/plant/INDEX.md" || { echo "FAIL: INDEX.md ontbreekt"; exit 1; }

# Bewijs 3: logboek is valide JSON en alles is geslaagd of wacht_op_mens
python3 - "$TMP/plant/logboek.json" <<'PY'
import json, sys
entries = json.load(open(sys.argv[1], encoding="utf-8"))
assert entries, "logboek is leeg"
assert all(e["status"] in ("geslaagd", "wacht_op_mens") for e in entries), \
    f"logboek bevat niet-geslaagde stappen: {[e for e in entries if e['status'] not in ('geslaagd', 'wacht_op_mens')]}"
print("E2E OK: alle stappen geslaagd of wacht_op_mens")
PY
