# GrowKit Fase 2 — Implementatieplan: Kieming

Datum: 3 september 2026
Status: concept — ter review (Claude) en goedkeuring (Tiëndo) vóór uitvoering
Spec: `docs/superpowers/specs/2026-09-03-growkit-design.md` (v10)
Fase 1: af — bewijs: 16 unit-tests + E2E-rooktest groen (commit `cbaa26e`)

**Goal:** Fase 2 bewijst dat GrowKit ontkiemt buiten de werkbank van de bouwer: iemand met een verse kopie en geen voorkennis plant een tweede-brein mét machine-bewijs (Test 1), en vage invoer wordt geweigerd met concrete vragen in plaats van uitgevoerd (Test 2). Daarmee is het oorspronkelijke fase-2-doel behaald: *bewijs-afdwinging en leesroute werken in de praktijk.*

**Architecture-anekdoten die dit plan raakt:** seed.py is nu een kiemkeuze-menu + motor-aansluiting. Wat ontbreekt voor fase 2: (a) de leesroute wordt niet door het script afgedwongen — SEED.md adviseert, maar seed.py ontsluit niets per fase (spec §5, open punt 1); (b) de Scope-poort bestaat alleen als veldcontrole op doel+profiel, niet als volledige poort met weigeringsteksten en vragenformulier voor de drie invoertypes (spec §11, open punt 6); (c) er is geen meetbaar testprotocol voor Test 1 en Test 2 (open punt 4).

**Tech Stack:** Python 3.11+ (stdlib only), unittest, bash voor E2E.

## Global Constraints

- Zelfde als fase 1: Nederlands, geen pip-dependencies, gecodeerd bewijs, sjablonen geen heredocs, commit (+push) per taak, TDD (eerst falende check).
- **Geen harnas** (fase 4, pas na dit bewijs) en **geen volledige Prompt-slijper**: de slijper-schuring zelf komt later; fase 2 bouwt alleen de harde poort + het vragenformulier-formaat (§11.3). Het mens-moment blijft niet-onderhandelbaar.
- **Buiten-scope voor fase 2:** reviewer-rol-configuratie (§12.5, fase 3), oerwoud-sync (§13, fase 5), ssh-configuratie per profiel (§12.3 — alleen noteren als open punt in dit plan).

---

## Task 1: Testprotocol — meetbare slaag/faal-criteria (open punt 4)

**Files:** Create `docs/superpowers/testprotocol-fase-2.md`

De criteria worden vóór de tests zelf geschreven — zodat we niet achteraf de lat leggen waar het bewijs toevallig valt.

- [ ] **Step 1: Schrijf het testprotocol** met daarin:

**Test 1 — "Schone-pleg-plant" (een vreemde plant een tweede-brein)**

| # | Slaag-criterium (hard, meetbaar) | Hoe gemeten |
|---|---|---|
| 1.1 | Verse kloon van GitHub (niet de werkkopie) plant zonder fout | `git clone` naar tmp → `python3 seed.py --profiel tweede-brein --doel <tmp>/plant` → exit-code 0 |
| 1.2 | Alle 8 stappen machine-bewijs: 7× geslaagd, 1× wacht_op_mens | logboek.json geautomatiseerd gecontroleerd |
| 1.3 | De vijf kernmappen + INDEX.md + geboortebewijs bestaan in de plant | file_exists-checks in het E2E-script |
| 1.4 | Alle gekopieerde bestanden byte-voor-byte gelijk aan sjablonen | sha256-vergelijking |
| 1.5 | Geen schrijfactie buiten de doelmap | vóór/na-snapshot van de repo-werkmap: `git status --porcelain` blijft leeg |
| 1.6 | Herstart-gedrag: tweede run van seed.py op dezelfde doelmap faalt niet onnodig en verontreinigt het logboek niet | idempotente herhaling; logboek heeft geen "gefaald"-entries |
| 1.7 | Draait op Python 3.11+ zonder pip-install | schone venv/virtualenv-vrije run |

**Faal = elk criterium dat niet aantoonbaar slaagt. Geen grijswaarden: een plant is bewezen of hij is het niet.**

**Test 2 — "Vrije beschrijving" (de poort weigert ruis, vraagt scherp)**

