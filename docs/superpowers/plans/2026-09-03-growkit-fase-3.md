# GrowKit Fase 3 — Implementatieplan: Review-laag

Datum: 3 september 2026
Status: concept — ter goedkeuring (Tiëndo) en optionele review (Claude) vóór uitvoering
Spec: `docs/superpowers/specs/2026-09-03-growkit-design.md` (v10)
Fase 1: af (16 tests + E2E, `cbaa26e`). Fase 2: af (Test 1: 7/7, Test 2: 5/5, `64bfce6`).

**Goal:** Fase 3 reduceert het aantal mens-momenten zonder de mens te vervangen: mens_verificatie-stappen krijgen eerst een onafhankelijke reviewer-blik (§9), de ruwe prompt wordt geschuurd tot een concept vóór de poort (§11.1), grote taken krijgen een vaste mijlpaal-controle (§11.4), en VPS-doele worden per profiel configureerbaar (§12.3). Kernbegrenzing uit de spec blijft overeind: machine-bewijs is eerste keuze; de reviewer vermindert mens-inzet, vervangt de mens niet; bij "onduidelijk" wordt alsnog de mens geroepen.

**Architecture:** Nieuwe module `growkit_review.py` haalt de reviewer-rol door een provider-agnostische aanroep. Configuratie leeft in `reviewconfig.json` (repo-niveau, géén leveranciers-binding): rollen → aanroep-voorschrift (bijv. endpoint/CLI-commando), nooit hardcoded modelnamen in profielen of code. De motor blijft ongewijzigd in zijn faalcontract; de reviewer zit vóór het mens-moment, er niet in plaats van.

**Tech Stack:** Python 3.11+ (stdlib only), unittest, bash voor E2E. HTTP-reviewers via urllib (stdardlib); lokale CLI-reviewers via subprocess — beide vallen onder bestaande bewijs-types (http_check/shell_check).

## Global Constraints

- Zelfde basis als fase 1-2: Nederlands, geen pip-dependencies, gecodeerd bewijs, TDD (eerst falende check), commit+push per taak.
- **Provider-agnostisch, hard:** nergens een leveranciers-modelnaam in code, profielen of defaults. Alleen rolnamen (`"reviewer"`) + een gebruikers-configuratiebestand dat niet met defaults wordt meegeleverd (geen stille leveranciers-binding).
- **Machine-bewijs blijft eerste keus** (§9): de reviewer krijgt alleen stappen die al als `mens_verificatie` gemarkeerd zijn; geen enkele machine-toetsbare stap gaat naar een reviewer.
- **De mens blijft de eindbeslisser:** reviewer-oordeel "geslaagd" maakt een stap nog niet definitief — het vermindert alleen het mens-moment tot een ratificatie; "onduidelijk" of "gefaald" = mens (altijd).
- Harnas bouwen we nog niet (fase 4). Oerwoud niet (fase 5).

---

## Task 1: Reviewconfiguratie — rollen zonder leveranciers (open punt §12.5)

**Files:** Create `growkit_review.py` (config-lezer + validatie); Test: `tests/test_reviewconfig.py`

**Interface:**
- `laad_reviewconfig(pad: Path) -> dict | None` — leest `reviewconfig.json`; retourneert None bij afwezigheid (review uit = alles gaat naar de mens, zoals in fase 1-2).
- `valideer_reviewconfig(config: dict) -> list[str]` — controleert vorm: elke rol heeft `type` (`http`|`cli`), per type de verplichte velden (`url`+`verwacht_status` resp. `commando`), en géén verboden velden (`model`, `provider`, `leverancier`).

- [ ] **Step 1: Falende tests** — afwezig bestand → None; geldig config → gevuld; config met `model`-veld → weigering (leveranciers-binding is schema-fout); http-rol zonder url → weigering.
- [ ] **Step 2: Run — falen. Step 3: Bouw. Step 4: Groen.**
- [ ] **Step 5: Voorbeeld-config meeleveren als `reviewconfig.voorbeeld.json`** (met `type: "http"` naar een placeholder-URL en duidelijke NL-commentaarregels) — voorbeeld, niet actief; het echte bestand staat in .gitignore (per-machine geheim, mag leveranciers-IDs bevatten maar geen secrets).
- [ ] **Step 6: Commit** — `feat: reviewconfig — rollen zonder leveranciers-binding (§12.5)`

