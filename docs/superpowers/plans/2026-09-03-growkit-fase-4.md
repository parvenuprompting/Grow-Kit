# GrowKit Fase 4 — Implementatieplan: Eigen harnas (loop.py)

Datum: 3 september 2026
Status: v2 — beslissingen vastgelegd na review (Claude, 3 sept 2026); herziening_nodig-gat gedicht (zie taak 2/5/8) — klaar voor uitvoering
Spec: `docs/superpowers/specs/2026-09-03-growkit-design.md` (v10, incl. §13-drift-guard)
Fase 1: af (`cbaa26e`). Fase 2: af (Test 1: 7/7, Test 2: 5/5). Fase 3: af (taken 1-8, Test 3: 5/5; afsluiting `a52d4ca`) — 61 unit-tests + 4 E2E's groen.

**Goal:** Fase 4 bewijst dat GrowKit een zelfstandig product is zonder agent-dependency (§8): een dunne, provider-agnostische orchestratieloop (`loop.py`, paar honderd regels, stdlib, geen framework) die de poort, leesroute, mijlpaal en ratificatie **hard afdwingt** in plaats van aan een geleende agent te delegeren. Twee fase-3-vereisten worden hier ingelost: (a) state-reconstructie — herstart leest het logboek, geen blind herdraaien; (c) omgevingsdetectie als gelabelde bron (§11.3-3b). Kernbegrenzing blijft: machine-bewijs eerste keus, de mens ratificeert, geen auto-rollback.

**Architecture:** Nieuwe module `kern/growkit_hervat.py` (pure functies: logboek → herstart-beslissingen) en `loop.py` (repo-root, dun: formulieren, bevestiging, moduskeuze, uitvoering via de bestaande motor). De motor (`growkit_motor.py`) blijft ongewijzigd in zijn faalcontract — loop.py bouwt een restdraai-profiel en geeft dat aan de bestaande `voer_uit`. De poort blijft de enige invoerbescherming; loop.py tekent het §11.3-formulier zelf (terminal-UI) maar interpreteert geen inhoud.

**Tech Stack:** Python 3.11+ (stdlib only), unittest, bash voor E2E. Geen LLM-aanroepen in loop.py: de reviewer-rol blijft uitsluitend via reviewconfig in de motor (fase-3-pad).

## Global Constraints

- Zelfde basis als fase 1-3: Nederlands, geen pip-dependencies, gecodeerd bewijs, TDD (eerst falende check), commit+push per taak.
- **Geen agent-dependency:** loop.py draait met alleen python3 + terminal-invoer. E2E Test 4 bewijst dit met gepijpte antwoorden, geen enkele agent.
- **Poort onomzeilbaar (§5, §11.1 hard in fase 4):** de loop voert niets uit dat niet de mensbevestiging heeft gehad. Er bestaat geen codepad van loop.py naar executie zonder bevestigde scope — dit is testbaar en wordt getest.
- **De mens blijft curator:** ratificatie in bulk is een mens-moment; afkeuring → `herziening_nodig`, append-only gelogd, géén auto-rollback (fase-3-semantiek, ongewijzigd).
- **Injectie-afweer:** output van een stap wordt nooit als commando geïnterpreteerd (motor: `capture_output`, gecodeerde bewijs-checks); loop.py accepteert geen vrije commando-invoer. Echte sandboxing blijft §14-buiten-scope, maar deze grens is in fase 4 testbaar.
- Corrupt of half-geschreven logboek → mens roepen, nooit crashen of auto-repareren.

---

## Task 1: Takenlijst-schema — taken bestaan alleen mét bewijs (§7)

**Files:** Create `kern/growkit_taken.py`; Test: `tests/test_taken.py`

**Interface:** `laad_taken(pad: Path) -> list[dict]`, `valideer_taak(taak: dict) -> list[str]` (hergebruik poort-taak-regel: geen `bewijs` met `type` → ongeldig), `log_taakgebeurtenis(pad: Path, taak_id: str, status: str, bewijs: str)` — append-only in de plant.

