# GrowKit Fase 5 — Implementatieplan: Het Oerwoud

Datum: 3 september 2026
Status: concept — ter goedkeuring (Tiëndo) en review (Claude) vóór uitvoering
Spec: `docs/superpowers/specs/2026-09-03-growkit-design.md` (v10, §13 + §11.2 + drift-guard)
Fase 1-4: af en bewezen (110 unit-tests, E2E 1-4 groen; laatste afsluiting `5154d51`).

**Goal:** Fase 5 bewijst dat meerdere bomen onder één gedeeld brein kunnen opereren (§13): de eerste `tweede-brein`-boom wordt het hart van het oerwoud, elke nieuwgeboren boom meldt zich daar aan in het **boom-register** (via haar volwaardige geboortebewijs), stuurt haar VOORSTELLEN append-only door naar de brein-inbox, en leest het brein als alleen-lezen opties-bron (§11.2-vliegwiel). Kernbegrenzing: **sync is append-only en eenrichting (boom → brein-inbox); het brein is alleen-lezen voor de loop behalve zijn register- en inbox-toevoegingen; de mens curateert — geen verborgen leerproces, geen automatische promotie.**

**Architecture:** Nieuwe module `kern/growkit_oerwoud.py` (geboortebewijs, boom-register, doorstroom, brein-opties — pure functies, hergebruikt door seed.py/loop.py). Per-machine oerwoud-staat (waar groeit het brein) leeft buiten de repo in `~/.growkit/oerwoud.json` — GrowKit-eigen domein, de repo blijft machine-neutraal. De motor blijft ongewijzigd; registratie en doorstroom zijn post-plant stappen in loop.py met machine-verifieerbare logboek-entries (zelfde patroon als de mijlpaal-entry uit fase 3).

**Tech Stack:** Python 3.11+ (stdlib only — `uuid`, `platform`, `json`, `pathlib`), unittest, bash voor E2E. Geen git-operaties in fase 5: sync is lokaal op dezelfde machine (cross-machine via git-remote is een expliciet uitgestelde beslissing, zie beslissing 5).

## Global Constraints

- Zelfde basis als fase 1-4: Nederlands, geen pip-dependencies, gecodeerd bewijs, TDD (eerst falende check), commit+push per taak.
- **Drift-guard hard (§13):** het brein ontvangt uitsluitend register-entries en VOORSTEL-bestanden. Paden, logboeken, ssh-doele, sleutels, omgevings-specifieke staat worden **nooit** gesynct — dit is per taak een test.
- **Alleen-lezen + append-only:** de loop schrijft in het brein uitsluitend (a) register-entries en (b) nieuwe VOORSTEL-bestanden in de brein-inbox. Bestaande brein-bestanden worden nooit gelezen-met-schrijven, nooit gemuteerd, nooit verwijderd.
- **De mens curateert:** promotie van VOORSTEL naar kennis/projecten blijft handwerk; de loop geeft status-overzicht, geen acties op brein-inhoud.
- Motor-faalcontract en poort blijven onaangetast; alle fase 1-4 tests + E2E's blijven groen.

---

## Task 1: Geboortebewijs volwaardig — placeholders worden feiten

**Files:** Create `kern/growkit_oerwoud.py`; Modify `seed.py` + `loop.py` (post-plant); Test: `tests/test_oerwoud_geboorte.py`

**Gedrag:** na een geslaagde plant wordt het gekopieerde `geboortebewijs.json` (nu nog met `{{BOOM_ID}}`/`{{MACHINE}}`/`{{LOCATIE}}`/`{{TIJDSTIP}}`) volgemaakt: `boom_id` = uuid4, `machine` = platform-naam, `locatie` = geresolveerd doel-pad, `geplant_op` = UTC-tijdstip. Daarna een machine-controle (valide JSON, verplichte velden, **geen `{{...}}`-placeholders meer**) die append-only als systeem-entry in het boom-logboek wordt gelogd (patroon: mijlpaal-entry uit fase 3). Bestaande bomen met placeholders blijven geldig — het register behandelt ze als "vóór-fase-5" (zie taak 2).

- [ ] **Step 1: Falende tests** — vul_geboortebewijs zet de vier velden (uuid-formaat, machine, locatie, tijdstip); controleer accepteert gevulde bewijzen en weigert placeholders; systeem-entry append-only (bestaande entries intact).
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: geboortebewijs volwaardig — uuid, machine, locatie, tijdstip (§13)`

## Task 2: Het boom-register — één plek die weet wie er bestaat

**Files:** Modify `kern/growkit_oerwoud.py`; Test: `tests/test_oerwoud_register.py`

**Interface:** `meld_geboorte(register_pad: Path, bewijs: dict) -> dict` — append-only entry `{type: "geboorte", boom_id, profiel, machine, locatie, tijdstip}` in `register/bomen.json` in de **brein-boom** (map wordt aangemaakt waar nodig). `lees_register(pad) -> list[dict]`. `recentste_status(register, boom_id) -> str | None` (geboorte / geregistreerd / gederegistreerd — deregistratie is een vervolg-entry door de mens, nooit verwijdering). Corrupt register → foutstatus, mens, geen auto-reparatie (patroon `corrupt_logboek`).

- [ ] **Step 1: Falende tests** — geboorte-entry append-only (bestaande entries blijven); dubbele boom-id → geweigerd met nette fout (één geboorte per boom); deregistratie via vervolg-entry; afwezig/corrupt bestand → leeg/foutstatus.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: boom-register — append-only in de brein-boom (§13)`