## Task 2: Reviewer-aanroep — output + verwacht → oordeel (§9)

**Files:** Modify `growkit_review.py`; Test: `tests/test_reviewer.py`

**Interface:** `roep_reviewer(rol: str, stap: dict, uitvoer: str, config: dict) -> str` — retourneert `"geslaagd"`, `"gefaald"`, of `"onduidelijk"`. Gedrag:
- `type: "http"`: POST de stap-definitie + uitvoer naar de geconfigureerde URL; het antwoord bevat een gecodeerd oordeel-veld (`{"oordeel": "geslaagd|gefaald|onduidelijk"}`).
- `type: "cli"`: voer het geconfigureerde commando uit met de stap+uitvoer als stdin-argument; het antwoord wordt gelezen als één van de drie gecodeerde oordelen (geen vrije tekst-parsing: exacte string-match op de drie waarden, anders `"onduidelijk"`).
- Time-out (10s http / 60s cli) of elke exceptie → `"onduidelijk"` — bij technische twijfel roep je de mens, nooit een gok.

- [ ] **Step 1: Falende tests** — cli-reviewer die "geslaagd" print → geslaagd; http-reviewer die een oordeel-JSON teruggeeft → correct vertaald; reviewer die onzin antwoordt → `"onduidelijk"`; crash/timeout → `"onduidelijk"`.
- [ ] **Step 2: Run — falen. Step 3: Bouw (stdlib only). Step 4: Groen.**
- [ ] **Step 5: Commit** — `feat: reviewer-aanroep — gecodeerd oordeel, twijfel = mens (§9)`

## Task 3: Motor-koppeling — reviewer vóór het mens-moment

**Files:** Modify `growkit_motor.py`; Test: `tests/test_motor_review.py`

**Gedrag:** bij een `mens_nodig`-stap mét een `review: "reviewer"`-veld én een geldige reviewconfig: roep de reviewer; `"geslaagd"` → log `review_ok_wacht_ratificatie` (de mens ratificeert later in bulk, niet per stap); `"gefaald"`/`"onduidelijk"`/geen config → exact het fase-1-2-gedrag (`wacht_op_mens`, bericht aan de mens). Het logboek noteert altijd welke rol is geraadpleegd en wat het oordeel was (append-only, geen verdwijnen van het mens-moment uit de geschiedenis).

- [ ] **Step 1: Falende tests** — stap mét reviewer en config: reviewer-oordeel "geslaagd" → status `review_ok_wacht_ratificatie`, geen `roep_mens`-print; oordeel "onduidelijk" → klassiek mens-moment; géén config → klassiek mens-moment; stappen zonder `review`-veld onaangetast.
- [ ] **Step 2: Run — falen. Step 3: Bouw. Step 4: Groen (incl. alle fase 1-2 tests onaangetast).**
- [ ] **Step 5: Commit** — `feat: reviewer vóór het mens-moment — ratificatie i.p.v. storing (§9)`

## Task 4: E2E — reviewlaag in de praktijk

**Files:** Create `tests/e2e_test3_review.sh`; bewijs in `docs/superpowers/bewijs/fase-3-test3.md`

Slaag-criteria (protocol-uitbreiding, vóór de run vastgelegd):
1. Plant met een cli-test-reviewer (echo "geslaagd") in reviewconfig: stap-008 logt `review_ok_wacht_ratificatie`, exit 0.
2. Dezelfde plant met reviewer die "onduidelijk" antwoordt: stap-008 logt `wacht_op_mens`, klassieke mens-instructie.
3. Zonder reviewconfig: identiek aan fase-2-gedrag (regressie-bewijs).
4. Alle overige stappen: 7× geslaagd, ongewijzigd — de reviewer raakt nooit machine-bewijs-stappen.
5. Logboek vermeldt in elk geval de geraadpleegde rol + oordeel.

- [ ] **Step 1: Script schrijven. Step 2: Run — groen; faal-uitvoer bewaren bij falen. Step 3: Bewijs-document. Step 4: Commit.**

## Task 5: Slijper-schuring (§11.1 stappen 1-2) — alleen expliciete