- [ ] **Step 1: Falende tests** — taak zonder bewijs → ongeldig (weigeringstekst poort); geldige taak → geaccepteerd; elke gebeurtenis append-only (bestaande entries blijven); afwezig bestand → lege lijst.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: takenlijst-schema — taken bestaan alleen mét bewijs (§7)`

## Task 2: State-reconstructie — herstart uit het logboek (§7, §11.4; audit-B)

**Files:** Create `kern/growkit_hervat.py`; Test: `tests/test_hervat.py`

**Interface:** `reconstructie(logboek: Path, profiel: dict) -> dict` — per stap een beslissing: `"overslaan"` (geslaagd of `review_ok_wacht_ratificatie`), `"heraanbieden"` (`wacht_op_mens`/`gefaald`/`herziening_nodig` — na mens-fix; herziening_nodig ontstaat pas in taak 5, maar de afbeelding staat hier vanaf de geboorte van de functie — geen mazen), en het herstartpunt: de laatste bevestigde mijlpaal (§11.4). Regels:
1. Een **niet-idempotent geslaagde** stap mag bij hervatting **nooit** opnieuw draaien — ook niet als later gestopt werd vóór ratificatie.
2. `review_ok_wacht_ratificatie` wordt niet opnieuw uitgevoerd en niet opnieuw gereviewd — hij wacht op de bulk-ratificatie (bevestigd in beslissing 4).
3. Corrupt JSON in het logboek → expliciete foutstatus `corrupt_logboek` (mens roepen), geen crash.

- [ ] **Step 1: Falende tests** — gesynthetiseerde logboeken: geslaagd-idempotent → overslaan; geslaagd-niet-idempotent → overslaan mét noot "nooit herdraaien"; gefaald → heraanbieden; review_ok → wachten op ratificatie; **herziening_nodig → heraanbieden** (status-string kan gesynthetiseerd worden vóór taak 5 bestaat — de afbeelding wordt hier getest, de echte doorloop in taak 5); geen mijlpaal-bevestiging → herstartpunt = start; corrupt JSON → `corrupt_logboek`, geen exceptie naar buiten.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: state-reconstructie — herstart uit het logboek, niet-idempotent nooit herdraaid (§7)`

## Task 3: loop.py plant-modus — formulier + harde bevestigingsdrempel (§5, §11.1)

**Files:** Create `loop.py`; Test: `tests/test_loop_plant.py`

**Gedrag:** loop.py start met moduskeuze (planten / hervatten / taak / ratificatie / status). Plant-modus: tekent het §11.3-formulier in de terminal (opties 1-n + "iets anders", vragenlijst uit de poort — geen dubbele logica), voegt antwoorden samenvoegend in een concept (poort `beoordeel_invoer`), toont het concept en vraagt één bevestiging; **pas na "ja"** wordt de motor gestart (mijlpaal-drempel uit fase 3 werkt door). Geen bevestiging → niets uitgevoerd, logboek onaangeroerd. Leesroute via `growkit_leesroute.fase_content` — niets buiten de route zichtbaar.

- [ ] **Step 1: Falende tests** (input-injectie via parameter, patroon `test_mijlpaal`) — formulier toont opties met nummers; antwoorden → concept exact via de poort; geen bevestiging → doel-logboek blijft `[]` en er is niets geplant; bevestiging → motor draait (profiel-stub); inhoudsinterpretatie bestaat niet: loop.py heeft geen codepad dat tekst naar een commando schrijft.
- [ ] **Step 2-4: falen → bouwen → groen (alle fase 1-3 tests onaangetast). Step 5: Commit** — `feat: loop.py plant-modus — formulier + harde bevestigingsdrempel (§11.1)`

## Task 4: Hervat-modus — restdraai-profiel, motor ongewijzigd (audit-B)

**Files:** Modify `loop.py`; Test: `tests/test_loop_hervat.py`

**Gedrag:** hervatten = `reconstructie()` (taak 2) → loop.py bouwt een restdraai-profiel (alleen stappen met beslissing `heraanbieden`, plus de nooit-herdraai-beslissing als harde filter) → bestaande `voer_uit`. Het herstartpunt (laatste bevestigde mijlpaal) wordt getoond vóór de restdraai. Geen hervatting nodig (alles geslaagd/geratificeerd) → nette mededeling, niets draait.

