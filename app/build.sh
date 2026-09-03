#!/usr/bin/env bash
# Build-bewijs voor de app (fase 6): xcodegen + xcodebuild, geen simulator.
set -euo pipefail
cd "$(dirname "$0")"

XCODEGEN_PINNED="2.46.0"
ACTUEEL="$(xcodegen --version | awk '{print $NF}')"
[ "$ACTUEEL" = "$XCODEGEN_PINNED" ] || { echo "FAIL: xcodegen $ACTUEEL, verwacht $XCODEGEN_PINNED"; exit 1; }

xcodegen generate
mkdir -p .build
xcodebuild -project GrowKit.xcodeproj -scheme GrowKit \
  -configuration Debug -destination 'platform=macOS' \
  -derivedDataPath .build build CODE_SIGNING_ALLOWED=YES > .build/log.txt 2>&1 \
  || { tail -25 .build/log.txt; exit 1; }

APP=".build/Build/Products/Debug/GrowKit.app"
test -d "$APP" || { echo "FAIL: app-bundle ontbreekt"; exit 1; }
echo "BUILD OK: $APP"
for font in Fraunces.ttf Inter.ttf; do
  test -f "$APP/Contents/Resources/$font" || { echo "FAIL: font $font ontbreekt in de bundle"; exit 1; }
done
echo "FONTS OK: Fraunces + Inter ingebed"
