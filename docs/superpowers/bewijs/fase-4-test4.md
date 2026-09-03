# Fase 4 — Test 4: harnas zonder agent + crash-herstart (bewijs)

Datum: 3 september 2026. Script: `tests/e2e_test4_harnas.sh`. Protocol stond
vóór de run vast in het fase-4-plan (fase-2-les). Uitvoering: twee opeenvolgende
runs, beide 6/6 — het kill-9-moment is poll-gedetermineerd (kill zodra stap-005
in het logboek staat) en reproduceerbaar.

## Wat het bewijst

De loop draait met uitsluitend bash + python3 en gepijpte antwoorden — geen
enkele agent of LLM is betrokken (§8: GrowKit als zelfstandig product).

## Criteria, per protocol

| # | Criterium | Bewijs uit de run |
|---|---|---|
| 1 | Plant zonder agent | `loop.py` gestart met `printf '1\n1\n<doel>\nja\n' |` — alleen python3; stappen 001-005 draaiden en zijn gelogd |
| 2 | Crash halverwege | `kill -9` zodra stap-005 in het logboek stond; logboek bevat stap-001..005 geslaagd en géén stap-006 |
| 3 | Herstart zonder herdraai | herstart (modus 2, profielnaam noemen, "ja"): stap-001 t/m 005 exact één geslaagd-entry; de niet-idempotente stap-005 is nooit herdraaid ("nooit herdraaien"-noot getoond); stap-006/007 draaiden opnieuw als `uitvoeren`; stap-008 → `review_ok_wacht_ratificatie` |
| 4a | Bulk-ratificatie "ja" | modus 4, één bevestiging → stap-008 krijgt vervolg-entry `geratificeerd`; de originele `review_ok`-entry blijft intact (append-only bewezen: 2 entries voor stap-008) |
| 4b | Afkeur + geen rollback + herstart | tweede boom: afkeur "1" → `herziening_nodig` mét doorloop-vermelding; INDEX.md en de rest blijven onaangetast; herstart biedt stap-008 opnieuw aan in de restdraai (gat-review-criterium: gedicht vóór deze E2E) |
| 5 | Poort-weigering in de loop | geen bevestiging → doelmap bestaat niet; leeg doel → vaste weigeringstekst ("helderziende"), exit 1 |
| 6 | Nette paden | corrupt logboek → mens-boodschap, exit 1, geen traceback; EOF tijdens interactie → nette weigering (unit-test) |

## Wat de E2E onderweg aantoonde (en het plan verbeterde)

1. **Menu-desync:** het E2E aanvankelijk één antwoord te weinig gaf — de loop
   leest het modus-menu als eerste; een droge stdin gaf een traceback. Gefixt:
   EOF-afhandeling om de hele interactie (`main` → nette weigering, exit 1)
   + unit-regressie in `test_loop_plant.py`.
2. **Hervatten vóór het geboortebewijs:** de crash kwam vóór stap-007, dus het
   geboortebewijs bestond nog niet. De loop vroeg niet om raden maar om de
   mens: "welk profiel is deze boom?" — met weigering bij onbekende namen.
   Nieuwe unit-tests in `test_loop_hervat.py` (fallback + onbekende naam).

Beide vondsten zijn gedragsverduidelijkingen binnen het plan (geen
plan-afwijkingen): het protocol zelf is ongewijzigd doorgelopen.