## Task 3: Brein-detectie en registratie bij het planten

**Files:** Create `~/.growkit/oerwoud.json`-lezer (in `kern/growkit_oerwoud.py`); Modify `loop.py`; Test: `tests/test_oerwoud_plant.py`

**Gedrag:** na een geslaagde plant vraagt de loop: "Waar groeit je brein? (pad, of leeg = deze boom wordt het brein)". Het antwoord wordt opgeslagen in de per-machine staat en de geboorte wordt aangemeld in het register van het brein. Is het brein al bekend op deze machine → geen vraag; de geboorte wordt direct aangemeld. Machine-bewijs van registratie: de register-entry verwijst naar een bestáánd geboortebewijs (`controleer_geboortebewijs` van taak 1). Bij een second-brein-plant die het brein **wordt**: de registratie-entry krijgt `is_brein: true`.

- [ ] **Step 1: Falende tests** (invoer_fn-injectie, temp-homes) — eerste plant zonder brein → vraag, "leeg" maakt deze boom het brein, staat opgeslagen; tweede plant → geen vraag, registratie in het bestaande register; register-entry verwijst naar bestaand geboortebewijs; geen bevestiging → niets geregistreerd (poort-discipline).
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: brein-detectie + geboorteregistratie bij het planten (§13)`

## Task 4: VOORSTEL-doorstroom — sync is append-only en gemarkeerd

**Files:** Modify `kern/growkit_oerwoud.py` + `loop.py`; Test: `tests/test_oerwoud_voorstellen.py`

**Gedrag:** VOORSTEL-bestanden zijn bestanden in de boom-inbox die beginnen met `VOORSTEL-` (machinetoetsbare naam-conventie, zie beslissing 3). `stuur_voorstellen(boom_doel, brein_pad)` kopieert ze append-only naar de brein-inbox met boom-id-prefix (`VOORSTEL-<boom_id>-<naam>`), en logt per bestand een gebeurtenis in het boom-logboek. Drift-guard, hard getest: bestanden zonder `VOORSTEL-`-prefix (REGELS.md, logboeken, `.ssh`-achtige paden, willekeurige bestanden) worden **nooit** gekopieerd; naam-collisie in de brein-inbox → nette weigering (nooit overschrijven). 

- [ ] **Step 1: Falende tests** — VOORSTEL-bestand komt append-only in de brein-inbox met prefix; REGELS.md en niet-gemarkeerde bestanden blijven thuis; tweemaal doorsturen → geen duplicaten (bron gemarkeerd als verzonden via logboek-check); collisie → weigering zonder overschrijven; corrupt brein-pad → nette fout.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: VOORSTEL-doorstroom — append-only, gemarkeerd, drift-guard hard (§13)`

## Task 5: Status-modus — het oerwoud zichtbaar maken (modus 5)

**Files:** Modify `loop.py`; Test: `tests/test_loop_status.py`

**Gedrag:** modus 5 (nu een stub) toont bij een boom: identiteit uit het geboortebewijs (boom-id, profiel, geplant_op), register-status in het brein, tellers (VOORSTEL wachtend in inbox / verzonden) en de laatste mijlpaal- of faal-entry uit het logboek. Puur lezen — geen acties, geen mutaties.

- [ ] **Step 1: Falende tests** — status toont boom-id + profiel; teller klopt bij n en n+1 VOORSTEL-bestanden; laatste mijlpaal-entry wordt getoond; zonder geboortebewijs → nette mededeling, geen crash.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: status-modus — boom-identiteit, register en tellers zichtbaar (§13)`

## Task 6: Het vliegwiel — het brein voedt de formulier-opties (§11.2)

**Files:** Modify `kern/growkit_oerwoud.py` + `loop.py` (formuliervraag); Test: `tests/test_oerwoud_opties.py`

**Gedang:** `brein_opties(brein_pad) -> list[str]` leest **alleen-lezen** de namen van de mappen in `projecten/` van het brein (max. 5, alfabetisch) en de loop voegt ze toe als extra opties onderaan de kiemkeuze- en omgeving-vragen, gemarkeerd "uit je brein". Geen brein bekend of map leeg → geen extra opties (gedrag identiek aan vandaag). Opties zijn advies — de poort blijft de enige invoerbescherming en interpreteert inhoud niet.

- [ ] **Step 1: Falende tests** — brein met 3 projectmappen → 3 extra opties gemarkeerd "uit je brein"; leeg/onbekend brein → geen extra opties; alleen-lezen bewezen (brein-bestanden onaangetast na formuliergebruik); meer dan 5 projecten → afgekapt op 5.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: vliegwiel — brein als alleen-lezen opties-bron (§11.2)`

## Task 7: E2E Test 5 — het oerwoud op een schone plek

