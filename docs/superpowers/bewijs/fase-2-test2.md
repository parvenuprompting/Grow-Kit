# Bewijs — Fase 2, Test 2: Vrije beschrijving (de poort)

Datum: 3 september 2026
Protocol: `docs/superpowers/testprotocol-fase-2.md`
Script: `tests/e2e_test2_poort.sh`
Uitvoerend: Mac Hermes (automatisch, geen mens tussen de stappen)

## Resultaat: 5/5 criteria geslaagd

```
OK 2.1a: vage invoer geweigerd (exit 1), geen map aangemaakt
OK 2.2: weigering + 3 vragen in §11.3-JSON-vorm (elk met 'iets anders')
OK 2.4: append-only logging — ruw + concept + beslissing ('geweigerd') aanwezig
OK 2.3: complete invoer → concept wacht op mens; niets uitgevoerd, geen map
OK 2.5: weigeringsteksten zijn vaste constanten conform spec §11

TEST 2 OK: poort weigert ruis en vraagt scherp — 5/5 criteria geslaagd
```

## Testinvoer

- **Vage invoer (2.1):** `maak me iets om m'n notities te ordenen of zo`
  → geweigerd met de vaste bui-tekst uit §11, exit-code 1, nul mappen aangemaakt.
- **Complete invoer (2.3):** einddoel + omgeving + slaag-criterium expliciet
  → concept-opdracht met `status: wacht_op_mens` en de bevestigingsvraag
  "Klopt dit? (ja / pas aan)"; géén plant-map aangemaakt, niets uitgevoerd.

## Methodenotities

- De vragenlijst (2.2) is hard gecheckt op het §11.3-JSON-formaat: keys
  `vraag`/`opties`, en de laatste optie is altijd "iets anders (beschrijf)".
- De slijper-logging (2.4) is aangesloten vóór de run: elke beurt schrijft
  append-only `ruw` + `concept` + `beslissing` + `tijdstip` naar
  `groei/slijper-logboek.json` (runtime-data, buiten git via .gitignore).
- De weigeringsteksten (2.5) zijn importeerbare constanten in growkit_poort.py
  en worden in de test vergeleken met de spec-§11-formulering — geen
  gegenereerde zinnen.
