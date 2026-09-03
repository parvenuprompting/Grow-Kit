# GrowKit 🌱

[![Visibility](https://img.shields.io/badge/visibility-private-red)]()
[![Status](https://img.shields.io/badge/status-fase_1_–_5_bewezen-brightgreen?style=flat-square)]()
[![Taal](https://img.shields.io/badge/inhoud-Nederlands-blue?style=flat-square)]()
[![Dependencies](https://img.shields.io/badge/dependencies-geen_(stdlib_only)-success?style=flat-square)]()
[![Tests](https://img.shields.io/badge/tests-171_unit_+_6_E2E_groen-success?style=flat-square)]()

> **Het eerste zaadje dat jij controleert — niet de agent.**
> Een repo die na installatie vanzelf ontkiemt: jouw AI-agent leest de geboortebrief, jij kiest de boom, de agent plant mét machine-geverifieerd bewijs, en daarna groeit het door — met een eigen harnas dat zonder AI-agent draait, en een oerwoud van bomen onder één gedeeld brein.

## Wat het is

GrowKit is een **zelfstandig product**: een repo ("zaadje") die een AI-agent samen met de gebruiker tot leven brengt. De gebruiker plant met één actie; de agent leest de geboortebrief (`SEED.md`), laat de gebruiker via een klikbaar formulier kiezen wat er moet groeien, voert een vast stappenplan uit — en bewijst elke stap machinaal. Niets wordt uitgevoerd zonder bewijs, niets wordt definitief zonder bevestiging.

GrowKit gaat er vanuit dat de AI fouten kan maken — **zero-trust**. De interpretatie van "is het gelukt?" ligt nooit bij het model, maar bij een deterministische controlelaag die de AI niet kan omzeilen. De AI is de tuinier; de mens is de curator.

Geïnspireerd op de bewezen vorm van een tweede brein (agent leest en stelt voor, mens keurt goed, alleen toevoegen nooit overschrijven) — maar volledig generiek: GrowKit schrijft nooit terug naar bestaande systemen van de gebruiker.

**De invoerketen** (hoe een "domme prompt" alsnog een boom wordt):

```
Vage prompt → Scope-poort (structuurcheck, weigering bij vage invoer)
           → Prompt-slijper (schuurt tot concept; gelabelde standaardwaarden; mens keurt)
           → Vragenformulier (opties uit catalogus, omgevingsdetectie & je eigen brein)
           → Mijlpaal-bevestiging (samenvatting + akkoord vóór definitief)
           → Stappenplan met machine-bewijs → de boom groeit
           → Geboorteregistratie in het oerwoud → het brein wordt voller
```

## Naam van de techniek

De techniek waarmee de repo (de reeks Python-scripts) een stukje software autonoom helpt uitbouwen van zaadje tot boom heet het **GrowKit Grow Protocol** (NL: **Groeikit Groei Protocol**).

## De vijf fases — allemaal bewezen

Elke fase bewees iets voordat de volgende begon. Er is niks "nog af te maken" aan het fundament:

| Fase | Naam | Bewezen met | Uitslag |
|---|---|---|---|
| 1 | **Stappenplan** | Echte profielen, uitgevoerd via je bestaande agent | 16 tests + rooktest |
| 2 | **Kieming** | Machine-bewijs + leesroute-afdwinging | Test 1: 7/7 · Test 2: 5/5 |
| 3 | **Review-laag** | `reviewer`-rol (provider-agnostisch) vóór het mens-moment; ratificatie i.p.v. storing | Test 3: 5/5 |
| 4 | **Eigen harnas** | `loop.py` draait zonder AI-agent — inclusief `kill -9`-crash en herstart uit het logboek | Test 4: 6/6 |
| 5 | **Oerwoud** | Boom-register, VOORSTEL-doorstroom, vliegwiel onder één gedeeld brein | Test 5: 6/6 |

## Hoe het werkt — de kern in drie wetten

1. **Niets draait zonder bevestigde scope.** De Scope-poort weigert vage invoer met vaste weigeringsteksten; wat de poort niet vrijgeeft, kan de agent niet uitvoeren.
2. **Succes is bewijs, nooit een claim.** Vijf gecodeerde checktypes (`shell_check`, `file_exists`, `json_valid`, `file_equals`, `http_check`) worden door de motor zelf uitgevoerd — met SHA256-vergelijkingen tegen sjablonen.
3. **De geschiedenis is append-only.** Er wordt nooit overschreven of teruggedraaid; afkeuring leidt tot nieuwe status-entries, nooit tot mutatie van het verleden.

De volledige uitleg — gewone mens én techneut — staat in **[`docs/HOE-HET-WERKT.md`](docs/HOE-HET-WERKT.md)**. De visuele rondleiding: `docs/mockups/growkit-ui-v1.html` (mockup) en `docs/mockups/growkit-uitleg-v1.html` (uitleg).

## Werking — de stukken en hun rol

| Stuk | Rol |
|---|---|
| `SEED.md` | Geboortebrief: rol, regels en leesroute voor de geleende agent. |
| `seed.py` | Plant-mechanisme: kiemkeuze, vrije beschrijving, slijper-logboek, motor. |
| `loop.py` | Het harnas: vijf modi — planten, hervatten, taak, ratificatie, status. Draait zonder AI-agent. |
| `kern/growkit_poort.py` | Scope-poort: weigeringen, vragenlijst, gelabelde standaardwaarden. Interpreteert nooit inhoud. |
| `kern/growkit_motor.py` | Stappen-motor: bewijs of mens; faalcontract (één alternatief, dan stop). |
| `kern/growkit_bewijs.py` | De vijf machine-controles — code, niet interpretatie. |
| `kern/growkit_review.py` | Review-laag: rollen via `reviewconfig.json`; stdin + `shell=False`; twijfel = mens. |
| `kern/growkit_leesroute.py` | Per-fase content-injectie: wat de agent niet krijgt, kan hij niet lezen. |
| `kern/growkit_hervat.py` | Crash-herstel: reconstructie uit het logboek; niet-idempotent nooit herdraaid. |
| `kern/growkit_taken.py` | Takenlijst van de groeilaag: taken bestaan alleen mét bewijs. |
| `kern/growkit_oerwoud.py` | Geboortebewijs, boom-register, VOORSTEL-doorstroom, brein-opties. |
| `profielen/` | De bomen: JSON-stappenplannen met gecodeerd bewijs + sjablonen. |
| `groei/` | Groeilaag-documentatie (`SETUP.md`) en het slijper-logboek. |

## Het Oerwoud — één brein, vele bomen

Fase 5 maakt van één boom een ecosysteem (spec §13):

- **Geboortebewijs volwaardig** — elke boom krijgt bij het planten echte feiten: boom-id (uuid), machine, locatie, tijdstip.
- **Boom-register** — de eerste `tweede-brein`-boom wordt het *brein*; elke nieuwgeboren boom meldt zich append-only aan in `register/bomen.json`. Deregistreren = vervolg-entry, nooit verwijderen.
- **VOORSTEL-doorstroom** — gemarkeerde bestanden (`VOORSTEL-*`) reizen append-only naar de brein-inbox, met boom-id-prefix. De drift-guard is hard: logboeken, paden, ssh-doele en sleutels reizen **nooit**.
- **Vliegwiel (§11.2)** — het brein voedt de formulieren alleen-lezen: projectnamen verschijnen als "uit je brein"-opties. Hoe voller het brein, hoe persoonlijker de keuzes.
- **Herstel is een eersteklas burger** — crash? `loop.py` leest het logboek, slaat geslaagde stappen over (niet-idempotent: nooit herdraaid) en pakt de restdraai op vanaf de laatste bevestigde mijlpaal.

## Structuur

```
growkit/
├── SEED.md                  ← geboortebrief
├── seed.py                  ← plant-mechanisme (geleende agent-modus)
├── loop.py                  ← het harnas: orchestratie zonder agent (fase 4)
├── kern/                    ← motor, bewijs, poort, review, leesroute,
│                              hervat, taken, oerwoud
├── profielen/
│   ├── INDEX.md             ← kiemkeuze-catalogus
│   ├── tweede-brein/        ← bewezen profiel (5 kernmappen) — de brein-boom
│   ├── autonome-fabriek/    ← in ontwikkeling (de "nachtfabriek")
│   └── dev-werkplaats/      ← in ontwikkeling
├── groei/                   ← groeilaag-instructie (SETUP.md)
├── tests/                   ← 171 unit-tests + 6 E2E-scripts
├── reviewconfig.voorbeeld.json  ← rollen zonder leveranciers (§12.5)
├── docs/
│   ├── HOE-HET-WERKT.md     ← de complete, correcte uitleg
│   ├── superpowers/specs/   ← ontwerpdocument (bron van waarheid, v10)
│   ├── superpowers/plans/   ← implementatieplannen fase 1-5
│   ├── superpowers/bewijs/  ← zelfreviews + E2E-bewijzen per fase
│   ├── research/            ← Hermes-harnas-analyse
│   └── mockups/             ← UI-mockup + uitlegpagina (Editorial Monochrome)
└── README.md
```

## Quickstart

```bash
git clone <repo-url>
cd growkit
python3.11+ seed.py            # geleende-agent-modus: kiemkeuze + planten
python3.11+ loop.py            # het harnas: planten / hervatten / taak / ratificatie / status
```

- Plant je tweede boom, dan vraagt de loop waar je brein groeit — of maakt van de eerste boom automatisch het brein.
- Review-rollen (optioneel): kopieer `reviewconfig.voorbeeld.json` naar `reviewconfig.json` (staat in `.gitignore` — per-machine) en map de rol `reviewer` naar jouw eigen endpoint.

Verder lezen (in volgorde): `SEED.md` → `profielen/INDEX.md` → **`docs/HOE-HET-WERKT.md`** → ontwerpdoc `docs/superpowers/specs/2026-09-03-growkit-design.md`.

## Tests en bewijs

- **171 unit-tests** (unittest, stdlib) + **6 end-to-end-scripts** — allemaal groen, alle draaien in ~2 seconden.
- Bewijs per fase, letterlijk vastgelegd: `docs/superpowers/bewijs/` (fase-2-test1/2, fase-3-test3, fase-4-test4, fase-5-test5 + zelfreviews).
- Test 4 bewijst de agent-onafhankelijkheid: het harnas plant, crasht (`kill -9`), hervat uit het logboek en ratificeert — met alleen python3 en gepijpte antwoorden.
- Test 5 bewijst het oerwoud: register, doorstroom, drift-guard en corrupt-register-afhandeling op een schone plek.

## Ontstaan

Het idee bleek ouder dan deze repo: het leefde al in notities en concept-documenten (PECL — Persistent External Context Layer, en het "AI Scratchpad"-productconcept) vóórdat het werd gebouwd als persoonlijk tweede brein, en nu is het terug als zelfstandig, generiek product. Meer daarover in de logboeken.

## Status

- **Fase 1-5 bewezen** (3 september 2026). Zelfreviews met letterlijke evidence: `docs/superpowers/bewijs/fase-4-zelfreview.md` en `fase-5-zelfreview.md`.
- **Volgende stappen** (voorstellen, nog niet afgesproken): fase 5.1 (cross-machine sync via git — eigen bewijsronde), de nachtfabriek (autonome-fabriek-profiel binnen de bewezen kaders), of de eerste echte gebruiker (distributie-beslissing: git-kloon vs. PyPI — naamcheck §2 herhalen bij een PyPI-release).
- Repo privé opzettelijk (ontwerpfase); openbaarmeming wordt een bewuste beslissing.
