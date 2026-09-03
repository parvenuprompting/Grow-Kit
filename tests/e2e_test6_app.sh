#!/usr/bin/env bash
# Test 6 — de app-eindtest (fase 6). Protocol vóór de run vastgesteld in het plan.
# Deel 1 (taak 5): build + fonts + adapter-smoke met de app-standaardinstellingen.
# Deel 2/3 (taak 8): adapter-scenario's + screenshots.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP="$REPO/app"
PY="/opt/homebrew/bin/python3.13"          # de app-standaardinterpreter (Runner.standaardInterpreter)

FAIL() { echo "$1"; exit 1; }
command -v xcodegen >/dev/null 2>&1 || FAIL "FAIL: xcodegen ontbreekt"
"$PY" --version >/dev/null 2>&1 || FAIL "FAIL: $PY niet beschikbaar — de app-standaardinterpreter werkt niet"

# ——— Criterium 1: de app compileert, fonts ingebed ———
BUILD_UIT="$(bash "$APP/build.sh")" || { echo "$BUILD_UIT" | tail -5; FAIL "FAIL 1: build faalde"; }
echo "$BUILD_UIT" | grep -q "BUILD OK" || FAIL "FAIL 1: geen BUILD OK in de build-uitvoer"
APPBUNDLE="$APP/.build/Build/Products/Debug/GrowKit.app"
test -d "$APPBUNDLE" || FAIL "FAIL 1: app-bundle ontbreekt"
test -f "$APPBUNDLE/Contents/Resources/Fraunces.ttf" || FAIL "FAIL 1: Fraunces ontbreekt"
test -f "$APPBUNDLE/Contents/Resources/Inter.ttf" || FAIL "FAIL 1: Inter ontbreekt"
echo "OK 1: app compileert — Fraunces + Inter ingebed"

# ——— Criterium 2: adapter-smoke precies zoals de app hem aanroept ———
export GROWKIT_OERWOUD_STAAT="$(mktemp -d)/growkit-home/oerwoud.json"
UIT="$(printf '{}' | "$PY" "$REPO/adapter.py" profielen)"
echo "$UIT" | "$PY" -c "
import json, sys
uit = json.loads(sys.stdin.read())
assert uit['ok'], 'adapter-smoke: ok ontbreekt'
namen = [p['naam'] for p in uit['data']['profielen']]
assert 'tweede-brein' in namen, f'tweede-brein ontbreekt: {namen}'
" || FAIL "FAIL 2: adapter-smoke faalde"
echo "OK 2: adapter bereikbaar met de app-interpreter — profielen als JSON"

echo "TEST 6 DEEL 1 OK: build + fonts + adapter-smoke"
