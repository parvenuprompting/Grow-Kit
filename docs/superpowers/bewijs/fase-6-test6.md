# Fase 6 — Test 6: de app compileert, bedient en bewijst

Datum: 4 september 2026. Script: `tests/e2e_test6_app.sh`. Protocol stond vóór
de run vast in het fase-6-plan (v2, na audit Claude). Uitvoering: meerdere
volle runs, alle criteria groen.

## Wat het bewijst

De macOS-app (`app/`) is een **bedienaar** van het harnas via de JSON-adapter —
de poort, motor en faalcontract blijven de enige bewakers, en de hele keten
is vrij van shell-uitvoering.

## Criteria, per protocol

| # | Criterium | Bewijs uit de run |
|---|---|---|
| 1 | Build + huisstijl | `xcodegen generate && xcodebuild build` (Debug, platform=macOS, team VJ9D2C765N); Fraunces + Inter liggen in de bundle (`Contents/Resources/`) |
| 2a | Concept zonder bevestiging voert niets uit | `plant` zonder `"bevestig"` → `"bevestiging_vereist": true`; de doelmap bestaat daarna **niet** — de poort is in de app-keten niet te omzeilen |
| 2b | Bevestigde plant | 8 stappen met `{id, status, bewijs}`; 7× geslaagd + 1× wacht_op_mens; geboortebewijs volwaardig (geen placeholders) |
| 2c | Registratie + status | plant met `brein: "pad"` → register-entry in het brein met de juiste locatie (realpath-vergelijking); `status` toont `"status": "geboorte"` |
| 2d | Ratificatie | lijst toont `stap-008` (review_ok via cli-testreviewer); bulk-bevestiging → `geratificeerd`-entry append-only |
| 4 | Schermen in de huisstijl | drie PNG's **gerenderd uit de echte SwiftUI-views** (ImageRenderer, 880×620 @2x): `docs/superpowers/bewijs/fase-6-schermen/` → status, plant, ratificatie |
| 5 | Geen shell | bron-scan: geen `subprocess`/`shell` in `adapter.py`, geen `NSAppleScript`/`osascript`/`shell` in `Runner.swift`; de keten is app → `Process` → adapter → kern |
| 6 | Regressie | 206 unit-tests + E2E 1-5 + rooktest, allemaal groen |

De gerenderde schermen: `docs/superpowers/bewijs/fase-6-schermen/status.png`,
`plant.png` en `ratificatie.png` (Fraunces-koppen, monochrome kaarten, badges —
de editorial-monochrome huisstijl uit de mockups).

## Opmerkingen bij de uitvoering

1. **Screenshot-methode:** `screencapture` vraagt Screen-Recording-toestemming
   voor deze shell ("could not create image from display"). Daarom zijn de
   schermen gegenereerd met `ImageRenderer` uit de échte SwiftUI-views —
   deterministisch, toestemming-vrij, en een directer bewijs van de view-code
   dan een venster-foto. Een echte venster-foto kan altijd handmatig zodra de
   toestemming staat.
2. **Realpath-nuance:** `mktemp` geeft `/var/folders/...` terwijl boom-locaties
   via `resolve()` naar `/private/var/folders/...` wijzen — de E2E vergelijkt
   realpaths (les vastgelegd in het script).
3. **Zelf-herkenning:** de shell-scan ving mijn eigen commentaar dat het woord
   "shell" bevatte — de scan werkt; het commentaar is herformuleerd.
4. **ImageRenderer + ScrollView:** ImageRenderer rendert ScrollView-inhoud
   leeg (bekende beperking) — de eerste renders waren identiek wit. De views
   hebben daarom een `metScroll`-parameter: de app scrolt, het render-bewijs
   gebruikt dezelfde inhoud in een vast frame. Les: controleer bewijs-beelden
   op inhoud (md5/pixel-diversiteit), nooit alleen op aanwezigheid.