**Files:** Modify `growkit_poort.py`; Test: `tests/test_slijper.py`

**Gedrag:** de slijper in `beoordeel_invoer` wordt uitgebreid: bij complete velden wordt het concept *samengevoegd zonder her-interpretatie* (formulier-antwoorden → opdracht, §11.3-punt 2); wat niet uit de invoer af te leiden is, wordt een vraag, nooit een aanname. Het mens-moment (bevestiging) blijft onaangetast.

- [ ] **Step 1: Falende tests** — complete invoer → concept bevat exact de drie velden, geen verzonnen extra's; incomplete invoer → alleen vragen over ontbrekende velden; concept vermeldt de rauwe invoer als bron.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit.**

## Task 6: Mijlpaal-bevestiging (§11.4)

**Files:** Modify `seed.py` + `growkit_poort.py`; Test: `tests/test_mijlpaal.py`

**Gedrag:** bij planten van profielen met ≥ N stappen (N = configureerbaar in het profiel, standaard 10) toont seed.py vóór de motorstart het vaste mijlpaal-formaat (begrepen / afgesproken mèt logboek-verwijzing / bewijs tot nu toe / hierna) en vraagt één bevestiging; de bevestiging wordt append-only gelogd. Het huidige tweede-brein-profiel (8 stappen) raakt de drempel niet — dus geen gedragsverandering in de bestaande E2E's (regressie-check).

- [ ] **Step 1: Falende tests** — profiel met 10 stappen → mijlpaal-blok + bevestigingsvraag; 8-stappenprofiel → geen mijlpaal; bevestiging wordt gelogd.
- [ ] **Step 2-4: falen → bouwen → groen. Step 5: Commit.**

## Task 7: ssh-configuratie per profiel (open punt §12.3)

**Files:** Create `profielen/_vps-doel.example.json`; documentatie in `profielen/INDEX.md` + SEED.md-leesroute-noot

**Beslissing (vast te leggen):** ssh-doelen worden **per profiel geconfigureerd** (herbruikbaar), niet tijdens het planten opgevraagd — planten moet één klik blijven (§11.3-geest). Voorbeeldbestand met velden `host`, `gebruiker`, `poort`, en de vuistregel: sleutels leven alleen op de doelmachine in `~/.ssh/config`, nooit in GrowKit-bestanden of de chat.

- [ ] **Step 1: Voorbeeld + docs schrijven. Step 2: Commit.** (Geen code in fase 3 — er is nog geen VPS-profiel om te planten; dit is voorbereiding, geen infra.)

## Task 8: Afsluiting

- [ ] **Step 1: Zelfreview** — §9 volledig gedekt (rol ≠ leverancier, onduidelijk → mens, machine-bewijs eerst); §11.1, §11.4, §12.3, §12.5 afgehandeld; regressie: alle fase 1-2 tests + E2E's groen.
- [ ] **Step 2: Mijlpaal-digest** naar Agent-Brain inbox.
- [ ] **Step 3: Commit** — `docs: fase 3 af — review-laag bewezen`

---

## Zelfreview-checklist (voor de executor)

1. **Leveranciers-onafhankelijkheid:** geen enkele modelnaam in code/tests/defaults; reviewconfig.voorbeeld.json gebruikt placeholders; het echte reviewconfig.json staat in .gitignore.
2. **De mens niet vervangen:** reviewer-"geslaagd" = ratificatie-vermindering, nooit definitief zonder mens; logboek houdt het mens-moment zichtbaar.
3. **Machine-bewijs eerst:** geen pad waar een `shell/file/json/http`-check-stap naar de reviewer gaat.
4. **Regressie:** alle fase 1-2 unit-tests en de drie E2E-scripts moeten na elke taak groen blijven — de review-laag mag niets aan fase 1-2-gedrag veranderen behalve op `mens_nodig`-stappen mét review-veld.
5. **Bekende valkuilen:** (a) http-reviewer in tests → gebruik alleen localhost of cli-type, geen externe dienst; (b) reviewer-antwoorden zijn exact-match op drie waarden — alles anders is "onduidelijk"; (c) reviewconfig van de gebruiker kan secrets bevatten → .gitignore vóór eerste echte bestand; (d) N=10-drempel dynamisch uit het profiel lezen, nooit hardcoded in de test.
