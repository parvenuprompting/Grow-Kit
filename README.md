# GrowKit 🌱

[![Visibility](https://img.shields.io/badge/visibility-private-red)]()
[![Status](https://img.shields.io/badge/status-fase_1_ontwerp-brightgreen?style=flat-square)]()
[![Taal](https://img.shields.io/badge/inhoud-Nederlands-blue?style=flat-square)]()
[![Dependencies](https://img.shields.io/badge/dependencies-geen_(stdlib_only)-success?style=flat-square)]()

> **Het eerste zaadje dat jij controleert — niet de agent.**
> Een repo die na installatie vanzelf ontkiemt: jouw AI-agent leest de geboortebrief, jij kiest de boom, de agent plant mét machine-geverifieerd bewijs, en daarna groeit het door — zelfvoorzienend, zelflerend, zelfcorrigerend.

## Wat het is

GrowKit is een **zelfstandig product**: een repo ("zaadje") die een AI-agent samen met de gebruiker tot leven brengt. De gebruiker plant met één actie; de agent leest de geboortebrief (`SEED.md`), laat de gebruiker via een klikbaar formulier kiezen wat er moet groeien, voert een vast stappenplan uit — en bewijst elke stap machinaal. Niets wordt uitgevoerd zonder bewijs, niets wordt definitief zonder bevestiging.

Geïnspireerd op de bewezen vorm van een tweede brein (agent leest en stelt voor, mens keurt goed, alleen toevoegen nooit overschrijven) — maar volledig generiek: GrowKit schrijft nooit terug naar bestaande systemen van de gebruiker.

**De invoerketen** (hoe een "domme prompt" alsnog een boom wordt):

```
Vage prompt → Scope-poort (structuurcheck)
           → Prompt-slijper (schuurt tot concept-opdracht; mens keurt)
           → Vragenformulier (opties uit catalogus, omgeving & je eigen brein)
           → Mijlpaal-bevestiging (samenvatting + akkoord vóór definitief)
           → Stappenplan met machine-bewijs → de boom groeit
```

## Naam van de techniek

De techniek waarmee de repo (de reeks Python-scripts) een stukje software autonoom helpt uitbouwen van zaadje tot boom heet het **GrowKit Grow Protocol** (NL: **Groeikit Groei Protocol**).

## Werking

- **SEED.md** — de geboortebrief: het eerste wat de agent leest. Rol, regels, leesroute.
- **seed.py** — het plant-mechanisme: kiemkeuze, stappen-motor, bewijscontroles.
- **profielen/** — de bomen: JSON-stappenplannen met gecodeerde bewijsvoorwaarden en sjabloonbestanden (geen heredocs, geen vrije-tekst-bewijzen).
- **groei/** — de levenslange laag na de installatie: append-only logboek, takenlijst, inzichten-inbox (VOORSTEL-status; de mens curateert).

**De vijf bewijstypes** (altijd gecodeerd, uitgevoerd door seed.py zelf — de agent claimt nooit zelf succes): `shell_check` · `http_check` · `file_exists` · `json_valid` · `file_equals`.

## Structuur

```
growkit/
├── SEED.md                  ← geboortebrief (fase 1)
├── seed.py                  ← plant-mechanisme (fase 1-2)
├── growkit_bewijs.py        ← de vijf machine-bewijscontroles
├── growkit_motor.py         ← stappen-motor: bewijs of mens
├── profielen/
│   ├── INDEX.md             ← kiemkeuze-catalogus
│   ├── tweede-brein/        ← eerste bewezen profiel (5 kernmappen)
│   ├── autonome-fabriek/    ← in ontwikkeling
│   └── dev-werkplaats/      ← in ontwikkeling
├── groei/                   ← groeilaag-instructie (SETUP.md)
├── tests/                   ← unit + E2E-bewijzen
└── docs/
    ├── superpowers/specs/   ← ontwerpdocument (bron van waarheid)
    ├── superpowers/plans/   ← implementatieplannen per fase
    ├── research/            ← Hermes-harnas-analyse
    └── mockups/             ← UI-mockups (Editorial Monochrome)
```

## Roadmap — de groeifases

Elke fase bewijst iets voordat de volgende begint. Het eigen harnas wordt pas gebouwd nadat fase 2 is bewezen.

| Fase | Naam | Wat | Bewijst |
|---|---|---|---|
| 1 | **Stappenplan** | Echte profielen, uitgevoerd via je bestaande agent (feature, geen noodoplossing) | Dat het stappenplan-formaat werkt |
| 2 | **Kieming** | seed.py machine-bewijs + Test 1 (schone plek) + Test 2 (vrije beschrijving) | Dat bewijs-afdwinging werkt |
| 3 | **Review-laag** | `reviewer`-rol (provider-agnostisch) voor mens-verificatie-stappen | Dat de mens minder vaak nodig is |
| 4 | **Eigen harnas** | Dunne provider-agnostische orchestratieloop — pas na fase 2 | Dat GrowKit zonder agent-dependency bestaat |
| 5 | **Oerwoud** 🌳 | Meerdere bomen registreren bij één gedeeld brein; sync via dat ene brein | Dat één brein het centrum van een ecosysteem is |

## Quickstart

```bash
git clone <repo-url>
cd growkit
python3 seed.py            # interactieve kiemkeuze — welke boom, welke plek?
```

Verder lezen (in volgorde): `SEED.md` → `profielen/INDEX.md` → ontwerpdoc `docs/superpowers/specs/2026-09-03-growkit-design.md`.

## Ontstaan

Het idee bleek ouder dan deze repo: het leefde al in notities en concept-documenten (PECL — Persistent External Context Layer, en het "AI Scratchpad"-productconcept) vóórdat het werd gebouwd als persoonlijk tweede brein, en nu is het terug als zelfstandig, generiek product. Meer daarover in de logboeken.

## Status

- **Fase 1, taak 1-9 gepland** — implementatieplan: `docs/superpowers/plans/2026-09-03-growkit-fase-1.md`.
- Repo privé opzettelijk (ontwerpfase); openbaarmeming wordt een bewuste beslissing.
