# GrowKit Fase 5 — Implementatieplan: Het Oerwoud

Datum: 3 september 2026
Status: v2 — beslissingen vastgelegd na review (Claude, 3 sept 2026); twee gaten gedicht (migratie oude bomen, brein_onbereikbaar) en valkuil (e) geverifieerd — klaar voor uitvoering
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

**Gedrag:** na een geslaagde plant wordt het gekopieerde `geboortebewijs.json` (nu nog met `{{BOOM_ID}}`/`{{MACHINE}}`/`{{LOCATIE}}`/`{{TIJDSTIP}}`) volgemaakt: `boom_id` = uuid4, `machine` = platform-naam, `locatie` = geresolveerd doel-pad, `geplant_op` = UTC-tijdstip (expliciete parameter; migratie van oude bomen geeft hier het teruggerekende tijdstip door, zie taak 3). Daarna een machine-controle (valide JSON, verplichte velden, **geen `{{...}}`-placeholders meer**) die append-only als systeem-entry in het boom-logboek wordt gelogd (patroon: mijlpaal-entry uit fase 3). Oude bomen (fase 1-4) met placeholders zijn **migreerbaar**: `is_voor_fase5(bewijs)` detecteert placeholders; het migratie-pad zelf staat in taak 3.

- [ ] **Step 1: Falende tests** — vul_geboortebewijs zet de vier velden (uuid-formaat, machine, locatie, tijdstip) en accepteert een expliciete geplant_op; controleer accepteert gevulde bewijzen en weigert placeholders; is_voor_fase5 herkent placeholders; systeem-entry append-only (bestaande entries intact).
- [ ] **Step 2: E2E-1 protocol-uitbreiding (vóór de fase-5-run vastgelegd):** E2E-1 assert `len(entries) == 8` (regel 49) — de systeem-entry maakt dat 9. De assert wordt aangepast mét notitie in het bewijs-document; E2E-3 is veilig (roept de motor direct aan, geen loop.py-plant).
- [ ] **Step 3-5: bouwen → groen. Step 6: Commit** — `feat: geboortebewijs volwaardig — uuid, machine, locatie, tijdstip + migratie-detectie (§13)`

## Task 2: Het boom-register — één plek die weet wie er bestaat

**Files:** Modify `kern/growkit_oerwoud.py`; Test: `tests/test_oerwoud_register.py`

**Interface:** `meld_geboorte(register_pad: Path, bewijs: dict) -> dict` — append-only entry `{type: "geboorte", boom_id, profiel, machine, locatie, tijdstip}` in `register/bomen.json` in de **brein-boom** (map wordt aangemaakt waar nodig). `lees_register(pad) -> list[dict]`. `recentste_status(register, boom_id) -> str | None` (geboorte / geregistreerd / gederegistreerd — deregistratie is een vervolg-entry door de mens, nooit verwijdering). Corrupt register → foutstatus, mens, geen auto-reparatie (patroon `corrupt_logboek`).

- [ ] **Step 1: Falende tests** — geboorte-entry append-only (bestaande entries blijven); dubbele boom-id → geweigerd met nette fout (één geboorte per boom); deregistratie via vervolg-entry; afwezig/corrupt bestand → leeg/foutstatus.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: boom-register — append-only in de brein-boom (§13)`

## Task 3: Brein-detectie en registratie bij het planten

**Files:** Create `~/.growkit/oerwoud.json`-lezer (in `kern/growkit_oerwoud.py`); Modify `loop.py`; Test: `tests/test_oerwoud_plant.py`

**Gedrag:** na een geslaagde plant vraagt de loop: "Waar groeit je brein? (pad, of leeg = deze boom wordt het brein)". Het antwoord wordt opgeslagen in de per-machine staat en de geboorte wordt aangemeld in het register van het brein. Is het brein al bekend op deze machine → geen vraag; de geboorte wordt direct aangemeld. Machine-bewijs van registratie: de register-entry verwijst naar een bestáánd, gecontroleerd geboortebewijs (`controleer_geboortebewijs` van taak 1). Bij een second-brein-plant die het brein **wordt**: de registratie-entry krijgt `is_brein: true`.

**Migratie van oude bomen (gat-review 1):** een boom uit fase 1-4 heeft placeholders en kan daardoor de registratie-controle niet passeren — de belofte "blijven geldig" uit taak 1 wordt hier waargemaakt. Bij registratie van een boom waarvan `is_voor_fase5` waar is, biedt de loop de migratie aan: het geboortebewijs wordt volgemaakt met `geplant_op` **teruggerekend uit de eerste (oudste) logboek-entry** van de boom — niet "nu", want de geboorte is historisch feit. Weigering van de migratie → geen registratie, geen stilzwijgende aanname. Corrupt boom-logboek tijdens het terugrekenen → foutstatus, mens.

**Brein onbereikbaar (gat-review 2):** wijst de per-machine staat naar een brein-pad dat niet bestaat (verplaatst, verwijderd, niet-aangesloten schijf) → expliciete foutstatus `brein_onbereikbaar`: de mens wordt geroepen, er is **geen** fallback naar "leeg = nieuw brein" — dat zou een bestaand oerwoud onbedoeld splitsen. De mens kan het pad corrigeren (de staat is pointer-config, geen logboek — bijgewerkt na expliciete menselijke correctie) of afbreken.

- [ ] **Step 1: Falende tests** (invoer_fn-injectie, temp-homes) — eerste plant zonder brein → vraag, "leeg" maakt deze boom het brein, staat opgeslagen; tweede plant → geen vraag, registratie in het bestaande register; register-entry verwijst naar bestaand geboortebewijs; geen bevestiging → niets geregistreerd (poort-discipline); **migratie: boom met placeholders + eerste logboek-entry 3 sept 18:42 → na migratie `geplant_op` == dat tijdstip, geen placeholders, registratie slaagt; weigering → geen registratie; corrupt logboek tijdens terugrekenen → foutstatus**; **brein-pad onbereikbaar → `brein_onbereikbaar`, geen crash, géén nieuw brein, geen registratie; pad-correctie door de mens → registratie slaagt daarna; afbreken → geen actie**.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: brein-detectie + geboorteregistratie + migratie oude bomen + brein_onbereikbaar (§13)`

