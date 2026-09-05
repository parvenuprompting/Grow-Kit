# Grow Kit 🌳

[![Visibility](https://img.shields.io/badge/visibility-private-red)]()
[![Status](https://img.shields.io/badge/status-vlaggenschip_·_v1.3.1_huis_bewezen-brightgreen?style=flat-square)]()
[![Taal](https://img.shields.io/badge/inhoud-Nederlands-blue?style=flat-square)]()
[![Dependencies](https://img.shields.io/badge/dependencies-geen_(stdlib_only)-success?style=flat-square)]()
[![Tests](https://img.shields.io/badge/tests-434_groen-success?style=flat-square)]()

> **Het eerste zaadje dat jij controleert — niet de agent.**
> En inmiddels veel meer dan een zaadje: Grow Kit is een **huis**. Een native macOS-app waarin een hele agent-familie woont, werkt en groeit — met machine-bewijs voor elke stap, een gouverneur die grenzen afdwingt, en de mens met de laatste stem.

![Thuis — de landingspagina](docs/screenshots/thuis.png)
*Thuis — de landingspagina: welkom, mini-dashboard (familie, saldo, harnas, geschiedenis) en de Knowledge Graph van het brein.*

## Wat het is

Grow Kit is een **zelfstandig product**: een repo ("zaadje") die een AI-agent samen met de gebruiker tot leven brengt. De gebruiker plant met één actie; de agent leest de geboortebrief (`SEED.md`), laat de gebruiker via een klikbaar formulier kiezen wat er moet groeien, voert een vast stappenplan uit — en bewijst elke stap machinaal. Niets wordt uitgevoerd zonder bewijs, niets wordt definitief zonder bevestiging.

Grow Kit gaat er vanuit dat de AI fouten kan maken — **zero-trust**. De interpretatie van "is het gelukt?" ligt nooit bij het model, maar bij een deterministische controlelaag die de AI niet kan omzeilen. De AI is de tuinier; de mens is de curator.

Geïnspireerd op de bewezen vorm van een tweede brein (agent leest en stelt voor, mens keurt goed, alleen toevoegen nooit overschrijven) — maar volledig generiek: Grow Kit schrijft nooit terug naar bestaande systemen van de gebruiker.

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

## De zes fases — allemaal bewezen

Elke fase bewees iets voordat de volgende begon. Er is niks "nog af te maken" aan het fundament:

| Fase | Naam | Bewezen met | Uitslag |
|---|---|---|---|
| 1 | **Stappenplan** | Echte profielen, uitgevoerd via je bestaande agent | 16 tests + rooktest |
| 2 | **Kieming** | Machine-bewijs + leesroute-afdwinging | Test 1: 7/7 · Test 2: 5/5 |
| 3 | **Review-laag** | `reviewer`-rol (provider-agnostisch) vóór het mens-moment; ratificatie i.p.v. storing | Test 3: 5/5 |
| 4 | **Eigen harnas** | `loop.py` draait zonder AI-agent — inclusief `kill -9`-crash en herstart uit het logboek | Test 4: 6/6 |
| 5 | **Oerwoud** | Boom-register, VOORSTEL-doorstroom, vliegwiel onder één gedeeld brein | Test 5: 6/6 |
| 6 | **De app** | Native macOS-app via JSON-adapter — bedienaar, geen machthebber; crash- en poort-contract bewezen | Test 6: groen |

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
| `adapter.py` | Machine-leesbare JSON-CLI over de kern — de brug voor de app. 37 commando's, bedienaar geen machthebber. |
| `app/` | Native macOS-app (SwiftUI, XcodeGen) in de editorial-monochrome huisstijl — 18 schermen + zijmenu. |
| `kern/` | **28 modules** — het volledige fundament (zie overzicht hieronder). |
| `profielen/` | De bomen: JSON-stappenplannen met gecodeerd bewijs + sjablonen. |
| `groei/` | Groeilaag-documentatie (`SETUP.md`) en het slijper-logboek. |

### De 28 kernmodules

| Module | Rol |
|---|---|
| `growkit_poort.py` | Scope-poort: weigeringen, vragenlijst, gelabelde standaardwaarden. |
| `growkit_motor.py` | Stappen-motor: bewijs of mens; faalcontract (één alternatief, dan stop). |
| `growkit_bewijs.py` | Vijf machine-controles — code, niet interpretatie. |
| `growkit_review.py` | Review-laag: rollen via `reviewconfig.json`; stdin + `shell=False`. |
| `growkit_ratificatie.py` | Bulk-ratificatie-logica — één bron voor loop.py en de adapter. |
| `growkit_leesroute.py` | Per-fase content-injectie: wat de agent niet krijgt, leest hij niet. |
| `growkit_hervat.py` | Crash-herstel: reconstructie uit het logboek. |
| `growkit_taken.py` | Takenlijst van de groeilaag. |
| `growkit_oerwoud.py` | Geboortebewijs, boom-register, voorstellen-doorstroom, brein-opties. |
| `growkit_vangnet.py` | Review-aanroepen en stap-uitkomsten in SQLite per boom. |
| `growkit_familie.py` | Parvenu Agent Family: 7 agents met rol en live-status. |
| `growkit_agents.py` | Agent-instanties en roster-beheer. |
| `growkit_agentstatus.py` | Live statuspolling per agent (VPS). |
| `growkit_agentcontrole.py` | Controle & goedkeuring: afgeronde taken → mens-moment. |
| `growkit_agenttaak.py` | Taak-koppeling: Mac → VPS agent-wachtrij. |
| `growkit_agentchat.py` | Agent Chat: bericht=taak, bron=agentchat, draad-koppeling. |
| `growkit_goedkeuring.py` | Bulk-goedkeuringslogica met audit-spoor. |
| `growkit_contract.py` | Taak-contract: zes Automatiek-bouwblokken, secrets-scanner. |
| `growkit_pts.py` | PTS-slot: SHA256-manifest, gewijzigde test blokkeert goedkeuring. |
| `growkit_observaties.py` | Voorstellen uit de brein-inbox, alleen-lezen in beeld. |
| `growkit_graaf.py` | Knowledge Graph: brein-verbanden als platte-tekst graaf. |
| `growkit_prompts.py` | Prompt-bibliotheek: 125 gecureerde prompts, 26 domeinen, filters. |
| `growkit_profiel.py` | Profiel-sjablonen en -opties voor de plant-wizard. |
| `growkit_hervatvlag.py` | Wizard-hervatvlag: generieke kieming + Tailscale. |
| `growkit_verbind.py` | SSH-verbinding naar VPS (omleidbaar via `GROWKIT_HOST`). |
| `growkit_openrouter.py` | OpenRouter-saldo: live uitlezen, rood onder €10. |
| `data/` | Prompt-bibliotheek-JSON + andere statische bestanden. |

## Het huis — het vlaggenschip-tijdperk (5 september 2026)

Sinds 5 september is Grow Kit het vlaggenschip: het huis waarin de **Parvenu Agent Family** (7 Telegram-agents) verhuist van de groepschat naar een eigen, ontworpen omgeving. Alles wat daarvoor losse projecten waren, wordt één voor één ingebouwd.

**Wat er nu in het huis woont:**

| Onderdeel | Wat het doet |
|---|---|
| **Familie-register** | 7 agents met rol en LIVE-status, rechtstreeks van de VPS |
| **Gouverneur** | max 2 taken/agent, 8 agents, controle vóór vrijlating |
| **Taak-koppeling** | taken van de app naar de VPS-agent-wachtrij |
| **Taak-contract** | zes Automatiek-bouwblokken; secrets-scanner weigert keys |
| **PTS-slot** | SHA256-manifest; gewijzigde test blokkeert goedkeuring |
| **Controle & goedkeuring** | afgeronde taken → mens-moment → goedgekeurd/afgekeurd |
| **Observaties** | voorstellen uit de brein-inbox, alleen-lezen |
| **Agent Chat** | live chat met VPS-agents — bericht=taak, draad-koppeling |
| **Knowledge Graph** | brein-verbanden als platte-tekst graaf, tabs per sectie |
| **Prompt-bibliotheek** | 125 gecureerde prompts, 26 domeinen, variabelen invullen en kopiëren |
| **Saldo** | OpenRouter-saldo live in het zijmenu (rood onder €10) |
| **Geheugen-geboorte** | onboarding als eerste ratificatie, append-only profiel |
| **Landingspagina** | rustige Home met mini-dashboard |
| **Statusbalk** | lokale tijd, datum, weer (Open-Meteo) in het zijmenu |
| **Laadscherm** | 2s animatie bij opstart, geen vensterdans |

**Ingebouwde projecten:** Parvenu Test Harnas (bewijs-slot), Saldo (saldo-kern), Automatiek (taak-contract).

**De vijf mock-schermen** tonen de visie voor wat komt: Skills (met evals-per-stap), Browser, IDE, Connectors, Handleiding.

Fase 5 maakt van één boom een ecosysteem (spec §13):

- **Geboortebewijs volwaardig** — elke boom krijgt echte feiten: boom-id (uuid), machine, locatie, tijdstip.
- **Boom-register** — de eerste `tweede-brein`-boom wordt het *brein*; elke nieuwe boom meldt zich append-only aan.
- **VOORSTEL-doorstroom** — gemarkeerde bestanden reizen append-only naar de brein-inbox. De drift-guard is hard: logboeken, paden, ssh-doelen en sleutels reizen **nooit**.
- **Vliegwiel (§11.2)** — het brein voedt de formulieren alleen-lezen: hoe voller het brein, hoe persoonlijker de keuzes.
- **Herstel is een eersteklas burger** — crash? `loop.py` leest het logboek, slaat geslaagde stappen over en pakt de restdraai op.

## De app — navigatie

Het zijmenu (editorial monochrome, versie 1.3.1). **Agent Chat is bewust 01 — direct na Thuis — als hoofdfunctie van het huis:**

```
00  Thuis              — landingspagina met mini-dashboard
    WERK
01  Agent Chat         — praat met de familie; bericht = taak via de wachtrij
02  Status             — identiteit, register, tellers, logboek
03  Planten            — profiel kiezen → concept → motor met bewijs
04  Goedkeuringen      — ratificatie: mens keurt goed of wijst af met reden
05  Dialoog            — AI — scope-poort, prompt-slijper, ronde tafel
06  Agenten            — agent-roster, taak-contract, gouverneur
07  Knowledge Graph    — brein-verbanden, tabs per sectie, platte tekst
08  Prompts            — gecureerde bibliotheek, variabelen invullen
09  Vangnet            — opgevangen review-aanroepen en stap-uitkomsten
10  Audit              — volledig logboek, append-only
    SYSTEEM
11  Hervatten          — crash-herstel: reconstructie uit het logboek
12  Taak               — boom-pad + governor → takenlijst met bewijs
    LEREN
13  Rondleiding        — de vijf schermen van het ontwerp
14  Uitleg             — zes regels · de engine room
```

### Rondleiding — van vage prompt tot geplante boom

![Rondleiding — de groeiketen](docs/screenshots/rondleiding.png)
*Rondleiding (13): de vijf schermen van het ontwerp — hier stap 1 (Kiemkeuze) en 2 (Schuring), met het vragenformulier dat opties aanbiedt in plaats van invulvelden.*

### Planten — de scope-poort in drie vragen

![Planten — scope-poort](docs/screenshots/planten.png)
*Planten (03): kiemkeuze, doelmap en oerwoud-registratie in één scherm; elke keuze wordt bevestigd en elk resultaat machine-gecontroleerd.*

### Prompts — de gecureerde bibliotheek

![Prompts — gecureerde bibliotheek](docs/screenshots/prompts.png)
*Prompts (08): 125 gecureerde audit-prompts uit de privé-bibliotheek — zoeken, filteren op domein, variabelen invullen en de prompt letterlijk kopiëren naar je agent.*

## Structuur

```
growkit/
├── SEED.md                  ← geboortebrief
├── seed.py                  ← plant-mechanisme (geleende agent-modus)
├── loop.py                  ← het harnas: orchestratie zonder agent
├── adapter.py               ← JSON-CLI brug (37 commando's)
├── kern/                    ← 28 modules (zie tabel hierboven)
├── profielen/
│   ├── INDEX.md             ← kiemkeuze-catalogus
│   ├── tweede-brein/        ← bewezen profiel (5 kernmappen)
│   ├── autonome-fabriek/    ← de "nachtfabriek"
│   └── dev-werkplaats/      ← in ontwikkeling
├── groei/                   ← groeilaag-instructie (SETUP.md)
├── tests/                   ← 434 tests groen + 13 E2E-scripts
├── reviewconfig.voorbeeld.json  ← rollen zonder leveranciers (§12.5)
├── app/
│   ├── Sources/             ← 18 SwiftUI-views + Thema/Bouwstenen
│   ├── Resources/           ← app-icoon (groene G met blaadjes)
│   ├── Fonts/               ← Fraunces + Inter (editorial monochrome)
│   ├── build.sh             ← xcodegen + xcodebuild (bewijsbare build)
│   └── project.yml          ← XcodeGen-specificatie
├── docs/
│   ├── HOE-HET-WERKT.md     ← de complete uitleg
│   ├── screenshots/         ← app-screenshots (Thuis, Planten, Prompts, Rondleiding)
│   ├── superpowers/specs/   ← ontwerpdocument (bron van waarheid)
│   ├── superpowers/plans/   ← implementatieplannen fase 1-5
│   ├── superpowers/bewijs/  ← zelfreviews + E2E-bewijzen per fase
│   ├── research/            ← Hermes-harnas-analyse
│   └── mockups/             ← UI-mockup + uitlegpagina
└── README.md
```

## Quickstart

```bash
git clone <repo-url>
cd growkit
python3 seed.py            # geleende-agent-modus: kiemkeuze + planten
python3 loop.py            # het harnas: planten / hervatten / taak / ratificatie / status

# de macOS-app bouwen en installeren:
(cd app && bash build.sh) && ditto app/.build/Build/Products/Debug/GrowKit.app /Applications/GrowKit.app
```

- Plant je tweede boom, dan vraagt de loop waar je brein groeit — of maakt van de eerste boom automatisch het brein.
- Review-rollen (optioneel): kopieer `reviewconfig.voorbeeld.json` naar `reviewconfig.json` (in `.gitignore`, per-machine).
- Verbinding met VPS: stel `GROWKIT_HOST` in om SSH te richten naar jouw machine.

Verder lezen: `SEED.md` → `profielen/INDEX.md` → **`docs/HOE-HET-WERKT.md`**.

## Tests en bewijs

- **434 tests groen** (unittest, stdlib) — volledige suite (5 september 2026).
- **13 end-to-end-scripts**: `e2e_test1_schoon.sh` t/m `e2e_test6_app.sh`, plus 7 slice-E2E-scripts voor de VPS-functies.
- Bewijs per fase: `docs/superpowers/bewijs/` (fase-2-test1/2, fase-3-test3, fase-4-test4, fase-5-test5 + zelfreviews).
- Test 4 bewijst agent-onafhankelijkheid: het harnas plant, crasht (`kill -9`), hervat uit het logboek en ratificeert — met alleen python3.
- Test 5 bewijst het oerwoud: register, doorstroom, drift-guard en corrupt-register-afhandeling op een schone plek.
- **Slice-bewijs (5 sept):** elke nieuwe slice TDD (eerst rood, dan groen); end-to-end tegen de echte VPS.

## Ontstaan

Het idee bleek ouder dan deze repo: het leefde al in notities en concept-documenten (PECL — Persistent External Context Layer, en het "AI Scratchpad"-productconcept) vóórdat het werd gebouwd als persoonlijk tweede brein, en nu is het terug als zelfstandig, generiek product. Meer daarover in de logboeken.

## Status

- **Fase 1-6 bewezen** (3-4 september 2026).
- **Het vlaggenschip-tijdperk (5 september 2026, v1.3.1):** de app is het huis van de Parvenu Agent Family. Familie-register met live VPS-status, gouverneur-loop in beeld, taak-contract met secrets-scanner, PTS-bewijs-slot, observaties uit de brein-inbox, saldo live, geheugen-geboorte, landingspagina en laadscherm. Drie losse projecten ingebouwd: Parvenu Test Harnas, Saldo, Automatiek.
- **Prompt-bibliotheek (5 september):** 125 gecureerde prompts uit de privé-auditbibliotheek, 26 domeinen, variabelen invullen en kopiëren.
- **Agent Chat live (5 september, bouw 13):** het grote chatvenster met de familie is geen mock meer — item 01 in het zijmenu, direct na Thuis, als hoofdfunctie. Bericht = taak via de bewezen wachtrij; de agent antwoordt met zijn eigen profiel; gouverneur en faalcontract blijven de bewakers.
- **Zijmenu gehernummereerd (5 september):** Agent Chat = 01 (bewust bovenaan, als hoofdfunctie), alle paginakoppen meeverplaatst (02 Status … 08 Prompts). Navigatie en koppen sluiten weer op elkaar aan.
- **Nieuwe identiteit (5 september):** groen logo (G met blaadjes), editorial-monochrome invoervelden met leesbare placeholders, app forceert lichte modus (titels blijven altijd zichtbaar).

**Op de plank (ontworpen, wacht op beurt):**
- Fase 4 inbouw: SecureVault + Amnesia
- PAC-inbouw: fabriek-tellers → Brain Index → Proof Coverage → Brain Graph
- Context-Rot bouwstenen: schema-dwang → hash-lock → tool-isolatie → context-cap → harde ratificatie
- Tailscale-bouwplan: 5 bouwstenen + read-only Gids-rol
- Profiel-sjabloon met research-lessen (evals-per-stap, herleidbare frontmatter, append-only JSONL)
- B-functies uit de mocks: Skills, Browser, IDE, Connectors, handleiding, extensie-builder
- Fase 5.1: cross-machine sync
- Packaging-beslissing

Repo privé opzettelijk (ontwerpfase); openbaarmeming wordt een bewuste beslissing.