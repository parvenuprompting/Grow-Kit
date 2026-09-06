# Grow Kit 🌳

[![CI](https://github.com/parvenuprompting/Grow-Kit/actions/workflows/ci.yml/badge.svg)](https://github.com/parvenuprompting/Grow-Kit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS_14%2B-black?style=flat-square)]()
[![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)]()
[![Tests](https://img.shields.io/badge/tests-566_groen-success?style=flat-square)]()
[![Agents](https://img.shields.io/badge/agent-familie-7_teal?style=flat-square)]()
[![Privacy](https://img.shields.io/badge/privacy-100%25_local-success?style=flat-square)]()
[![Made by](https://img.shields.io/badge/build_in_public-Ti%C3%ABndo-9cf?style=flat-square)]()
[![Encryption](https://img.shields.io/badge/secrets-AES--256_GCM-orange?style=flat-square)]()

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

## De app

Native macOS-app (SwiftUI) in editorial-monochrome stijl. Zijmenu:

| Nr. | Scherm | Wat het doet |
|---|---|---|
| 00 | Thuis | Dashboard, mini-graaf, saldo |
| **WERK** | | |
| 01 | Agent Chat | Praat met de familie; Thought-blok per antwoord, gesprek wissen (→archief), geschiedenis |
| 02 | Status | Identiteit, register, tellers, logboek |
| 03 | Planten | Kiemkeuze → concept → motor met bewijs |
| 04 | Goedkeuringen | Ratificatie: mens keurt goed of af |
| 05 | Dialoog | Scope-poort, prompt-slijper, ronde tafel |
| 06 | Agenten | Gouverneur: familie, observaties, taak-contracten |
| 07 | **Automatiek** | Eén zin in, automation-plan uit — KairOS stelt voor, jij keurt |
| 08 | Knowledge Graph | Brein-verbanden; klik op een sectie om in te zoeken |
| 09 | Prompts | Gecureerde bibliotheek, variabelen invullen |
| 10 | Vangnet | Opgevangen review-aanroepen en uitkomsten |
| 11 | Audit | Volledig, append-only logboek |
| **SYSTEEM** | | |
| 12 | Secure Vault | Echte kluizen via macOS hdiutil (AES-256/APFS) |
| 13 | Amnesia Protocol | Gevoelige tekst anonimiseren en herstellen |
| 14 | Digitale Kloon | Persoonlijke kluis: 6 categorieën, AES-256-GCM, PIN + Touch ID |
| 15 | Hervatten | Crash-herstel uit het logboek |
| 16 | Taak | Boom-pad + governor → takenlijst met bewijs |
| **LEREN** | | |
| 17 | Rondleiding | Het ontwerp in vijf schermen |
| 18 | Uitleg | De motor uitgelegd |
| 19 | Best Practices | Kerninzichten uit eigen onderzoek, met zoeken |

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

- **Python-kern** (`kern/`, 32 modules): scope-poort, stappen-motor met faalcontract, vijf machine-controles, review-laag, ratificatie, leesroute, crash-herstel, boom-register, vangnet (SQLite), agent-familie, Knowledge Graph, prompt-bibliotheek, Secure Vault (hdiutil), Amnesia (anonimiseren), Digitale Kloon (AES-256-GCM via `cryptography` in een repo-eigen `.venv` — bewuste uitzondering op stdlib-only), Best Practices.
- **Adapter** (`adapter.py`): JSON-CLI met 56 commando's over de kern — de enige poort tussen app en motor.
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
.venv/bin/python -m unittest discover tests   # 546 tests

python3 seed.py            # geleende-agent-modus: kiemkeuze + planten
python3 loop.py            # het harnas: planten / hervatten / taak / ratificatie / status

# de macOS-app bouwen (XcodeGen + xcodebuild):
(cd app && bash build.sh)
```

- Review-rollen: kopieer `reviewconfig.voorbeeld.json` → `reviewconfig.json` (in `.gitignore`, nooit in de repo).
- VPS-verbinding: `export GROWKIT_HOST=gebruiker@jouw-vps` of zet het in `.env`.
- Verdere uitleg: `SEED.md` → `profielen/INDEX.md` → **`docs/HOE-HET-WERKT.md`**.

## Structuur

```
Grow-Kit/
├── SEED.md                  ← geboortebrief
├── seed.py                  ← plant-mechanisme
├── loop.py                  ← het harnas: orchestratie zonder agent
├── adapter.py               ← JSON-CLI brug (56 commando's)
├── kern/                    ← 32 modules
├── profielen/               ← bomen: JSON-stappenplannen met gecodeerd bewijs
├── groei/                   ← groeilaag-instructie
├── tests/                   ← 566 tests + 20 E2E-scripts
├── app/                     ← macOS SwiftUI-app (22 views)
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

- **566 tests groen** (unittest; de enige externe dependency is `cryptography` voor de Digitale Kloon, in een repo-eigen `.venv` — bewuste, gedocumenteerde keuze)
- **20 end-to-end-scripts**: fase-testen + slice-E2E
- Test 4 bewijst agent-onafhankelijkheid: harnas plant, crasht (`kill -9`), hervat en ratificeert — met alleen python3
- Elke nieuwe slice TDD: eerst rood, dan groen, dan end-to-end

## Filosofie

Grow Kit gaat ervan uit dat de AI fouten maakt — **zero-trust**. De interpretatie van "is het gelukt?" ligt nooit bij het model, maar bij een deterministische controlelaag.

Geïnspireerd door het "Zen of Reticulum"-principe: **een tool is nooit neutraal. Een tool is intentie, gekristalliseerd.** Grow Kit is gebouwd met de bedoeling dat de mens bepaalt — niet de agent, niet de provider, niet de infrastructuur.

## Over de maker

Ik ben **Tiëndo**, vrachtwagenchauffeur. Ik bouw dit project in mijn eentje, in de avonden naast fulltime werk. Dit is een **build-in-public** project: je ziet het groeien, inclusief de missers. Vragen? Open een issue.

## Licentie

MIT — zie [LICENSE](LICENSE).

Buiten bereik getest: de software is ontworpen voor autonoom gebruik. De gebruiker blijft eindverantwoordelijk voor wat de agent uitvoert.

## Bijdragen

Pull requests zijn welkom. Elke bijdrage moet vergezeld zijn van de bijbehorende tests — eerst rood, dan groen. Bewijs telt.
