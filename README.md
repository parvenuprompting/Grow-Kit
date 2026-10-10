# Grow Kit 🌳

[![CI](https://github.com/parvenuprompting/Grow-Kit/actions/workflows/ci.yml/badge.svg)](https://github.com/parvenuprompting/Grow-Kit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS_14%2B-black?style=flat-square)]()
[![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)]()
[![Tests](https://img.shields.io/badge/tests-799_in_CI-success?style=flat-square)]()
[![Agents](https://img.shields.io/badge/agent-familie-7_teal?style=flat-square)]()
[![Privacy](https://img.shields.io/badge/privacy-lokaal_eerst-success?style=flat-square)](#wat-verlaat-je-machine)
[![Made by](https://img.shields.io/badge/build_in_public-Ti%C3%ABndo-9cf?style=flat-square)]()
[![Encryption](https://img.shields.io/badge/secrets-AES--256_GCM-orange?style=flat-square)]()
[![X](https://img.shields.io/badge/X-@GrowKitHarnas-black?style=flat-square)](https://x.com/GrowKitHarnas)

**GROW** = **G**overned **R**eproducible **O**perational **W**orkflow — de wet waar elke stap onder draait.

> **Het zaadje dat jij controleert — niet de agent.**
> Een zero-trust AI-werkbank waarin elke stap machine-bewezen is, de mens het laatste woord heeft, en niets verdwijnt.

## Wat is Grow Kit?

Grow Kit is een **AI-werkbank met een harnas**. Je geeft een idee, een agent voert het uit, en de machine bewijst bij elke stap dat het klopt. Jij keurt goed of af. De agent mag nooit zeggen "klaar" — hij moet het bewijzen.

## De drie wetten

1. **Niets draait zonder bevestigde scope.** Wat de poort niet vrijgeeft, kan de agent niet uitvoeren.
2. **Succes is bewijs, nooit een praatje.** Vijf gecodeerde controles (`shell_check`, `file_exists`, `json_valid`, `file_equals`, `http_check`) worden door de motor zelf uitgevoerd.
3. **De geschiedenis is append-only.** Nooit overschrijven, nooit teruggedraaien. Het verleden blijft intact.

Volledige uitleg: **[`docs/HOE-HET-WERKT.md`](docs/HOE-HET-WERKT.md)**.

## Sponsorware 🌳

Grow Kit is MIT-opensource. De motor en de vijf bewijscontroles blijven altijd gratis. Wil je de groei steunen? Bekijk de [sponsor-tiers](SPONSORS.md) — van 🌱 Zaadje (€5/mnd) tot 🏛️ Boomgaard (€500/mnd).

## De app

Native macOS-app (SwiftUI) in editorial-monochrome stijl. De zijbalk begint met de
drie hoofdingangen — **00 Vandaag**, **01 Opdrachten**, **02 Bibliotheek** — en al
het gereedschap daaronder zit onder één uitklapper *Gereedschappen*.

| Nr. | Scherm | Wat het doet |
|---|---|---|
| 00 | **Vandaag** | Begroeting, de vier cijfers (familie, saldo, wacht op jou, geschiedenis) en de knowledge graph |
| 01 | **Opdrachten** | Eén dossier per opdracht: plan, grenzen, uitvoering, bewijs, jouw oordeel — met drie lokale voorbeelden |
| 02 | **Bibliotheek** | Gecureerde audit-prompts, letterlijk en alleen-lezen |
| **Gereedschappen** | | |
| 03 | Agent Chat | Praat met de familie; Thought-blok per antwoord, gesprek wissen (→archief), geschiedenis |
| 04 | Status | Identiteit, register, tellers, logboek |
| 05 | Planten | Kiemkeuze → concept → motor met bewijs |
| 06 | Goedkeuringen | Ratificatie: mens keurt goed of af |
| 07 | Dialoog | Scope-poort, prompt-slijper, ronde tafel |
| 08 | Agenten | Gouverneur: familie, observaties, taak-contracten |
| 09 | **Automatiek** | Eén zin in, automation-plan uit — KairOS stelt voor, jij keurt |
| 10 | Knowledge Graph | Brein-verbanden; klik op een sectie om in te zoeken |
| 11 | Vangnet | Opgevangen review-aanroepen en uitkomsten |
| 12 | Audit | Volledig, append-only logboek |
| 13 | Agenda | Cron, wachtende goedkeuringen en taken |
| 14 | Secure Vault | Echte kluizen via macOS hdiutil (AES-256/APFS) |
| 15 | Amnesia Protocol | Gevoelige tekst anonimiseren en herstellen |
| 16 | Digitale Kloon | Persoonlijke kluis: 6 categorieën, AES-256-GCM, PIN + Touch ID |
| 17 | Hervatten | Crash-herstel uit het logboek |
| 18 | Taak | Boom-pad + governor → takenlijst met bewijs |
| 19 | **Telegram Connect** | De familie koppelen aan jouw eigen Telegram, stap voor stap |
| 20 | **CyberSeed** | Zes niveaus (Sprout → Amazone), lokaal (Ollama) of frontier-cloud (OpenRouter), eigen SOUL |
| 21 | Skills | Welke skills draaien er op jouw GrowKit? |
| 25 | Rondleiding | Het ontwerp in vijf schermen |
| 26 | Uitleg | De motor uitgelegd |
| 27 | Best Practices | Kerninzichten uit eigen onderzoek, met zoeken |

Instellingen staat permanent onderaan de zijbalk. De nummers 22–24 zijn
voorbereide schermen (browser, IDE, connectors) die nog niet in het menu staan.

## De agent-familie

Zeven agents, elk met een eigen rol en stem. Ze sturen in plaats van mee-praten: behulpzaam altijd, meegaand nooit.

| Agent | Rol | Stem |
|---|---|---|
| **KairOS** | Bouwer & coördinator — de eerste agent, naamdrager van het toekomstige KairOS-OS | Kalm, degelijk; praat als een ervaren voorman |
| **Riri** | Research — onderzoek, ontwerp, externe review | Warm en scherp; noemt altijd haar bron |
| **Vigil** | Bewaking — infrastructuur, security, signalen | Alert en zakelijk; korte feitelijke meldingen |
| **Libra** | Kosten — budget, pricing, verbruik | Bedachtzaam en cijfergericht; noemt de euro's |
| **Memoria** | Geheugen — herinneringen, logboeken, overzicht | Vertellend; vindt data en dataprecies terug |
| **Codex** | Archief — brein-boekingen, documenten, orde | Ordelijk; genummerde samenvattingen |
| **Genius** | Observer — kijkt mee, levert aan, groeit in fasen | Stil observerend; zegt weinig, raakt wel |

De agents kennen de gebruiker bij naam (het `van`-veld in elk chatbericht) en spreken hem aan met zijn naam of "de Baas" — nooit anders. Hun gedrag staat in SOUL-bestanden op de eigen server: focus-manifest, antwoord-verdeling, titulatuur en per-agent stem.

## De techniek

Voor wie verder wil kijken:

- **Python-kern** (`kern/`, 54 modules): scope-poort, stappen-motor met faalcontract, vijf machine-controles, review-laag, ratificatie, leesroute, crash-herstel, boom-register, vangnet (SQLite), agent-familie, Knowledge Graph, prompt-bibliotheek, Secure Vault (hdiutil), Amnesia (anonimiseren), Digitale Kloon (AES-256-GCM via `cryptography` in een repo-eigen `.venv` — bewuste uitzondering op stdlib-only), Best Practices.
- **Adapter** (`adapter.py`): JSON-CLI met 74 commando's over de kern — de enige poort tussen app en motor.
- **Opdrachtdossier** (`kern/growkit_opdrachten.py`): één blijvend dossier per opdracht — bevestigd plan met `plan_hash`, uitvoerslot tegen dubbel draaien, wachtende mens-stappen, oordeel en PANIC-herstel. Transactionele opslag (`kern/growkit_opslag.py`: flock + atomair schrijven).
- **Pauze is geen fout** (`kern/growkit_motor.py`): `uitkomst()` benoemt wat een run deed (geslaagd · wacht_op_mens · gepauzeerd · gefaald) en `machine_deel_voltooid()` zegt of alleen nog jouw besluit openstaat. Een mens-moment levert exit 0 met status `wacht_op_mens`; een echt falen houdt exit 2.
- **Gegevensroute** (`kern/growkit_route.py`): leidt per plan af of er iets de machine verlaat (lokaal · eigen VPS · cloud). Een profiel mag het zelf verklaren; verklaart het minder dan zijn commando's doen, dan wint het zwaarste en verschijnt er een waarschuwing. Cloud vraagt om expliciete toestemming — zonder die toestemming start de opdracht niet.
- **Voorbeelden** (`kern/growkit_voorbeelden.py` + `profielen/`): drie lokale voorbeeldopdrachten (projectcontrole, documentenoverzicht, terugkerend rapport), elk met een eigen plan, sjablonen en een mens-stap. Eén bron: het profiel draagt zijn eigen voorbeeld-blok.
- **CyberSeed** (`kern/growkit_cyberseed.py` + `kern/growkit_ram.py`): zes modelniveaus — Sprout v0.5, Root v1.0, Leaf v1.5, Tree v2.0, Jungle v2.5, Amazone v3.0 — elk met een eigen systeemprompt op autonomie-schaal (governance in alle tiers). Per niveau kies je **lokaal** (Ollama, RAM-klasse bepaalt het model; te zware namen zijn vergrendeld met min-RAM-uitleg) of **cloud** (OpenRouter, frontier-opties per naam). Zelfbijgewerkte SOUL-snapshot uit GrowKit-data; routinglog per aanroep; chatlog append-only; wissen alleen met `bevestig=true`. Eigen OpenRouter-model per naam mogelijk mét tier-validatie (±1 niveau, `force=true` voor bewuste keuze). Lokaal is de eindbestemming — cloud is de brug. Niets verlaat de Mac bij lokaal.

### CyberSeed: de zes niveaus

| Niveau | Naam | Lokaal (24 GB Mac) | Cloud-opties (OpenRouter) |
|---|---|---|---|
| 1 | **Sprout v0.5** — instap, kort | qwen3:4b | gemini-3.5-flash · gpt-5.6-luna · glm-5.3-flash |
| 2 | **Root v1.0** — SOUL-bewust, suggereert | qwen3:8b | deepseek-v4-pro · gpt-5.6-terra |
| 3 | **Leaf v1.5** — taakspecifiek (Vangnet) | qwen3:14b | qwen3.8-max · kimi-k2.6 |
| 4 | **Tree v2.0** — coördinator/orkestratie | gpt-oss:20b | claude-sonnet-5 · glm-5.2 |
| 5 | **Jungle v2.5** — patronen, zwaar | qwen3.6:27b | grok-4.6 · kimi-k3 · gpt-5.6-sol |
| 6 | **Amazone v3.0** — frontier | qwen3:32b | claude-opus-5 · claude-fable-5.1 · gpt-6-astra |

- Lokaal: RAM-klasse bepaalt het model per niveau (8–15 / 16–23 / 24–36 / 48–64 / 96+ GB); op een 24 GB Mac zijn alle zes beschikbaar. Volledige mapping: `kern/data/cyberseed_models.json`.
- Cloud: eerste optie is de standaard; eigen model-id per niveau kan via scherm 19 (met tier-validatie).
- De systeemprompt hoort bij de **naam**, niet bij het model — Sprout gedraagt zich als Sprout, welk model er ook onder hangt.
- **Automatiek** (`kern/growkit_automatiek.py`): het zes-blokken-model (doel & trigger, bronnen, stappen, kwaliteit, uitvoering, randvoorwaarden) uit de Automatiek-planner; secrets-scanner weigert plannen met keys; `automatiekvoorstel` stuurt je wens naar KairOS, zijn JSON-antwoord wordt een plan.
- **Agent Chat-pijplijn**: bericht → `~/.../agenttaken/<agent>/wachtrij/*.json` op de VPS → poller (cron, 1 min) → `hermes chat -q --profile <agent>` met `[van: NAAM]`-prefix → antwoord gepuurd van CLI-meuk (`zuiver_antwoord`) + redenatie apart bewaard → antwoorden/<id>.json.
- **Chat-geschiedenis**: wissen = verplaatsen naar `<agent>/geschiedenis/` (antwoorden als `antwoord-*.json`); definitief wissen vereist `bevestig=true`. Elk antwoord kan een `redenatie`-veld meedragen (het denkproces, per bericht in- en uitklapbaar).
- **SSH**: de app praat met de VPS via `GROWKIT_HOST` (omgeving of `.env` in de repo-root; in `.gitignore`).
- **SOUL-bestanden**: gedrag, rol en stem van elke agent op de VPS (`/root/.hermes/SOUL.md` + profiel-SOUL's): focus-manifest, titulatuur ("Tiëndo" of "de Baas", nooit "papa"/"oom"), antwoord-verdeelregel, per-agent STEM.

## Quickstart

```bash
git clone git@github.com:parvenuprompting/Grow-Kit.git
cd Grow-Kit
python3 -m venv .venv && .venv/bin/pip install cryptography
.venv/bin/python -m unittest discover tests   # 802 tests

python3 seed.py            # geleende-agent-modus: kiemkeuze + planten
python3 loop.py            # het harnas: planten / hervatten / taak / ratificatie / status

# de macOS-app bouwen (XcodeGen + xcodebuild):
(cd app && bash build.sh)
```

- Review-rollen: kopieer `reviewconfig.voorbeeld.json` → `reviewconfig.json` (in `.gitignore`, nooit in de repo).
- VPS-verbinding: `export GROWKIT_HOST=gebruiker@jouw-vps` of zet het in `.env`.
- Verdere uitleg: `SEED.md` → `profielen/INDEX.md` → **`docs/HOE-HET-WERKT.md`**.

### Je eerste opdracht (één minuut)

1. Open de app → **00 Vandaag**.
2. Kies links onder **VOORBEELDEN** één van de drie: *Projectcontrole*,
   *Documentenoverzicht* of *Terugkerend rapport*.
3. Je ziet het plan, de afgesproken grenzen en de gegevensroute — er draait nog niets.
4. Bevestig: de machine doet de stappen en legt per stap bewijs vast.
5. De opdracht pauzeert bij het mens-moment. Lees het resultaat, geef je reden en
   keur goed of wijs af.

De drie voorbeelden werken **zonder VPS, zonder sleutel en zonder internet**: ze
tellen en controleren alleen bestanden op jouw machine.

## Structuur

```
Grow-Kit/
├── SEED.md                  ← geboortebrief
├── seed.py                  ← plant-mechanisme
├── loop.py                  ← het harnas: orchestratie zonder agent
├── adapter.py               ← JSON-CLI brug (74 commando's)
├── kern/                    ← 54 modules
├── profielen/               ← bomen: JSON-stappenplannen met gecodeerd bewijs
├── groei/                   ← groeilaag-instructie
├── tests/                   ← 802 tests + 13 E2E-scripts
├── app/                     ← macOS SwiftUI-app
│   ├── Sources/             ← views + Thema/Bouwstenen
│   ├── Fonts/               ← Fraunces + Inter (SIL OFL)
│   └── build.sh             ← XcodeGen + xcodebuild
├── docs/
│   ├── HOE-HET-WERKT.md     ← de complete uitleg
│   ├── plannen/             ← bouwplannen (o.a. Automatiek-inbouw)
│   └── mockups/             ← UI-mockups
└── README.md
```

## Tests & CI

Elke push en PR draait automatisch **CI** (GitHub Actions):
1. **Tests** — de volledige unittest-suite; rood = merge geblokkeerd
2. **Secrets-scan** — dezelfde key-patronen als het taak-contract, over elke diff; een echte key blokkeert de push
3. **macOS-build** — GrowKit.app moet compileren met fonts ingebed (op main)

- **799 in CI (Linux); 818 op macOS — 19 Digitale-Kloon-tests vereisen de macOS Keychain.** (unittest; de enige externe dependency is `cryptography` voor de Digitale Kloon, in een repo-eigen `.venv` — bewuste, gedocumenteerde keuze)
- **13 end-to-end-scripts**: fase-testen + slice-E2E
- Test 4 bewijst agent-onafhankelijkheid: harnas plant, crasht (`kill -9`), hervat en ratificeert — met alleen python3
- Elke nieuwe slice TDD: eerst rood, dan groen, dan end-to-end

## Wat verlaat je machine?

Grow Kit is **lokaal-eerst**, en dat is een belofte die je per opdracht kunt
controleren in plaats van op een badge te vertrouwen. Elke opdracht toont vóór het
draaien zijn **gegevensroute**:

| Route | Wat het betekent |
|---|---|
| **Lokaal** | Alles gebeurt op jouw machine. Geen sleutel, geen verbinding nodig. |
| **Eigen VPS** | Er gaat iets naar je eigen server (`GROWKIT_HOST`) — niets daarbuiten. |
| **Cloud** | Er gaat inhoud naar een clouddienst buiten je eigen systemen. |

De route wordt afgeleid uit de commando's van het plan (`ssh`/`scp` → eigen VPS,
`curl`/`wget`/`http(s)` → cloud). Verklaart een profiel mínder dan zijn commando's
doen, dan wint het zwaarste en verschijnt er een waarschuwing — geen stille keuze.

**Cloud start nooit vanzelf.** Is de route cloud, dan blijft de uitvoerknop dicht
tot je met een reden toestemming geeft. Dat besluit landt in de geschiedenis en is
net zo zichtbaar in te trekken. De motor weigert de uitvoering ook als een script
het zonder toestemming probeert.

Eerlijk over de rest van het huis: **Agent Chat** loopt via je eigen VPS,
**CyberSeed** kiest per niveau lokaal (Ollama) of cloud (OpenRouter) — die keuze
maak jij, en op een 24 GB Mac zijn alle zes niveaus lokaal beschikbaar. De drie
voorbeeldopdrachten, de motor, de vijf bewijscontroles en de opslag zijn volledig
lokaal, kosten € 0 en hebben geen sleutel nodig.

## Filosofie

Grow Kit gaat ervan uit dat de AI fouten maakt — **zero-trust**. De interpretatie van "is het gelukt?" ligt nooit bij het model, maar bij een deterministische controlelaag.

Geïnspireerd door het "Zen of Reticulum"-principe: **een tool is nooit neutraal. Een tool is intentie, gekristalliseerd.** Grow Kit is gebouwd met de bedoeling dat de mens bepaalt — niet de agent, niet de provider, niet de infrastructuur.

## Over de maker

Ik ben **Tiëndo**, vrachtwagenchauffeur. Ik bouw dit project in mijn eentje, in de avonden naast fulltime werk. Dit is een **build-in-public** project: je ziet het groeien, inclusief de missers. Volg de voortgang op [X (@GrowKitHarnas)](https://x.com/GrowKitHarnas). Vragen? Open een issue.

## Licentie

MIT — zie [LICENSE](LICENSE).

Buiten bereik getest: de software is ontworpen voor autonoom gebruik. De gebruiker blijft eindverantwoordelijk voor wat de agent uitvoert.

## Bijdragen

Pull requests zijn welkom. Elke bijdrage moet vergezeld zijn van de bijbehorende tests — eerst rood, dan groen. Bewijs telt.

- **PANIC-knop** (`kern/growkit_panic.py`): één commando pauzeert alles — motor stopt, geen merges, geen pushes. Reden verplicht. Elke panic/herstel is een nieuwe append-only logboek-entry. Herstel nooit automatisch; de Baas beslist. Adapter-commando's: `panic`, `panicherstel`, `panicstatus`.
