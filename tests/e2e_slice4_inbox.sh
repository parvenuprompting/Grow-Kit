#!/usr/bin/env bash
# Slice 4 — E2E: inbox-curatiescherm end-to-end via de adapter.
# Protocol: VOORSTEL tonen → goedkeuren (append-only geboekt, inbox gemarkeerd)
# → afwijzen met reden → collisie geweigerd → niets gewist.
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
    "boom_id": "brein-s4", "profiel": "tweede-brein", "machine": "e2e",
    "locatie": str(brein), "geplant_op": "2026-09-04T09:00:00+00:00"}), encoding="utf-8")
PYEOF
"$PY" -c "from kern import growkit_oerwoud; growkit_oerwoud.sla_brein_pad(__import__('pathlib').Path('$BREIN'))" \
  || FAIL "voorwerk: oerwoud-staat schrijven faalde"

# ——— 1: lege inbox → lege lijst ———
UIT="$(printf '{}' | "$PY" "$REPO/adapter.py" inbox)"
echo "$UIT" | grep -q '"items": \[\]' || FAIL "FAIL 1: inbox niet leeg"
echo "OK 1: lege inbox → lege lijst"

# ——— 2: VOORSTEL aanmaken → zichtbaar ———
printf 'het vliegwiel draait' > "$BREIN/inbox/VOORSTEL-abc-123-inzicht.md"
printf 'geen voorstel, gewoon notitie' > "$BREIN/inbox/REGELS.md"
UIT="$(printf '{}' | "$PY" "$REPO/adapter.py" inbox)"
echo "$UIT" | grep -q 'VOORSTEL-abc-123-inzicht.md' || FAIL "FAIL 2: voorstel niet zichtbaar"
echo "$UIT" | grep -q 'vliegwiel' || FAIL "FAIL 2: inhoud niet meegeleverd"
echo "$UIT" | grep -q 'REGELS.md' && FAIL "FAIL 2: REGELS.md lekte mee (drift-guard)"
echo "OK 2: VOORSTEL zichtbaar, REGELS.md reist niet mee"

# ——— 3: goedkeuring → geboekt in kennis/, inbox gemarkeerd .geboekt ———
UIT="$(printf '{"items":[{"naam":"VOORSTEL-abc-123-inzicht.md","besluit":"goedgekeurd"}]}' \
  | "$PY" "$REPO/adapter.py" curate)" || FAIL "FAIL 3: curate faalde"
test -f "$BREIN/kennis/goedgekeurd/VOORSTEL-abc-123-inzicht.md" \
  || FAIL "FAIL 3: niet geboekt in kennis/goedgekeurd"
grep -q 'vliegwiel' "$BREIN/kennis/goedgekeurd/VOORSTEL-abc-123-inzicht.md" \
  || FAIL "FAIL 3: inhoud beschadigd bij boeken"
test -f "$BREIN/inbox/VOORSTEL-abc-123-inzicht.md.geboekt" \
  || FAIL "FAIL 3: inbox-copy niet gemarkeerd"
test ! -f "$BREIN/inbox/VOORSTEL-abc-123-inzicht.md" \
  || FAIL "FAIL 3: onbesloten copy blijft openstaan"
echo "OK 3: goedkeuring → geboekt + gemarkeerd (append-only, niets gewist)"

# ——— 4: afwijzing vereist reden; afwijzing markeert .afgewezen ———
printf 'tweede inzicht' > "$BREIN/inbox/VOORSTEL-def-456-anders.md"
UIT="$(printf '{"items":[{"naam":"VOORSTEL-def-456-anders.md","besluit":"afgewezen"}]}' \
  | "$PY" "$REPO/adapter.py" curate 2>/dev/null)" && FAIL "FAIL 4: afwijzing zonder reden gaf exit 0"
echo "$UIT" | grep -q 'reden' || FAIL "FAIL 4: fouttekst noemt reden niet"
UIT="$(printf '{"items":[{"naam":"VOORSTEL-def-456-anders.md","besluit":"afgewezen","reden":"dubbel"}]}' \
  | "$PY" "$REPO/adapter.py" curate)" || FAIL "FAIL 4: afwijzing mét reden faalde"
test -f "$BREIN/inbox/VOORSTEL-def-456-anders.md.afgewezen" \
  || FAIL "FAIL 4: afwijzing niet gemarkeerd"
grep -q 'dubbel' "$BREIN/kennis/afwijzingen.md" || FAIL "FAIL 4: reden niet gelogd"
echo "OK 4: afwijzing → gemarkeerd + reden gelogd"

# ——— 5: collisie → weigering, nooit overschrijven ———
printf 'derde inzicht' > "$BREIN/inbox/VOORSTEL-ghi-789-collisie.md"
mkdir -p "$BREIN/kennis/goedgekeurd"
printf 'BESTAAND' > "$BREIN/kennis/goedgekeurd/VOORSTEL-ghi-789-collisie.md"
UIT="$(printf '{"items":[{"naam":"VOORSTEL-ghi-789-collisie.md","besluit":"goedgekeurd"}]}' \
  | "$PY" "$REPO/adapter.py" curate 2>/dev/null)" && FAIL "FAIL 5: collisie gaf exit 0"
echo "$UIT" | grep -qi 'overschrij' || FAIL "FAIL 5: fouttekst noemt overschrijven niet"
test "$(cat "$BREIN/kennis/goedgekeurd/VOORSTEL-ghi-789-collisie.md")" = "BESTAAND" \
  || FAIL "FAIL 5: bestaand bestand overschreven"
echo "OK 5: collisie geweigerd — nooit overschrijven"

# ——— 6: curatie gelogd in het brein-logboek (append-only) ———
"$PY" - "$BREIN" <<'PYEOF'
import json, sys
from pathlib import Path
entries = json.loads((Path(sys.argv[1]) / "logboek.json").read_text(encoding="utf-8"))
curaties = [e for e in entries if e.get("type") == "curatie"]
assert len(curaties) == 2, f"verwacht 2 curatie-entries, kreeg {len(curaties)}"
assert all(e["status"] in ("goedgekeurd", "afgewezen") for e in curaties)
PYEOF
echo "OK 6: besluiten gelogd (type curatie, append-only)"

# ——— 7: inbox toont alleen nog onbesloten items ———
printf 'vierde inzicht' > "$BREIN/inbox/VOORSTEL-jkl-012-vers.md"
UIT="$(printf '{}' | "$PY" "$REPO/adapter.py" inbox)"
echo "$UIT" | grep -q 'VOORSTEL-jkl-012-vers.md' || FAIL "FAIL 7: nieuwe VOORSTEL mist"
echo "$UIT" | grep -q 'abc-123' && FAIL "FAIL 7: besloten item staat nog open"
echo "$UIT" | grep -q 'def-456' && FAIL "FAIL 7: afgewezen item staat nog open"
echo "OK 7: inbox toont alleen onbesloten items"

rm -rf "$TMP"
echo ""
echo "SLICE 4 E2E: ALLE 7 CRITERIA GROEN"
