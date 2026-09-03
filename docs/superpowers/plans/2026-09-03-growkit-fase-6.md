# GrowKit Fase 6 — Implementatieplan: De macOS-UI (het huis)

Datum: 3 september 2026
Status: v2 — audit (Claude, 3 sept) verwerkt: afkeur-reden in het schema, mijlpaal = fase 6.1 met nette weigering, brein-auto-vraag in het protocol — klaar voor uitvoering
Spec: `docs/superpowers/specs/2026-09-03-growkit-design.md` (v10) + beslissingen gebruiker 3 sept (JSON-adapter · native SwiftUI · v1 = status + planten + ratificatie)
Fase 1-5: af en bewezen (173 unit-tests, 6 E2E's; laatste commit `7dde550`).

**Goal:** Een native macOS-app (SwiftUI via XcodeGen, in de editorial-monochrome huisstijl: Fraunces + Inter, papier/inkt) die het harnas bedient **als een bedienaar, nooit als een machthebber** (§5-geest). De app praat via een nieuwe machine-leesbare **JSON-adapter** met de kern — dezelfde poort, motor en faalcontract blijven de enige bewakers. Mens-bevestiging gebeurt in de app met knoppen, maar de adapter afdwingt dat niets uitgevoerd wordt zonder expliciete bevestiging: de UI is de §11.3-formulier-ervaring die het harnas al had, nu met klikbare oppervlakken.

**Architecture:** Twee lagen, bewust gescheiden:
1. **`adapter.py` (repo-root, Python stdlib)** — machine-leesbare CLI over `kern/`: elk subcommando leest JSON via stdin, schrijft precies één JSON-document naar stdout (`{"ok": bool, "data": ..., "vragen": [...], "fout": ...}`), exit-codes 0/1/2 conform het harnas. Confirmaties zijn expliciete vlaggen (`"bevestig": true`); zonder bevestiging retourneert een actie het *concept* (poort-output) en voert niets uit. De adapter is stateless en bouwt uitsluitend op de bestaande functies van `kern/` — motor, poort, faalcontract onaangetast.
2. **`app/` (XcodeGen + SwiftUI, macOS 14+)** — `project.yml` genereert `GrowKit.xcodeproj` (gitignored); SwiftUI-views in huisstijl; een `Runner`-model roept de adapter via `Process` (geen shell) aan, async, met een harde time-out. Fonts Fraunces/Inter (SIL OFL) ingebed; AppIcon uit de kiemplant-SVG van de mockups.

**Tech Stack:** Python 3.11+ stdlib (adapter); Swift 5.10/SwiftUI, XcodeGen, xcodebuild voor bewijs; geen derde-partij-packages in app of adapter.

## Global Constraints

- Zelfde basis als fase 1-5: Nederlands, gecodeerd bewijs, TDD (eerst falende check), commit+push per taak.
- **De adapter is een bedienaar:** hij mag uitsluitend de bestaande kern-functies aanroepen; nergens een tweede implementatie van poort- of motor-logica. De poort blijft de enige invoerbescherming — de adapter accepteert nooit vrije tekst als commando.
- **Geen shell in de hele keten:** adapter via subprocess zonder shell; app→adapter via `Process` zonder shell. Stap-output wordt nooit als commando geïnterpreteerd.
- **Confirmatie is expliciet en stateless:** zonder `"bevestig": true` voert een actie niets uit en retourneert het concept; er is geen verborgen sessie-staat tussen aanroepen.
- Huisstijl komt uit de mockups: papier `#FFFFFF`, inkt `#000000`, zacht `#555555`, gedempt `#888888`, lijn `rgba(0,0,0,0.12)`; Fraunces (display) + Inter (tekst); editorial-monochrome, geen kleuraccenten.
- Signing: Apple Development Team **VJ9D2C765N**; v1 is een lokale dev-build (geen notarisatie nog).

---

## Task 1: Adapter-grondslag — het JSON-protocol + status-commando

**Files:** Create `adapter.py`; Test: `tests/test_adapter.py`

**Interface:** `python3 adapter.py <commando>` — JSON in via stdin, één JSON-document uit op stdout. Contract: (a) stdout is uitsluitend geldig JSON, mens-leesbare tekst gaat naar stderr; (b) fouten zijn `{"ok": false, "fout": "<NL-tekst>"}` met exit 1 — nooit een traceback; (c) onbekend commando → nette fout met de commando-lijst. Commando's in taak 1: `status` (doel-pad → identiteit, register-status, tellers, laatste mijlpaal/faal — hergebruik `toon_status`-logica als pure functie), `profielen` (bewezen profielen + brein-opties §11.2).

- [ ] **Step 1: Falende tests** — status retourneert identiteit/register/tellers als JSON; afwezig geboortebewijs → ok met `data: null` + melding; corrupt logboek → `{"ok": false}` + exit 1, géén traceback; stdout-bevat-alleen-JSON-bewijs (parse-check); onbekend commando → nette fout.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: adapter-grondslag — JSON-protocol + status (fase 6)`

## Task 2: Adapter-plant — concept eerst, uitvoering mét bevestiging

**Files:** Modify `adapter.py`; Test: `tests/test_adapter_plant.py`

**Gedrag:** `plant` leest `{profiel, doel, brein?: "auto"|"pad"|"geen", bevestig?: bool}`. Zonder bevestiging: retourneert het poort-concept (kiemkeuze-check) — **niets uitgevoerd**. Met bevestiging: motor-run; het resultaat bevat per stap `{id, status, bewijs}` (machine-leesbaar uit het logboek) + geboortevolmaking + registratie. Faal → `{"ok": false, "stappen": [...]}` + exit 2.

**Brein-semantiek (audit-punt 3):** `"auto"` werkt direct wanneer het brein bekend is in de oerwoud-staat; is het brein **onbekend**, dan kan de stateless adapter niets vragen — hij retourneert een **vragen-respons** (`vragen: [{vraag: "waar groeit je brein", opties: ["deze boom wordt het brein", "pad opgeven", "niet registreren"]}]`) en voert en registreert **niets**; de app doet een tweede aanroep met `brein` expliciet gevuld. `"geen"` registreert nooit. **Mijlpaal (beslissing 7):** raakt het profiel de mijlpaal-drempel (§11.4), dan weigert de adapter netjes ("dit profiel raakt de mijlpaal-drempel — plant via loop.py; adapter-ondersteuning komt in fase 6.1") — nooit een stilzwijgende midden-staat.

- [ ] **Step 1: Falende tests** — concept-modus voert niets uit (doelmap bestaat niet); bevestigde plant retourneert 8 stap-resultaten + geboorte-entry; faal-contract → exit 2 met stappen-overzicht; brein "geen" → geen registratie; "auto" met bekend brein → staat onaangetast, registratie in dat brein; **"auto" met onbekend brein → vragen-respons, niets uitgevoerd, niets geregistreerd**; onbekend profiel → nette poort-fout; **profiel dat de mijlpaal-drempel raakt → nette weigering (beslissing 7), ook mét bevestiging**.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: adapter-plant — concept eerst, uitvoering mét bevestiging (fase 6)`

## Task 3: Adapter-ratificatie — lijst, goedkeuring, afkeur

**Files:** Modify `adapter.py`; Test: `tests/test_adapter_ratificatie.py`

**Gedrag:** `ratificeer` leest `{doel, bevestig?: bool, afkeur?: [{stap_id, reden}]}` (audit-punt 1: de reden die de UI verzamelt, komt expliciet in het logboek). Zonder bevestiging: de lijst `review_ok_wacht_ratificatie`-stappen. Met bevestiging zonder afkeur → alles `geratificeerd`; met afkeur-entries → die stappen `herziening_nodig` **mét de reden als bewijs-tekst** in de vervolg-entry, de rest onaangetast (fase-3-semantiek, hergebruik `ratificeer`-logica als pure functie). Afkeur zonder reden → schema-fout (nette weigering).

- [ ] **Step 1: Falende tests** — lijst-modus wijzigt niets; bevestiging → geratificeerd-entries append-only; afkeur → herziening_nodig **mét de doorgegeven reden in de logboek-entry**; afkeur zonder reden → nette schema-weigering; geen wachtende stappen → ok met lege lijst.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: adapter-ratificatie — lijst, goedkeuring, afkeur mét reden (fase 6)`

## Task 4: Beveiligings-contract — de adapter is een bedienaar

**Files:** Modify `adapter.py`; Test: `tests/test_adapter_contract.py`

**Gedrag:** harde contract-tests: (a) de adapter-spawning gebruikt nergens `shell=True` (scan + gedragsassertie); (b) vrije tekst in verplichte velden kan nooit als commando landen (poort-weigering bewezen via de adapter); (c) stdout bevat nooit secrets/reviewconfig-inhoud; (d) stateless: twee identieke concept-aanroepen geven identieke output, geen verborgen sessie; (e) alle kern-aanroepen lopen via `kern/` — scan bewijst dat er géén poort/motor-logica is gedupliceerd.

- [ ] **Step 1: Falende tests** per regel (a)-(e). **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: adapter-contract — bedienaar, niet machthebber (fase 6)`

## Task 5: XcodeGen-project + huisstijl-skelet

**Files:** Create `app/project.yml`, `app/Sources/…` (App, Thema, Runner), `app/Fonts/`, `app/Assets.xcassets`; Test: build-script `app/build.sh` + E2E `tests/e2e_test6_app.sh` (deel 1)

**Gedang:** `xcodegen generate` → `xcodebuild build` (scheme GrowKit, team VJ9D2C765N) = het bewijs dat de app compileert. Thema volgens huisstijl (`Thema.swift`: kleuren + Fraunces/Inter als ingebedde fonts); `Runner.swift`: async `Process`-aanroepen van de adapter met time-out, stdin-JSON, stdout-parse naar `AdapterResult`; minimale `ContentView` met het hoofdmenu (vijf modi, v1-modi actief, v2-modi gedimd).

- [ ] **Step 1: project.yml + thema + runner + skeleton. Step 2: build.sh → groen. Step 3: E2E-deel-1 (build + adapter smoke via de app-tests). Step 4: Commit** — `feat: macOS-app skelet — XcodeGen, huisstijl, adapter-runner (fase 6)`

## Task 6: Status-scherm — het oerwoud zichtbaar

**Files:** Modify `app/Sources/…`; E2E-deel-2

**Gedrag:** StatusView: identiteitskaart (boom-id, profiel, gepland), register-status, VOORSTEL-tellers, logboek-timeline (append-only weergave: newest last, geen filters die iets verbergen), brein-paneel (pad + onbereikbaar-toestand). Doelkeuze via een boom-kiezer (recente doelen; pad-invoer). Adapter-aanroep `status`.

- [ ] **Step 1: Views + binding op Runner. Step 2: build groen. Step 3: Commit** — `feat: status-scherm — oerwoud zichtbaar in de app (fase 6)`

## Task 7: Plant- en ratificatie-schermen — klikken met poort-discipline

**Files:** Modify `app/Sources/…`; E2E-deel-3

**Gedrag:** PlantView: profielkeuze (kaarten uit `profielen` + "uit je brein"-opties gemarkeerd), doel-veld, omgeving-hint; de knop "Bekijk concept" haalt het poort-concept op en toont het als geslepen kaart (met gelabelde standaardwaarden); pas na expliciete "Plant" (bevestiging) loopt de motor — stappen verschijnen live met hun bewijs-status; faal → rood-inkt-toestand + "roep de mens". RatificeerView: lijst wachtende stappen, per stap goedkeuren/afkeuren, één bulk-knop; afkeur vraagt om een reden (komt in het logboek).

- [ ] **Step 1: Views. Step 2: build groen. Step 3: Commit** — `feat: plant- en ratificatie-schermen — klikken met poort-discipline (fase 6)`

## Task 8: E2E Test 6 — de app-eindtest

**Files:** Extend `tests/e2e_test6_app.sh`; bewijs in `docs/superpowers/bewijs/fase-6-test6.md`

**Protocol — vóór de run vastgesteld:**
1. `xcodegen generate && xcodebuild build` — de app compileert zonder waarschuwingen in de release-config.
2. Adapter-scenario's end-to-end via subprocess (status/profielen/plant-concept/plant-bevestigd/ratificeer) op een schone plek, geïsoleerde oerwoud-staat.
3. Poort-contract in de app-keten: concept zonder bevestiging voert niets uit (doelmap blijft afwezig — gecontroleerd).
4. UI-screenshots (StatusView, PlantView-concept, PlantView-live, RatificeerView) in het bewijs-document — de huisstijl is zichtbaar (Fraunces-kop, monochrome kaarten).
5. Geen shell in de keten: scan + gedragsbewijs; geen secrets in stdout.
6. Alle fase 1-5 tests + E2E 1-5 blijven groen.

- [ ] **Step 1: Script. Step 2: Run — groen. Step 3: Bewijs-document. Step 4: Commit** — `test: Test 6 — de app compileert, bedient en bewijst (fase 6)`

## Task 9: Afsluiting

- [ ] **Step 1: Zelfreview** — bedienaar-contract bewezen; poort/motor onaangetast; huisstijl check; regressie compleet. Bewijs: `docs/superpowers/bewijs/fase-6-zelfreview.md`.
- [ ] **Step 2: Mijlpaal-digest als VOORSTEL** naar Agent-Brain inbox.
- [ ] **Step 3: Commit** — `docs: fase 6 af — de app bewezen`

---

## Vastgelegde beslissingen (3 sept 2026, review Claude — niet meer open)

1. **Adapter-locatie:** `adapter.py` in de repo-root, naast `seed.py`/`loop.py` — het is een entrypoint met hetzelfde staatsburgerschap.
2. **Confirm-semantiek:** stateless één-call-met-vlag (`bevestig: true`) — geen sessie-staat, §11.3 "één ronde, één klik". Er is geen concept-id-terugkoppeling; het concept is de return-waarde van de vlag-loze aanroep.
3. **Registratie/doorstroom in de adapter-plant:** automatisch (machine-feit, fase-5-beslissing); de app toont het als gebeurtenis.
4. **macOS-minimum:** 14 Sonoma.
5. **Font-licentie:** Fraunces/Inter embedden (beide SIL OFL).
6. **App in de GrowKit-repo:** `app/` als map in deze repo — één bron van waarheid, contracttests lopen samen groen.
7. **Mijlpaal in de adapter = fase 6.1 (audit-punt 2):** het stateless één-call-model kan geen midden-run-bevestiging dragen; v1 weigert profielen die de mijlpaal-drempel (§11.4) raken met een nette, testbare weigering — ook mét bevestiging. Voor het huidige tweede-brein (8 stappen) is dit onbereikbaar, dus niets verliest vandaag functionaliteit; wanneer het eerste ≥10-stappen-profiel komt, levert fase 6.1 het twee-staps-protocol (plant-pauze + `bevestig_mijlpaal`).
8. **Afkeur-schema (audit-punt 1):** `afkeur?: [{stap_id, reden}]` — de reden die de UI verzamelt, landt expliciet in de logboek-entry; afkeur zonder reden is een schema-fout.
9. **Brein-auto (audit-punt 3):** `"auto"` met onbekend brein → vragen-respons, niets uitgevoerd of geregistreerd; de app doet een tweede aanroep met expliciete keuze. Getest in taak 2.

**Vooraf bevestigd:** de twee fase-5-gaten (migratie oude bomen; `brein_onbereikbaar`) zijn gesloten én getest vóór deze fase — 11 tests groen (`test_oerwoud_plant` + `test_loop_status.TestOnbereikbaarBrein`), plus veld-bewezen tijdens de harnas-rondleiding (3 sept): een verontreinigde aanwijzing in `~/.growkit` werd door de status-modus correct als mens-vraag afgehandeld. Task 2 erft dus geen openstaand probleem.

## Zelfreview-checklist (voor de executor)

1. **Bedienaar-contract:** geen enkele poort- of motor-logica gedupliceerd in adapter of app; scan + contract-tests (taak 4) bewijzen het.
2. **Confirmatie zonder uitzonderingen:** elke uitvoerende adapter-aanroep eist `"bevestig": true`; een UI-knop zonder vlag kan per definitie niets uitvoeren — test bewijst het.
3. **Geen shell, geen secrets:** scan over adapter + Runner; stdout-parse-tests; reviewconfig-inhoud komt nooit in JSON-uitvoer.
4. **Huisstijl trouw:** fonts ingebed, kleuren uit de mockup-CSS, geen systeem-blauw; screenshots in het bewijs-document.
5. **Bekende valkuilen:** (a) `Process` zonder `shell`; (b) JSON-uitvoer — élke print in de adapter-paden moet via stderr of in het JSON-document (unit: stdout-parse-check); (c) XcodeGen-versie pinnen in build.sh; (d) geen SwiftUI-tests in v1 — het contract leeft in de adapter-tests; de UI is een weergave; (e) oerwoud-staat in app-tests → temp-home via env, nooit de echte `~/.growkit` (les uit de harnas-rondleiding: een verontreinigde echte aanwijzing werd alleen door toeval zichtbaar); (f) app-build in E2E → pinned `xcodegen` en `xcodebuild -destination 'platform=macOS'`, geen simulator; (g) mijlpaal-weigering (beslissing 7) zit in de adapter vóór de motor — niet als app-afvang erna.