- [ ] **Step 1: Falende tests** — logboek met stap-001 geslaagd (idempotent), stap-002 niet-idempotent geslaagd, stap-003 gefaald: restdraai bevat alléén stap-003; herstartpunt correct getoond; geen hervatting nodig → geen motor-aanroep; corrupt logboek → mens-boodschap, geen crash.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: loop.py hervat-modus — restdraai-profiel, motor ongewijzigd (§7)`

## Task 5: Ratificatie in bulk — één moment, append-only (fase-3-semantiek afmaken, §9)

**Files:** Modify `loop.py`; Test: `tests/test_loop_ratificatie.py`

**Gedrag:** na een run toont loop.py alle stappen met status `review_ok_wacht_ratificatie` als één lijst en vraagt **één** bevestiging: "ja" → elke stap krijgt append-only een vervolg-entry status `geratificeerd` (originele entry blijft); afkeuring van één stap → status `herziening_nodig` + doorloop-vermelding (welke latere stappen erop bouwen — staat al in het logboek), géén auto-rollback; geen `review_ok`-stappen → geen ratificatie-moment.

- [ ] **Step 1: Falende tests** — twee review_ok-stappen: één "ja" → twee `geratificeerd`-entries, originele entries intact (append-only); afkeur van stap 1 → `herziening_nodig` voor die stap, stap 2 blijft `wacht_ratificatie`, bestanden onaangetast; **doorloop na afkeuring: `reconstructie()` behandelt de `herziening_nodig`-stap als `heraanbieden`** (gat-review 3 sept: taak-2's oorspronkelijke testset dekte dit scenario niet — hier bewezen gesloten); nul review_ok-stappen → geen vraag gesteld (aanroep-teller = 0).
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: ratificatie in bulk — één bevestiging, append-only, geen rollback (§9)`

## Task 6: Taak-uitvoering via de loop — poort eerst, motor uit (§7)

**Files:** Modify `loop.py`; Test: `tests/test_loop_taak.py`

**Gedrag:** taak-modus: kies taak uit de takenlijst (taak 1) → door de poort (`taak`-type) → uitvoer via de motor als éénstaps-profiel → gebeurtenis append-only gelogd (voorgesteld → geslaagd/gefaald/wacht_op_mens). Een taak zonder bewijs bestaat niet (poort-weigering, niets draait). Bij faal: mens; geen retries zonder mens.

- [ ] **Step 1: Falende tests** — geldige taak → uitgevoerd en gelogd; taak zonder bewijs → geweigerd, niets uitgevoerd; faal-alternatief wordt precies één keer geprobeerd (motor-contract, bewijs via logboek).
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: taak-uitvoering via loop — poort eerst, motor uit (§7)`

## Task 7: Omgevingsdetectie als gelabelde bron (§11.3-3b; audit-C)

**Files:** Modify `loop.py`; Test: `tests/test_omgeving.py`

**Gedrag:** detectie-functie `detecteer_omgeving(profiel_pad: Path) -> dict`: bestaat er een `vps-doel.json` in het profiel → de omgeving-vraag krijgt de optie "een VPS" voorinvuld als **gelabelde standaardwaarde** (hergebruik fase-3-mechanisme: `standaardwaarde: true` + bronvermelding "omgevingsdetectie"); anders de bekende lokaal-standaard. Alleen veldaanwezigheid wordt gelezen — de inhoud van vps-doel.json (host/gebruiker/poort) wordt niet geopend. De poort zelf blijft ongewijzigd.

- [ ] **Step 1: Falende tests** — profiel mét vps-doel.json → standaardoptie VPS, gelabeld + bron "omgevingsdetectie"; zonder → lokaal-standaard; detectie leest géén inhoud (test met een vps-doel.json waarvan de waarden bewust nooit in het concept mogen verschijnen); poort-gedrag onveranderd (bestaande `test_slijper`-tests groen zonder aanpassing).
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: omgevingsdetectie als gelabelde bron — aanwezigheid, nooit inhoud (§11.3-3b)`

## Task 8: E2E Test 4 — het harnas zonder agent, mét crash-herstart

**Files:** Create `tests/e2e_test4_harnas.sh`; bewijs in `docs/superpowers/bewijs/fase-4-test4.md`

**Protocol — vóór de run vastgesteld (fase-2-les):**
1. `loop.py` plant een boom volledig met uitsluitend python3 + gepijpte antwoorden — géén agent betrokken (bewijst §8-zelfstandigheid).
2. Plant wordt halverwege gedood (`kill -9` na eerste geslaagde stap; bewijs via logboek).
3. Herstart: stap-001 wordt **niet** opnieuw uitgevoerd (logboek toont exact één geslaagd-entry per stap + hervat-entry); de niet-idempotent geslaagde stap wordt nooit herdraaid.
4. Bulk-ratificatie: `review_ok`-stappen → `geratificeerd`; afkeur-variant → `herziening_nodig`, bestanden onaangetast (geen rollback); **herstart ná afkeuring: de `herziening_nodig`-stap wordt als `heraanbieden` behandeld (gat vóór deze taak gedicht — taak 5 doorloop-test).**
5. Poort-weigering in de loop (geen bevestiging) → niets uitgevoerd, doel-logboek `[]`.
6. Exit-codes netjes; geen traceback naar de gebruiker bij verwachte paden (corrupt logboek → mens-boodschap).