**Files:** Create `tests/e2e_test5_oerwoud.sh`; bewijs in `docs/superpowers/bewijs/fase-5-test5.md`

**Protocol — vóór de run vastgesteld (fase-2-les):**
1. Schone plek: plant boom A (tweede-brein) → "leeg" maakt haar het brein; geboortebewijs volwaardig (geen placeholders), register-entry met `is_brein: true`.
2. Plant boom B op een tweede plek → geen brein-vraag meer; register van het brein bevat géén dubbele boom-ids en verwijst naar bestaande geboortebewijzen.
3. VOORSTEL-bestand in boom B's inbox → doorstroom: append-only in brein-inbox met boom-id-prefix; REGELS.md is níét meegenomen (drift-guard-bewijs).
4. Status-modus voor beide bomen toont identiteit, register-status en tellers.
5. Corrupt-register-pad → mens-boodschap, geen crash, geen traceback; exit-codes netjes.
6. Uitsluitend python3 + gepijpte antwoorden — geen agent betrokken.

- [ ] **Step 1: Script schrijven. Step 2: Run — groen; faal-uitvoer bewaren bij falen. Step 3: Bewijs-document. Step 4: Commit** — `test: Test 5 — oerwoud bewezen (register + doorstroom + vliegwiel)`

## Task 8: Afsluiting

- [ ] **Step 1: Zelfreview** — drift-guard bewezen per taak; alleen-lezen-garantie van het brein; append-only overal; motor/poort onaangetast; regressie: fase 1-4 tests + E2E 1-5 groen. Bewijs: `docs/superpowers/bewijs/fase-5-zelfreview.md`.
- [ ] **Step 2: Mijlpaal-digest als VOORSTEL** naar Agent-Brain inbox (append-only).
- [ ] **Step 3: Commit** — `docs: fase 5 af — oerwoud bewezen`

---

## Open beslissingen — expliciet voor de reviewer (Claude)

1. **Per-machine oerwoud-staat:** `~/.growkit/oerwoud.json` (voorkeur: GrowKit-eigen domein, zoals `~/.ssh/config`; de repo blijft machine-neutraal) vs. het brein-pad bij elke plant opnieuw vragen (frictie) vs. in de repo (machine-specifieke staat hoort daar niet).
2. **Register-curate:** geboorte-entries zijn machine-feiten en worden direct gelogd (voorkeur — het bewijs bestaat: het geboortebewijs is gecontroleerd); deregistratie/correctie gebeurt via vervolg-entries door de mens, nooit verwijdering. Alternatief: ook registratie als VOORSTEL (meer curatie, meer friction).
3. **VOORSTEL-conventie:** bestandsnaam-prefix `VOORSTEL-` in de boom-inbox als machinetoetsbaar criterium (voorkeur: simpel, te testen, consistent met de bestaande [AFGEWEZEN]-markeringsconventie uit REGELS.md) vs. frontmatter-parsing (inhoudsinterpretatie — de poort-geest verbiedt dat).
4. **Doorstuur-trigger:** automatisch na een geslaagde plant + beschikbaar via de status-modus met één bevestiging (voorkeur: minimale klikken, §11.3-geest) vs. een aparte zesde modus.
5. **Cross-machine sync:** fase 5 is bewust lokaal-only (voorkeur — git-remotes in de loop voeren git-operaties in het uitvoeringspad; dat verdient een eigen bewijsronde) vs. direct git-sync bouwen. Uitstel betekent: het oerwoud is eerst één-machine waar; fase 5.1 (git) volgt indien gewenst.

## Zelfreview-checklist (voor de executor)

1. **Drift-guard:** geen test-pad kopieert ook maar één bestand zonder `VOORSTEL-`-prefix; de drift-test staat in taak 4 én E2E-5 criterium 3.
2. **Alleen-lezen brein:** na elke test-run worden brein-bestanden byte-voor-byte vergeleken met het origineel, behalve register/ en inbox-toevoegingen.
3. **Append-only:** register, logboeken en inbox verlenen alleen `append`; geen enkele functie in `growkit_oerwoud.py` schrijft een bestaand bestand opnieuw weg (geen `write_text` op gevulde bestanden behalve de append-helpers).
4. **Regressie:** alle fase 1-4 unit-tests + E2E 1-4 blijven groen; het tweede-brein-profiel wordt NIET gewijzigd (geen nieuwe stappen — het register leeft buiten het profiel).
5. **Bekende valkuilen:** (a) `~/.growkit` in tests → temp-home via monkeypatch/env, nooit de echte home; (b) uuid's in bewijzen → alleen formaat-checken, nooit vast waarde; (c) boom-id in bestandsnamen → de uuid is bestandsnaam-veilig (hex + streepjes); (d) brein = de boom zelf → registratie met `is_brein: true` mag niet dubbel (taak 2's dubbel-check geldt ook hier); (e) E2E-3 assert "8 entries" in de boom-logboeken blijft staan — registratie/doorstroom schrijven in het boom-logboek vóórdat E2E-3 telt? Nee: E2E-3 draait in zijn eigen plant met eigen logboek; controleer de volgorde in de script-run.