| # | Slaag-criterium | Hoe gemeten |
|---|---|---|
| 2.1 | Vrije-beschrijving-invoer zonder einddoel/omgeving/slaag-criterium wordt geweigerd zónder enige uitvoering | unit-test: geen map aangemaakt, exit != 0 |
| 2.2 | De weigering bevat exact de drie verplichte velden als vragen + de vragenlijst-opties (§11.3 JSON-formaat) | unit-test op poort-uitvoer-structuur |
| 2.3 | Complete invoer (doel+omgeving+slaag-criterium) leidt tot een concept-opdracht die wacht op mens-bevestiging — niet direct uitvoert | unit-test: status `wacht_op_mens`, geen commando's uitgevoerd |
| 2.4 | Weigering + concept worden append-only gelogd (ruw + geschuurd + beslissing) | logboek-check |
| 2.5 | De vaste weigeringsteksten zijn droog-maar-nette, Nederlandse teksten uit spec §11 | tekstvergelijking in test |

- [ ] **Step 2: Commit** — `docs: testprotocol fase 2 — harde slaag/faal-criteria Test 1 & 2`

---

## Task 2: Leesroute-afdwinging — seed.py ontsluit per fase (spec §5, open punt 1)

**Files:** Modify `seed.py`; Create `growkit_leesroute.py`; Test: `tests/test_leesroute.py`

**Interface:** `fase_content(fase: int, context: dict) -> str` — retourneert uitsluitend de inhoud die bij de huidige fase hoort (fase 0: SEED.md-inhoud; fase 1: INDEX.md-inhoud; fase 2: de stap-JSON van de volgende uit te voeren stap; fase 3: SETUP.md-inhoud). Voorkeursimplementatie uit de spec: **directe content-injectie**, geen pad-verwijzing — wat de agent niet te zien krijgt, kan hij niet lezen.

- [ ] **Step 1: Falende test** — `fase_content(0, {})` bestaat nog niet; ook een test die beweert dat fase-2-content van stap-002 de tekst van stap-001 níet bevat (afdwinging, niet advies).
- [ ] **Step 2: Run — moet falen** (ModuleNotFoundError)
- [ ] **Step 3: Bouw `growkit_leesroute.py`** (stdlib): leest SEED.md, profielen/INDEX.md, profiel.json per stap, groei/SETUP.md uit de repo en geeft per fase alleen het relevante stuk terug. seed.py gebruikt dit in de interactieve modus om de agent-route te printen/injecteren; de `--profiel/--doel`-modus blijft werken zoals hij is.
- [ ] **Step 4: Run — groen** (alle tests, ook die van fase 1)
- [ ] **Step 5: Commit** — `feat: leesroute afgedwongen door script — per-fase content-injectie`

---

## Task 3: Scope-poort — weigeren en vragen bij alle drie invoertypes (spec §11, open punt 6)

**Files:** Create `growkit_poort.py`; Modify `seed.py` (vrije-beschrijving-modus `--vrij "<beschrijving>"`); Test: `tests/test_poort.py`

**Interface:**
- `beoordeel_invoer(invoer: dict, type_: str) -> tuple[bool, str, list[dict]]` — (geaccepteerd, weigeringstekst-of-concept, vragenlijst). Types: `kiemkeuze`, `vrije_beschrijving`, `taak`.
- Verplichte velden per type (uit spec §11-tabel):
  - kiemkeuze: `profiel` + `doel`
  - vrije_beschrijving: `einddoel` + `omgeving` (lokaal/VPS) + `slaag_criterium`
  - taak: `bewijs` (§4-schema) — een taak zonder bewijs-check is ongeldig en bestaat niet
- Weigeringsteksten: de twee vaste teksten uit §11 (bui/tuinier-formulering), plus per type de concrete drie vragen.
- Vragenlijst: vast JSON-formaat (§11.3) met per vraag `vraag` + `opties`, laatste optie altijd "iets anders (beschrijf)".