- [ ] **Step 1: Script schrijven. Step 2: Run — groen; faal-uitvoer bewaren bij falen. Step 3: Bewijs-document. Step 4: Commit** — `test: Test 4 — harnas zonder agent bewezen`

## Task 9: Afsluiting

- [ ] **Step 1: Zelfreview** — poort onomzeilbaar bewezen (codepad + test); geen agent-dependency (Test 4); motor-faalcontract onaangetast; provider-scan; regressie: alle fase 1-3 tests + E2E 1-4 groen. Bewijs: `docs/superpowers/bewijs/fase-4-zelfreview.md`.
- [ ] **Step 2: Mijlpaal-digest als VOORSTEL** naar Agent-Brain inbox (append-only).
- [ ] **Step 3: Commit** — `docs: fase 4 af — harnas bewezen`

---

## Vastgelegde beslissingen (3 sept 2026, review Claude — niet meer open)

1. **Ratificatie-opslag:** hetzelfde doel-logboek (append-only vervolg-entries). Rationale: één bron van waarheid weegt zwaarder dan de scheiding van een apart bestand; een los ratificatiebestand is precies het soort sync-risico dat `reconstructie()` door alles uit één append-only bron te lezen probeert te elimineren.
2. **Takenlijst-bron:** alleen JSON; `takenlijst.md` verhuist naar fase 5. Een mens-leesbare view is een presentatielaag, geen kern-mechanisme — bouw hem pas als er een concrete lezer is.
3. **Detectie-signaal:** aanwezigheid van `vps-doel.json`. Lezen van `~/.ssh/config` is het secrets-gebied dat de global constraints vermijden; aanwezigheid-alleen is bovendien testbaar tot "de inhoud kan niet in een concept verschijnen, simpelweg omdat de code hem nooit opent".
4. **Crash vóór ratificatie:** wachten, geen her-review. Her-review zou non-deterministisch zijn (zelfde stap, tweede aanroep, ander oordeel) en het logboek een oordeel laten tonen dat niet meer matcht met wat er werkelijk gebeurde. Bevestigt taak-2 regel 2 expliciet.
5. **Corrupt logboek:** mens roepen met `corrupt_logboek`-status, nooit auto-reparatie. Auto-reparatie is per definitie een gok naar wat er "eigenlijk" had moeten staan — interpretatie is voor de mens.

**Gevonden gat (gesloten in dit document):** `herziening_nodig` ontbrak in de besliscategorieën van `reconstructie()` (taak 2 introduceerde overslaan/heraanbieden vóórdat taak 5 de status introduceert). Oplossing, in dit plan verankerd: de afbeelding `herziening_nodig → heraanbieden` staat vanaf taak 2 in de functie-definitie, wordt daar getest op een gesynthetiseerd logboek, als echte doorloop getest in taak 5, en als herstart-pad afgedekt in taak 8, criterium 4 — vóórdat de E2E draait.

## Zelfreview-checklist (voor de executor)

1. **Zelfstandigheid:** Test 4 draait met alleen python3; geen import van een agent-interface; geen LLM-aanroep in loop.py (provider-scan zoals fase 3).
2. **Poort onomzeilbaar:** geen codepad van loop.py naar `subprocess` anders dan via motor + bevestigde scope; een test bewijst de weigering zonder bevestiging.
3. **Hervatting veilig:** niet-idempotent geslaagde stappen worden door geen enkel pad herdraaid; herstartpunt = laatste bevestigde mijlpaal.
4. **Regressie:** alle fase 1-3 unit-tests + E2E 1-3 blijven na elke taak groen — de loop voegt een laag toe, wijzigt niets bestaands behalve de aangegeven aansluitpunten.
5. **Bekende valkuilen:** (a) `input()` in tests → injectie via parameter (patroon `test_mijlpaal`), nooit echte stdin in unit-tests; (b) ratificatie-entries zijn vervolg-entries — de originele `review_ok_wacht_ratificatie`-entry verdwijnt nooit; (c) detectie leest uitsluitend bestandenaanwezigheid, nooit de inhoud van vps-doel.json; (d) geen drempel/pad hardcoded in tests; (e) E2E met `kill -9` → altijd de exit-status bewijzen uit het logboek, niet uit de shell-uitvoer alleen.
