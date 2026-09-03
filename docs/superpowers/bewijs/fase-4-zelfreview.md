# Fase 4 — zelfreview (taak 9, afsluiting)

Datum: 3 september 2026. Alles hieronder is op de afsluitdatum uitgevoerd;
evidence is letterlijk, niet samengevat.

## 1. Poort onomzeilbaar (§5, §11.1 hard in fase 4)

- **Codepad:** `grep -c subprocess loop.py` → **0**. De loop spawnt zelf nooit
  een proces; het enige uitvoeringspad loopt via `growkit_motor.voer_uit`
  (plant-modus, hervat-modus, taak-modus) — en elke modus staat achter een
  expliciete mens-bevestiging.
- **Test:** "geen bevestiging → niets uitgevoerd, doelmap bestaat niet"
  (`test_loop_plant.TestPlantModus.test_geen_bevestiging_niets_uitgevoerd`) en
  E2E-4 criterium 5 (poort-weigering, leeg doel → vaste weigeringstekst).
- De inhoud van mens-antwoorden komt nooit in een commando: profielkeuze is
  een nummer uit een lijst; doel is een pad; de poort interpreteert niets.

## 2. Geen agent-dependency (§8)

E2E Test 4 draait met alleen bash + python3 en gepijpte antwoorden —
twee keer uitgevoerd, beide 6/6 (zie `fase-4-test4.md`). Geen import van een
agent-interface, geen LLM-aanroep in de loop.

## 3. Motor-faalcontract onaangetast

`growkit_motor.py` is in fase 4 **niet gewijzigd** (`git log -- kern/growkit_motor.py`
→ laatste wijziging fase 3). De loop voegt een laag toe: reconstructie-beslissingen
filteren het stappen-profiel vóór de bestaande `voer_uit`. Test 4 criterium 3
bewijst het faalcontract-eindgedrag (mens-moment, geen retries).

## 4. Provider-agnostisch

Scan op `anthropic|openai|gpt-|claude-|model=` over `loop.py`, `kern/`, `seed.py`:
**leeg**. De reviewer-rol leeft uitsluitend in reviewconfig (repo-niveau,
.gitignore, fase-3-mechanisme ongewijzigd).

## 5. Regressie (eindstand, letterlijk uitgevoerd)

- Unit-tests: `Ran 110 tests — OK` (fase 1-3: 61 → fase 4: +49)
- E2E 1 (schone-pleg-plant): groen — 7/7
- E2E 2 (poort): groen — 5/5
- E2E 3 (review-laag): groen — 5/5
- E2E 4 (harnas zonder agent + crash-herstart): groen — 6/6 (2× gedraaid)
- E2E plant (basisrooktest): groen

## 6. Beslissingen uit het plan-review (Claude, 3 sept) — alle vijf verwerkt

| Beslissing | Waar bewezen |
|---|---|
| 1. ratificatie in hetzelfde logboek (vervolg-entries) | Test 4a: originele review_ok-entry intact + geratificeerd-entries; reconstructie leest één bron |
| 2. takenlijst alleen JSON | `kern/growkit_taken.py`; geen .md-spiegel gebouwd |
| 3. detectie = aanwezigheid vps-doel.json | `test_omgeving.test_detectie_leest_nooit_de_inhoud`: geheimen kunnen niet lekken — de code opent het bestand niet |
| 4. crash vóór ratificatie → wachten | `test_hervat` (review_ok → overslaan + "geen her-review"); Test 4 criterium 3 |
| 5. corrupt logboek → mens | `test_hervat.TestCorruptLogboek` + E2E-4 criterium 6 (exit 1, geen traceback) |

**Gat-audit (herziening_nodig):** de afbeelding staat in taak 2 (`test_hervat.
test_herziening_nodig_wordt_heraangeboden`), de echte doorloop in taak 5
(`test_loop_ratificatie.test_doorloop_na_afkeuring_reconstructie_behandelt_
als_heraanbieden`), en het herstart-pad in E2E-4 criterium 4b — precies de
volgorde die het plan na de review voorschreef.

## 7. Vondsten tijdens de uitvoering (bewaard in de digest)

1. **Menu-desync/EOF:** E2E-4 vond een traceback bij droge stdin → nette
   weigering + unit-regressie.
2. **Hervatten vóór het geboortebewijs:** crash vóór stap-007 → de loop vraagt
   het profiel aan de mens i.p.v. te raden; onbekende namen worden geweigerd.
3. **Restdraai-correctie (plan-fix in taak 2):** stappen zonder logregel
   beslissen "uitvoeren" — anders loopt een hervatting na een vroege crash vast.
4. **geratificeerd-afbeelding (taak 5):** reconstructie kent de nieuwe status
   van het begin af aan — geen mazen tussen taak 2 en taak 5.
