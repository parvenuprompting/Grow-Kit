# Testprotocol Fase 2 — Kieming

Datum: 3 september 2026
Status: vastgesteld vóór uitvoering (spec §12, open punt 4)
Plan: `docs/superpowers/plans/2026-09-03-growkit-fase-2.md`

> **IJzeren regel:** dit protocol wordt vastgelegd vóór de eerste test-run. De lat
> wordt niet achteraf bijgesteld naar waar het bewijs toevallig uitkomt. Faalt een
> criterium, dan wordt de faal-uitvoer bewaard en gecommit — nooit stil gefixt.

## Test 1 — "Schone-pleg-plant" (een vreemde plant een tweede-brein)

Situatie: een verse kloon van de repo (niet de werkkopie), geen voorkennis,
Python 3.11+, geen pip-install. Geslaagd = **alle** criteria aantoonbaar waar.

| # | Slaag-criterium (hard, meetbaar) | Hoe gemeten |
|---|---|---|
| 1.1 | Verse kloon van Git plant zonder fout | `git clone` naar tmp-map → `seed.py --profiel tweede-brein --doel <tmp>/plant` → exit-code 0 |
| 1.2 | Alle 8 stappen machine-bewijs: 7× geslaagd, 1× wacht_op_mens | geautomatiseerde controle van logboek.json (lengte 8, statussen conform) |
| 1.3 | De vijf kernmappen + INDEX.md + geboortebewijs.json bestaan in de plant | file_exists-checks in het E2E-script |
| 1.4 | Alle gekopieerde bestanden byte-voor-byte gelijk aan de sjablonen | sha256-vergelijking sjabloon ↔ plant-bestand |
| 1.5 | Geen schrijfactie buiten de doelmap | vóór/na `git status --porcelain` in de kloon: blijft leeg |
| 1.6 | Herstart-gedrag: tweede run op dezelfde doelmap faalt niet onnodig en verontreinigt het logboek niet | idempotente herhaling; logboek bevat na run 2 geen enkele `"status": "gefaald"`-entry; de niet-idempotente stap wordt **dynamisch** uit profiel.json gehaald (eerste `"idempotent": false`) — nooit hardcoded |
| 1.7 | Draait op Python 3.11+ zonder pip-install | run in schone omgeving; script zoekt zelf 3.11+ (zoals e2e_plant.sh) |

## Test 2 — "Vrije beschrijving" (de poort weigert ruis, vraagt scherp)

Situatie: iemand beschrijft in eigen woorden een nieuwe boom, zonder de
verplichte structuur. Geslaagd = **alle** criteria aantoonbaar waar.

| # | Slaag-criterium | Hoe gemeten |
|---|---|---|
| 2.1 | Vrije-beschrijving-invoer zonder einddoel/omgeving/slaag-criterium wordt geweigerd zónder enige uitvoering | unit-test + E2E: geen map aangemaakt, exit ≠ 0 |
| 2.2 | De weigering bevat de drie verplichte velden als vragen + de vragenlijst in het §11.3-JSON-formaat | unit-test op poort-uitvoer-structuur (vaste keys `vraag`, `opties`; laatste optie altijd "iets anders (beschrijf)") |
| 2.3 | Complete invoer (einddoel + omgeving + slaag-criterium) leidt tot een concept-opdracht die wacht op mens-bevestiging — niet direct uitvoert | unit-test: status `wacht_op_mens`, geen commando's uitgevoerd |
| 2.4 | Weigering + concept worden append-only gelogd (ruw + geschuurd + beslissing) | logboek-check: entry heeft `type: "slijper"`, velden `ruw`/`concept`/`beslissing` |
| 2.5 | De vaste weigeringsteksten zijn de droog-maar-nette teksten uit spec §11 | tekstvergelijking tegen vaste constanten in growkit_poort.py |

## Algemene regels

- **Faal = elk criterium dat niet aantoonbaar slaagt.** Geen grijswaarden: een
  plant is bewezen of hij is het niet.
- Bewijs-uitvoer van elke run wordt append-only vastgelegd in
  `docs/superpowers/bewijs/` (fase-2-test1.md, fase-2-test2.md).
- De poort beoordeelt uitsluitend veldaanwezigheid en -vorm — nooit inhoud
  (spec §11-les: interpretatie is interpretatie, geen verificatie).
- Mens-moment (§11.1-stap 3) is niet-onderhandelbaar: een concept-opdracht
  zonder mensbevestiging wordt nooit uitgevoerd.