## Task 4: VOORSTEL-doorstroom — sync is append-only en gemarkeerd

**Files:** Modify `kern/growkit_oerwoud.py` + `loop.py`; Test: `tests/test_oerwoud_voorstellen.py`

**Gedrag:** VOORSTEL-bestanden zijn bestanden in de boom-inbox die beginnen met `VOORSTEL-` (machinetoetsbare naam-conventie, zie beslissing 3). `stuur_voorstellen(boom_doel, brein_pad)` kopieert ze append-only naar de brein-inbox met boom-id-prefix (`VOORSTEL-<boom_id>-<naam>`), en logt per bestand een gebeurtenis in het boom-logboek. Drift-guard, hard getest: bestanden zonder `VOORSTEL-`-prefix (REGELS.md, logboeken, `.ssh`-achtige paden, willekeurige bestanden) worden **nooit** gekopieerd; naam-collisie in de brein-inbox → nette weigering (nooit overschrijven). 

- [ ] **Step 1: Falende tests** — VOORSTEL-bestand komt append-only in de brein-inbox met prefix; REGELS.md en niet-gemarkeerde bestanden blijven thuis; tweemaal doorsturen → geen duplicaten (bron gemarkeerd als verzonden via logboek-check); collisie → weigering zonder overschrijven; corrupt brein-pad → nette fout.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: VOORSTEL-doorstroom — append-only, gemarkeerd, drift-guard hard (§13)`

## Task 5: Status-modus — het oerwoud zichtbaar maken (modus 5)

**Files:** Modify `loop.py`; Test: `tests/test_loop_status.py`

**Gedrag:** modus 5 (nu een stub) toont bij een boom: identiteit uit het geboortebewijs (boom-id, profiel, geplant_op), register-status in het brein, tellers (VOORSTEL wachtend in inbox / verzonden) en de laatste mijlpaal- of faal-entry uit het logboek. Puur lezen — geen acties, geen mutaties. Eén uitzondering met bevestiging: een boom die `is_voor_fase5` is of nog niet geregistreerd staat, krijgt hier het migratie-en-registratie-aanbod uit taak 3 (één bevestiging; weigering → geen actie).

- [ ] **Step 1: Falende tests** — status toont boom-id + profiel; teller klopt bij n en n+1 VOORSTEL-bestanden; laatste mijlpaal-entry wordt getoond; zonder geboortebewijs → nette mededeling, geen crash; **niet-geregistreerde oude boom → migratie-aanbod, weigering → geen actie; "ja" → geboortebewijs volgemaakt (teruggerekend) + geregistreerd**.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit** — `feat: status-modus — boom-identiteit, register en tellers zichtbaar (§13)`

## Task 6: Het vliegwiel — het brein voedt de formulier-opties (§11.2)

**Files:** Modify `kern/growkit_oerwoud.py` + `loop.py` (formuliervraag); Test: `tests/test_oerwoud_opties.py`

**Gedrag:** `brein_opties(brein_pad) -> list[str]` leest **alleen-lezen** de namen van de mappen in `projecten/` van het brein (max. 5, alfabetisch) en de loop voegt ze toe als extra opties onderaan de kiemkeuze- en omgeving-vragen, gemarkeerd "uit je brein". Geen brein bekend of map leeg → geen extra opties (gedrag identiek aan vandaag). Opties zijn advies — de poort blijft de enige invoerbescherming en interpreteert inhoud niet.

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

## Vastgelegde beslissingen (3 sept 2026, review Claude — niet meer open)

1. **Per-machine oerwoud-staat:** `~/.growkit/oerwoud.json`. Consistent met het `~/.ssh/config`-precedent uit fase 3: machine-specifieke staat hoort niet in een repo die machine-neutraal moet zijn.
2. **Register-entries direct gelogd, niet als VOORSTEL.** Een geboorte is een geverifieerd feit (het geboortebewijs is al gecontroleerd), geen interpretatie; VOORSTEL is voor dingen die de mens moet beoordelen — hier is niets te beoordelen.
3. **`VOORSTEL-`-naamconventie.** Machine-toetsbaar; frontmatter-parsing is inhoudsinterpretatie en dus een poort-schending. Consistent met de [AFGEWEZEN]-markeringsconventie uit REGELS.md.
4. **Doorsturen automatisch na een geslaagde plant + zichtbaar in de status-modus** — de "minimale klikken"-lijn van §11.3.
5. **Cross-machine sync uitgesteld.** Git-operaties in het uitvoeringspad (netwerk, auth, merge-conflicten) zijn een reëel nieuw risico-oppervlak dat een eigen bewijsronde verdient — fase 5.1, niet erbij geplakt.

**Gevonden gaten (gesloten in dit document):**
- **Gat 1 — oude bomen:** taak 1 beloofde "blijven geldig" maar taak 3 eiste een controle die placeholders weigert. Oplossing, verankerd in dit plan: `is_voor_fase5`-detectie (taak 1) + migratie-pad (taak 3): het geboortebewijs wordt volgemaakt met `geplant_op` teruggerekend uit de eerste logboek-entry; weigering → geen registratie. De status-modus (taak 5) is de ingang voor oude bomen.
- **Gat 2 — onbereikbaar brein:** eigen foutstatus `brein_onbereikbaar` in taak 3: mens roepen, geen crash, géén fallback naar "leeg = nieuw brein" (dat zou het oerwoud splitsen); pad-correctie of afbreken, beide alleen via de mens.

## Zelfreview-checklist (voor de executor)

1. **Drift-guard:** geen test-pad kopieert ook maar één bestand zonder `VOORSTEL-`-prefix; de drift-test staat in taak 4 én E2E-5 criterium 3.
2. **Alleen-lezen brein:** na elke test-run worden brein-bestanden byte-voor-byte vergeleken met het origineel, behalve register/ en inbox-toevoegingen.
3. **Append-only:** register, logboeken en inbox verlenen alleen `append`; geen enkele functie in `growkit_oerwoud.py` schrijft een bestaand bestand opnieuw weg (geen `write_text` op gevulde bestanden behalve de append-helpers).
4. **Regressie:** alle fase 1-4 unit-tests + E2E 1-4 blijven groen; het tweede-brein-profiel wordt NIET gewijzigd (geen nieuwe stappen — het register leeft buiten het profiel).
5. **Bekende valkuilen:** (a) `~/.growkit` in tests → temp-home via monkeypatch/env, nooit de echte home; (b) uuid's in bewijzen → alleen formaat-checken, nooit vaste waarde; (c) boom-id in bestandsnamen → de uuid is bestandsnaam-veilig (hex + streepjes); (d) brein = de boom zelf → registratie met `is_brein: true` mag niet dubbel (taak 2's dubbel-check geldt ook hier); (e) **E2E-tellingen, geverifieerd en definitief (3 sept):** E2E-1 assert `len(entries) == 8` (regel 49) en E2E-3 idem (regel 56). E2E-3 roept de motor **direct** aan (geen loop.py-plant) en blijft onaangetast. E2E-1 plant via `seed.py` en krijgt wél de taak-1-systeem-entry: de assert wordt in taak 1 uitgebreid naar 9, vastgelegd als protocol-uitbreiding vóór de fase-5-run. E2E-4's checkers filteren per stap-id en zijn bewezen ongevoelig voor extra systeem-entries; `e2e_plant.sh` telt geen exacte lengte. De migratie-systeem-entry (taak 3) telt alleen in bomen die nú gemigreerd worden — geen van de vijf bestaande E2E's migreert.