- [ ] **Step 1: Falende tests** — vage invoer geweigerd zonder uitvoering; complete invoer → concept + `wacht_op_mens`; taak zonder bewijsveld bestaat niet; vragenlijst-schema klopt.
- [ ] **Step 2: Run — falen**
- [ ] **Step 3: Bouw `growkit_poort.py`** — pure functies, geen interpretatie: alleen veldaanwezigheid en -vorm. De poort beoordeelt niet of een opdracht "goed" is — alleen of de verplichte structuur er is (spec-les).
- [ ] **Step 4: Aansluiten in seed.py** — `--vrij` loopt eerst door de poort; geweigerd → weigeringstekst + vragenlijst geprint, exit 1, niets uitgevoerd; geaccepteerd → concept-opdracht getoond + append-only gelogd + "klopt dit?"-bevestiging (één mens-moment, §11.1) vóór iets plant.
- [ ] **Step 5: Run — alle tests groen**
- [ ] **Step 6: Commit** — `feat: Scope-poort — weigering met vragen i.p.v. raden; concept pas na mens`

---

## Task 4: Test 1 uitvoeren — de schone-pleg-plant (geautomatiseerd)

**Files:** Create `tests/e2e_test1_schoon.sh`

- [ ] **Step 1: Schrijf het script** — kloont de repo (lokaal via `git clone <repo-pad>` in tmp, neemt dus niet de werkkopie), draait seed.py in de kloon, en controleert alle 7 criteria uit het protocol (task 1) geautomatiseerd, inclusief de "geen schrijfactie buiten doelmap"-check en de herstart-check.
- [ ] **Step 2: Run — verwacht groen.** Faalt iets, dan eerst het criterium laten zien (geen half bewijs), dan pas fixen met een aparte commit.
- [ ] **Step 3: Bewijs vastleggen** — draai-uitvoer in `docs/superpowers/bewijs/fase-2-test1.md` (append-only).
- [ ] **Step 4: Commit** — `test: Test 1 — schone-pleg-plant bewezen (7/7 criteria)`

---

## Task 5: Test 2 uitvoeren — de poort in de praktijk

**Files:** Create `tests/e2e_test2_poort.sh`

- [ ] **Step 1: Schrijf het script** — voert een echte vage beschrijving in ("maak me iets om m'n notities te ordenen of zo") en controleert alle 5 criteria: weigering zónder uitvoering, juiste vragen, complete-invoer-pad eindigt in wacht_op_mens, logging append-only, weigeringsteksten conform.
- [ ] **Step 2: Run — groen; bewijs vastleggen** in `docs/superpowers/bewijs/fase-2-test2.md`
- [ ] **Step 3: Commit** — `test: Test 2 — poort weigert ruis en vraagt scherp (5/5 criteria)`

---

## Task 6: Afsluiting — zelfreview en mijlpaal

- [ ] **Step 1: Zelfreview-checklist** (onderaan dit document) doorlopen; open punt §12.3 (ssh-configuratie per profiel) en §12.5 (reviewer-configuratie) expliciet doorgestuurd naar fase 3-planning.
- [ ] **Step 2: Mijlpaal-digest** naar de Agent-Brain inbox via brain_digest (VOORSTEL, mens curateert).
- [ ] **Step 3: Commit** — `docs: fase 2 af — kieming bewezen (Test 1 + 2)`

---

## Zelfreview-checklist (voor de executor)

1. **Spec-dekking:** §5 (leesroute, task 2), §11 (poort + formulier, task 3), §11.1-mens-moment (in task 3-4 verankerd), §12-punten 1, 4 en 6 (taken 1–3). Bewust níet in fase 2: slijper-schuring zelf, reviewer-rol, harnas, oerwoud.
2. **Honest-beweis:** elk criterium in de tabellen is gemeten door een script-assertion, niet door executor-inspectie; faalt een check, dan wordt de faal-uitvoer bewaard en gecommit — nooit stil aangepast.
3. **Type-consistentie:** `beoordeel_invoer()`-uitvoer == seed.py-gebruik; vragenlijst-JSON == §11.3-voorbeeldvorm; logboek-entries == fase-1-formaat (append-only, zelfde velden).
4. **Bekende valkuilen:** (a) clone-test mag niet per ongeluk de werkkopie gebruiken — clone-pad geforceerd tmp; (b) poort mag nooit tekst gaan interpreteren — alleen veldaanwezigheid; (c) herstart-test (1.6) haalt de niet-idempotente stap **dynamisch uit profiel.json** (zoek de eerste `"idempotent": false`) — nooit een hardcoded stapnummer, anders test je na een profielwijziging de verkeerde stap; (d) weigeringsteksten zijn vaste constanten, geen gegenereerde zinnen — anders is de tekst-vergelijkingstest nep.
