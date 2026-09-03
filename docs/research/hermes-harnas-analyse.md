# Architectuuranalyse: Hermes Agent als research voor het GrowKit-harnas (fase 4)

Datum: 3 september 2026
Status: research-document — er is niets gebouwd en niets gewijzigd in Hermes-installaties.
Aanleiding: GrowKit-ontwerpdoc §8 (fase 4: "Eigen harnas — dunne provider-agnostische orchestratieloop, paar honderd regels, geen framework").

## 0. Doel, bronnen en aanpak

Dit rapport analyseert hoe Hermes Agent (Nous Research) technisch is opgebouwd, per onderdeel dat relevant is voor het toekomstige GrowKit-harnas. Per onderdeel: hoe het is opgezet (met concrete bestandspaden), de kerninterfaces/patronen, en een eerlijk oordeel **hergebruiken als patroon** versus **bewust niet overnemen**.

Gebruikte bronnen:

- **Lokale installatie** (primair): `~/.hermes/hermes-agent/` — editable git-install (pip: `hermes-agent 0.20.5`, install-methode git, venv in `~/.hermes/hermes-agent/venv`, Python 3.11). Runtime-gegevens in `~/.hermes/` (config.yaml, skills/, plugins/, sessions.db, state.db).
- **Documentatie** (autoritatief): `https://hermes-agent.nousresearch.com/docs` — met name `developer-guide/architecture`, `developer-guide/agent-loop`, `developer-guide/provider-runtime`, `developer-guide/tools-runtime`, `user-guide/features/skills`, `user-guide/features/mcp`.
- **Publieke repo**: `https://github.com/NousResearch/hermes-agent` — open source, MIT-licentie, actief ontwikkeld. De lokale kloon is een afgeleide hiervan (+143 gedragen commits). De GitHub-versie is dus legitiem quotbaar/hergebruikbaar onder MIT.
- Ontwerpdoc: `docs/superpowers/specs/2026-09-03-growkit-design.md` (fase-4-eisen: provider-agnostisch, dun, bewijs-gefundeerd, mens als curator).

Geen secrets, `.env`-bestanden of tokens zijn gelezen; config.yaml is uitsluitend structuur-gescand (keys/types), niet inhoudelijk gekopieerd.

## 1. Systeemoverzicht Hermes in één alinea

Hermes is één agent-kern (`AIAgent` in `run_agent.py`) die door vijf entry-points wordt gebruikt: CLI (`cli.py`), messaging-gateway (`gateway/run.py`, 20+ platforms), ACP-adapter (IDE), batch-runner en API-server. De kern: systeem-prompt bouwen → provider/api-mode resolven → model-aanroep → tool-calls dispatchen via een centraal registry → resultaten terug de loop in → sessie persisteer in SQLite+FTS5. Optionele subsystemen (MCP, memory-providers, plugins, skills) hangen aan registry- en ABC-patronen, niet aan harde afhankelijkheden. Twee ontwerpregels uit hun AGENTS.md zijn sfeerbepalend: (1) *per-conversation prompt caching is sacred* — niets muteert de context of systeem-prompt mid-gesprek; (2) *the core is a narrow waist* — capaciteit leeft aan de randen (tools/skills/plugins), de kern blijft klein.

**Relevantie voor GrowKit:** dit is precies de "dunne taille"-vorm die fase 4 wil — alleen wil GrowKit de taille nóg smaller (één api-mode, sequentiële executie, geen platformen).

---

## 2. (a) De agent-loop en berichten-context

### Opzet

- `run_agent.py` (±427 KB, ±9000+ regels): klasse `AIAgent` (regel 421). Kernmethodes: `run_conversation()` (r. 8492), `_execute_tool_calls()` (r. 8323) met `_execute_tool_calls_sequential()` (r. 8453) en `_execute_tool_calls_concurrent()` (r. 8448).
- `agent/conversation_loop.py`: een tweede, slankere `run_conversation()` (r. 1766) — kennelijk een uitgeklede loopvariant.
- `agent/prompt_builder.py`: systeem-prompt-assemblage (identiteit, platform-hints, skills-index, context-bestanden, geheugen).
- `agent/context_compressor.py` + `agent/context_engine.py`: pluggable contextcompressie (ABC + default lossy-summarization-engine).
- `hermes_state.py`: SQLite-sessieopslag met FTS5 (doorzoekbare historie).

### Kernpatroon: de loop

Uit de docs (developer-guide/agent-loop), bevestigd door de bronstructuur:

```
run_conversation()
  1. Genereer task_id indien afwezig
  2. Append user-message aan conversatie-historie
  3. Bouw of hergebruik gecachte systeem-prompt (prompt_builder.py)
  4. Preflight-compressie indien >50% context
  5. Bouw API-berichten uit historie
  6. Injecteer efemere prompt-lagen (budget-warnings)
  7. Prompt-caching-markers (Anthropic)
  8. Onderbreekbare API-aanroep (_interruptible_api_call)
  9. Response parsen:
     - tool_calls? → uitvoeren, resultaten appenden, terug naar stap 5
     - tekst? → sessie persisteren, geheugen flushen, returnen
```

Interne berichten zijn overal OpenAI-formaat:

```python
{"role": "system", "content": "..."}
{"role": "user", "content": "..."}
{"role": "assistant", "content": "...", "tool_calls": [...]}
{"role": "tool", "tool_call_id": "...", "content": "..."}
```

Drie harde invarianten (providers weigeren anders): nooit twee assistant-berichten op een rij, nooit twee user-berichten op een rij, alleen `tool`-rollen mogen aaneengesloten staan (parallelle tool-resultaten). Reasoning-content wordt bewaard in `assistant_msg["reasoning"]`.

Verder in de loop:

- **IterationBudget**: standaard 500 iteraties (`agent.max_turns`), per agent een eigen budget; subagents een onafhankelijk, lager plafond (`delegation.max_iterations`, standaard 50). Bij 100% stopt de agent en vat samen wat er gebeurd is.
- **Onderbreekbaarheid**: de HTTP-aanroep draait in een achtergrondthread; de hoofdthread wacht op response/timeout/interrupt. Bij interrupt wordt de response weggegooid — nooit een half antwoord in de historie.
- **Callbacks-contract** (platformonafhankelijke voortgang): `tool_progress_callback`, `thinking_callback`, `reasoning_callback`, `clarify_callback`, `step_callback`, `stream_delta_callback` — zo tonen CLI, gateway en ACP dezelfde loop op hun eigen manier.
- **Tool-resultaten terug in historie**: resultaten worden in de oorspronkelijke tool-call-volgorde herinseerdeerd, ongeacht voltooiingsvolgorde van de threadpool.
- **Sessie-persistatie na elke beurt**: berichten naar de session store, geheugen-flush naar `MEMORY.md`/`USER.md`.

### Oordeel

**Hergebruiken als patroon:**
- De loopvorm zelf (stappen 1–9) is exact het GrowKit-harnas-skelet. GrowKit's `loop.py` kan dit in ±150 regels zonder compressie/caching-lagen.
- OpenAI-berichtformaat als interne lingua franca + de rol-alternatie-invarianten. Dit is de industrie-standaard en voorkomt hele klassen provider-fouten.
- IterationBudget: GrowKit heeft hier zelfs een strengere variant al in het ontwerp (`bij_falen`: precies één alternatief, dan mens). Een budgetteller per taak hoort in het harnas.
- Onderbreekbare API-aanroep als thread + discard: klein patroon, groot comfort, goed herbruikbaar.
- Callbacks-contract: GrowKit fase 4 heeft een terminal-UI; een `progress_callback` na elke stap is genoeg (één callback i.p.v. Hermes' negen).

**Bewust niet overnemen:**
- De omvang: `run_agent.py` is een 427 KB god-file. Het harnas van GrowKit moet één leesbaar bestand/module blijven — dit is precies wat het ontwerpdoc met "paar honderd regels, geen framework" verbiedt.
- Contextcompressie, prompt-caching-markers en "efemere prompt-lagen" — irrelevant op GrowKit's taaklengtes (stappenplannen met bewijs, geen 500-turn-gesprekken). Weglaten is een feature.
- Parallelle tool-executie via ThreadPoolExecutor. GrowKit voert stappenplannen sequentieel uit met bewijs per stap; concurrentie voegt alleen determinisme-risico toe.
- Sessie-database met FTS5. GrowKit heeft al append-only `groei/logboek.json` in het ontwerp — JSON-log is voldoende en past bij "de mens kan alles teruglezen".

---

## 3. (b) Provider- en model-abstractie

### Opzet

- `providers/base.py`: `ProviderProfile` — declaratieve dataclass per leverancier:

```python
@dataclass
class ProviderProfile:
    name: str
    api_mode: str = "chat_completions"   # chat_completions | codex_responses | anthropic_messages
    aliases: tuple = ()
    env_vars: tuple = ()                  # credentie-bronnen in prioriteitsvolgorde
    base_url: str = ""
    auth_type: str = "api_key"            # api_key|oauth_device_code|oauth_external|copilot|aws_sdk
    ...
```

  Expliciet docstring-beleid: profielen zijn *declarative* — ze beschrijven gedrag, maar bezitten géén client-constructie of streaming (dat blijft bij AIAgent).
- `hermes_cli/runtime_provider.py` + `hermes_cli/auth.py`: de gedeelde runtime-resolver, gebruikt door CLI, gateway, cron, ACP en hulptaken. Resolutievolgorde: expliciete runtime-aanvraag → config.yaml (`model.provider`/`model.default`/`model.base_url`) → omgevingsvariabelen → defaults. Auto-detectie van api_mode uit de base-URL (host `api.anthropic.com` → `anthropic_messages`, `/anthropic`-suffix idem, met spoofing-weerstanden als exact-hostname-matches).
- `plugins/model-providers/<name>/`: per-provider plugins (±30 gebundeld: OpenRouter, Nous Portal, Anthropic native, Gemini, Bedrock, Ollama, custom, …) die zichzelf registreren; user-plugins in `$HERMES_HOME/plugins/model-providers/` overschrijven gebundelde.
- **Drie API-modes** die allemaal convergeren op hetzelfde interne OpenAI-formaat: `chat_completions` (elk OpenAI-compatibel endpoint, via `openai.OpenAI`), `codex_responses` (Responses API), `anthropic_messages` (native, via `agent/anthropic_adapter.py`).
- Fallback-keten: `fallback_providers`-lijst in config; bij 429/5xx/401/403 wordt in-place geswitcht (`self.model/provider/base_url/api_mode/client`), met eigen credential-resolutie en reset van retry-count.
- Credential-scoping per base-URL: `OPENROUTER_API_KEY` gaat alleen naar `openrouter.ai`-endpoints enz. — voorkomt key-lekkage naar verkeerde custom endpoints.

### Kernpatroon: provider-agnostisch via "alles OpenAI-compatibel is één mode"

De slimme zet van Hermes is dat provider-agnosticisme niet zit in n adapter per leverancier, maar in **één dominant transport** (`chat_completions`) plus declaratieve profielen die alleen URL/key/quirks invullen. OpenRouter, Ollama, LM Studio, lokaal, elke SaaS: allemaal dezelfde mode. `provider: custom` is een eersteklas burger voor elk OpenAI-compatibel endpoint.

### Oordeel

**Hergebruiken als patroon:**
- De default naar `chat_completions` als enige smalste punt. Voor het GrowKit-harnas: **alleen** deze mode implementeren (OpenAI SDK, `base_url` + `api_key` configureerbaar). Dat dekt OpenRouter én vrijwel alle leveranciers — precies het ontwerpprincipe "geen binding aan één AI-leverancier".
- De declaratieve ProviderProfile-vorm, maar dan ingekrompen tot: `name`, `base_url`, `api_key_env`, `model`. GrowKit's §9 reviewer-rol-mapping ("gebruiker mapt rollen naar modellen in zijn eigen configuratie") is letterlijk een mini-runtime-resolver: rol → (provider, model) in een eigen config-bestand, zelfde resolutievolgorde (expliciet → config → default).
- Credential-scoping per base-URL: als GrowKit meerdere rollen (uitvoerder/reviewer) op verschillende endpoints zet, mogen keys nooit naar het verkeerde endpoint gaan. Klein, hard te testen, over te nemen.
- Fallback-gedachte, maar GrowKit-streng: het ontwerp zegt al "één alternatief, dan mens". Hermes' oneindige fallback-ketens zijn voor GrowKit te genereus.

**Bewust niet overnemen:**
- De `codex_responses` en `anthropic_messages` modes met hun adapters (samen goed voor duizenden regels in `agent/anthropic_adapter.py`, `agent/gemini_native_adapter.py`, enz.). GrowKit kiest één wire-formaat; modellen die dat niet spreken, vallen buiten de Pro-laat (of komen later).
- OAuth-apparaten, credential-pools, refresh-flows (`agent/credential_pool.py`, `agent/credential_sources.py`). Fase 4 heeft `api_key` in een eigen config/env genoeg.
- models.dev-registry-integratie en modellen-catalogi met health-checks. GrowKit heeft geen model-picker nodig; de gebruiker zet zijn modelnaam in de config.

---

## 4. (c) Tool-definitie en -executie, inclusief guards

### Opzet

- `tools/registry.py`: centraal singleton-registry. Elk tool-bestand roept **at import time** aan:

```python
registry.register(
    name="terminal",              # uniek, gebruikt in API-schema
    toolset="terminal",           # groepering
    schema={...},                 # model-facing schema (description + parameters)
    handler=handle_terminal,      # uitvoerende functie
    check_fn=check_terminal,      # optioneel: beschikbaarheidsgate (True/False)
    requires_env=["SOME_VAR"],    # optioneel: benodigde env-variabelen
    is_async=False,
)
```

- **Discovery zonder importlijst**: `discover_builtin_tools()` scant elk `tools/*.py` met AST-parse op top-level `registry.register()`-calls (met mtime/size-memo-cache). Ieder bestand dat zich registreert is automatisch een tool; schaduwing van een bestaande tool wordt geweigerd tenzij `override=True` (+ operator-opt-in voor plugins).
- `model_tools.py` (±74 KB): schema-collectie voor de model-aanroep + `handle_function_call()`-dispatch.
- **Guards, in lagen**:
  1. `tools/approval.py`: detectie van gevaarlijke commando's vóór executie; via `approval_callback` wachten op menselijke goedkeuring (de "smart approval" uit GrowKit's terminal-tooling is hiervan de gebruikerskant).
  2. `agent/tool_guardrails.py`: *pure, side-effect-vrije* loop-guardrails — classificeert tools in `IDEMPOTENT_TOOL_NAMES` (read_file, search_files, web_search, …) versus `MUTATING_TOOL_NAMES` (terminal, write_file, patch, delegate_task, …) en telt per turn; runtime beslist of dat een warning, synthetisch tool-resultaat of harde stop wordt. Config: `tool_loop_guardrails.warn_after` / `hard_stop_after` per categorie. Plus een stall-guard voor identieke herhaalde calls, met een ontheffingslijst voor legitieme pollers (`process poll`, `<vendor>_get_result`).
  3. **Error-bounding in het registry zelf**: tool-fout-body's worden afgekapt op 2048 tekens voor de model-context (8192 voor logs) — "no registered tool can return an unbounded error body that stacks across retries". Dit geldt ook voor handlers die zelf JSON met een `error`-veld serialiseren.
  4. Sommige tools worden **voor het registry geïntercepteerd** door `run_agent.py` (`todo`, `memory`, `session_search`, `delegate_task`) omdat ze agent-state muteren — synthetische tool-resultaten buiten het registry om.
- Executie: één tool-call sequentieel in de hoofdthread; meerdere via ThreadPoolExecutor, behalve interactieve tools (bijv. `clarify`) die sequentieel forceren; resultaten altijd in call-volgorde terug.

### Oordeel

**Hergebruiken als patroon:**
- Het `register(name, schema, handler, check_fn)`-mini-registry. Voor GrowKit volstaat een dict van ±4 tools (`shell_check`, `http_check`, `file_exists`, `json_valid` — het §3-bewijs-typeset van het ontwerpdoc) + `log_step`. Geen AST-discovery nodig; een handgeschreven lijst is eerlijker op deze schaal.
- **check_fn-idee**: tool alleen aanbieden aan het model als aanwezig (bijv. `http_check` alleen als httpx beschikbaar). Voorkomt dat het model tools kiest die toch falen.
- **De idempotent/mutating-classificatie** is een directe invulling van GrowKit's `idempotent`-veld per stap (§4): het harnas kan de classificatie hard coderen per bewijs-type in plaats van uit te lezen, maar het patroon "sommbare categorieën + per-categorie drempels" is exact de juiste vorm.
- Error-bounding op tool-output: gegarandeerd relevant — GrowKit's `shell_check`-output kan explosief zijn; een cap van ±2 KB in het model-context en een grotere cap in het logboek is één-op-één herbruikbaar.
- Interception van state-muterende tools: in GrowKit is élke stap state-muterend (append-only log); de les is dat de log-schrijfregel niet als normaal "tool door het model" moet lopen maar afgedwongen door de loop zelf — het model kan de log niet overslaan of vervalsen.

**Bewust niet overnemen:**
- 70+ tools, 28 toolsets en platform-presets (`toolsets.py`): GrowKit's harnas heeft er hooguit zes.
- AST-gebaseerde auto-discovery: mooie engineering, maar voor een harnas van paar honderd regels is explicititeit een deugd (het ontwerpdoc wil juist dat het script afdwingt en niet de agent kiest).
- ThreadPoolExecutor + tool-annotaties voor interactiviteit. Sequentieel is het bewijsmodel.

---

## 5. (d) Het skills-systeem

### Opzet

- Primaire opslag: `~/.hermes/skills/<naam>/SKILL.md` (+ ondersteunende `references/`, `templates/`, `scripts/`). Gebundelde skills uit de repo worden gesynchroniseerd met een origin-hash-manifest (`.bundled_manifest`) zodat gebruikerwijzigingen en upstream-updates niet botsten.
- Formaat: YAML-frontmatter + markdown-body, compatibel met het agentskills.io open standaard. Echte frontmatter (uit `~/.hermes/skills/humanizer/SKILL.md`):

```yaml
---
name: humanizer
description: |
  Remove signs of AI-generated writing from text. Use when editing or
  reviewing text... (beschrijving is de trigger — "Use when …")
license: MIT
metadata:
  version: "2.9.1"
---
```

- **Progressive disclosure, drie niveaus** (docs, user-guide/features/skills):
  - Niveau 0: `skills_list()` → naam + korte beschrijving (~3k tokens voor alle skills samen); de systeem-prompt bevat alléén deze index (beschrijving afgekapt tot ±57 tekens).
  - Niveau 1: `skill_view(name)` → volledige inhoud, pas als het model hem nodig heeft.
  - Niveau 2: `skill_view(name, file_path)` → specifiek referentiebestand.
- Laadmechanisme: `agent/skill_utils.py` (frontmatter-parse, platform- en omgevingsmatching `skill_matches_platform`), `agent/prompt_builder.py` (index in systeem-prompt, cache-stabiel), `agent/skill_commands.py` (slash-commando's, gedeeld tussen CLI en gateway; skill-inhoud wordt in de user-turn geëxpandeerd met markers, inclusief een extractor die de *echte* gebruikersinstructie terugvindt zodat geheugen-providers niet de hele skill-body opslaan).
- Extras die patroon tonen: `required_environment_variables` met prompts (skills verdwijnen niet uit de index bij missende env, maar declaren hun setup), conditionele fallback-skills (`fallback_for_toolsets`), project-lokale skills met vertrouwenspoort en security-scan, en `skill_manage` (de agent kan eigen skills schrijven/patchen — procedureel geheugen).

### Oordeel

**Hergebruiken als patroon:**
- **Progressive disclosure** is direct toepasbaar op GrowKit's profielen-catalogus: `profielen/INDEX.md` (kiemkeuze) is niveau 0, het stappenplan-JSON is niveau 1. Het ontwerpdoc's leesroute-afdwinging (§5) is eigenlijk een strikte variant: niveau 1 wordt pas ontsloten door seed.py per fase. Dezelfde drieledige vorm, sterker afgedwongen.
- Frontmatter met `name` + *gedrags-trigger* in de description ("Use when …") als enige index-inhoud: goedkoop, model-vriendelijk, en de afkap-regel (korte venstergrootte) dwingt concrete beschrijvingen af.
- Skills als pure *documenten* (markdown + frontmatter, geen code-executie in de skill zelf): precies hoe GrowKit's profielen eruit moeten zien — data, geen programma's.

**Bewust niet overnemen:**
- Slash-commando-expansie, skill-bundles, Skills Hub met trust-levels en security-scans, project-lokale trust-flow: allemaal platform-features. GrowKit heeft één entry-point (seed.py) en geen hub.
- `skill_manage` (de agent schrijft zijn eigen skills): GrowKit's tweede-brein-profiel laat de agent wél voorstellen doen, maar promotie blijft mens — geen automatisch procedureel geheugen in het harnas zelf.

---

## 6. (e) De memory-provider-interface (incl. Agent-Brain)

### Opzet

- `agent/memory_provider.py`: de ABC. Lifecycle (geroepen door MemoryManager, gedraad in `run_agent.py`):

```python
initialize()          — verbinden, resources, opwarmen
system_prompt_block() — statische tekst voor de systeem-prompt
prefetch(query)       — achtergrond-recall vóór elke beurt
sync_turn(user, asst) — asynchrone schrijf na elke beurt
get_tool_schemas()    — tool-schema's blootstellen aan het model
handle_tool_call()    — die tool-calls dispatchen
shutdown()            — netjes afsluiten
# optionele hooks: on_turn_start, on_session_end, on_session_switch,
# on_pre_compress, on_memory_write, on_delegation, backup_paths
```

- **Eén-externe-provider-limiet** (MemoryManager): voorkomt tool-schema-bloat en conflicterende geheugen-backends. Activering via `memory.provider`-config-key.
- Gebundelde providers in `plugins/memory/<name>/`: honcho, mem0, hindsight, supermemory, openviking, retaindb, … Elke provider mag eigen tools meegeven (bijv. `brain_search`-patroon) én een `RecallStatus`-glyph teruggeven voor een deterministische "geheugen-gebruikt"-indicator (model-onafhankelijk).
- Kleine maar elegante guard: `TRIVIAL_PROMPT_RE` — triviaal invoer ("ok", "hi", "continue") slaat prefetch over; geen netwerkrondje en geen stalen context die een eenwoord-antwoord vergalt.
- **Agent-Brain als concreet geval** (gebruikersplugin, `~/.hermes/plugins/agent-brain/`): `plugin.yaml` + `agent_brain_provider.py` (±490 regels), subclasseert de ABC. Config via `plugins.agent-brain.brain_path` in config.yaml. Belangrijk voor GrowKit: dit is de vorm (niet de inhoud) van het tweede-brein-profiel:
  - **Alleen-lezen brein**: leest identiteit/projecten/kennis uit de repo-kloon; schrijft nóóit in het brein zelf.
  - **Append-only inbox-voorstellen**: `brain_digest`-tool schrijft uitsluitend naar `inbox/` als VOORSTEL-bestand (met datumstempel + slug + botsingsteller); curatie blijft bij de mens. Ook `on_memory_write` (de ingebouwde geheugen-acties) wordt *gespiegeld* als voorstel naar de inbox, niet uitgevoerd.
  - `system_prompt_block()`: bootstrap-context bewust < ±2000 tekens (identiteitskern + actieve projecten met status + volgende stap).
  - `prefetch()`: voor elke beurt max 2 zoektreffers als korte fragmenten (±400 tekens per fragment).

### Oordeel

**Hergebruiken als patroon:**
- De **ABC-vorm zelf** (init → prompt-block → prefetch → tools → shutdown): een dossier-dunne provider-interface. GrowKit's groeivliegwiel (§11.2: "het geplante brein voedt de slijper") heeft exact deze interface nodig: het brein is een alleen-lezen grondstof met append-only retourkanaal. De Agent-Brain-provider is daarvan het referentie-exemplaar — maar let op ontwerpdoc §10: GrowKit's tweede-brein-profiel is generiek en raakt Tiëndo's inhoud niet; overneembaar zijn de *interface-vorm* en de *inbox-curatiewijze*, niet de bestanden.
- De **alleen-lezen + inbox-voorstel-scheiding** als hard protocol: dit is al GrowKit's eigen regel (inzichten-inbox met VOORSTEL-status, mens cureert) — bevestigd als werkbare vorm.
- `TRIVIAL_PROMPT_RE`-achtige gating: ook de GrowKit-slijper moet geen brein-prefetch doen op lege/formulier-invoer.
- De systeem-prompt-block-budgettering (<2k tekens): direct herbruikbaar om GrowKit's fase-injectie klein te houden.

**Bewust niet overnemen:**
- De volledige optionele-hooklijst (on_delegation, backup_paths, on_session_switch, …): GrowKit's harnas heeft alleen `prefetch`-achtige lees en `propose`-achtige schrijf nodig. Twee methodes, geen negen.
- Meerdere externe providers, RecallStatus-glyphs en model-onafhankelijke indicatoren: presentatie-fijnheid die het harnas niet nodig heeft.

---

## 7. (f) MCP-integratie

### Opzet

- Client: `tools/mcp_tool.py` — verbindt via stdio, HTTP/StreamableHTTP of SSE; configured in `config.yaml` onder `mcp_servers` (command+args of url+headers; timeouts, keepalive, idle/lifetime-recycle van stdio-processen). De Python-MCP-package is optioneel — niet geïnstalleerd ⇒ module is een no-op (graceful degradation).
- **Tools verschijnen in hetzelfde registry** als ingebouwd gereedschap, met naam-prefix `mcp_<server>_<tool>` tegen collisions; per-server include/exclude-filtering van tools; dynamische herontdekking via `list_changed`-notificaties; automatische reconnect met backoff.
- Veiligheid: stdio-servers krijgen alleen expliciet geconfigureerde env-vars + safe baseline (geen volledige shell-omgeving — geen accidental secret leakage); onzichtbare Unicode-TAG-tekens (U+E0000–U+E007F, een klassiek prompt-injectie-smokkelkanaal) worden uit alle tool-resultaten, resources en beschrijvingen gestript; per-user identity-headers optioneel.
- Catalogus: `optional-mcps/<name>/manifest.yaml` — alleen toegevoegd via PR (Nous-goedkeuring = aanwezigheid in de map); versies exact gepind (`uvx pkg==X`, commit-SHA's); nooit auto-update; install-geheimen gaan naar `~/.hermes/.env`.
- Hermes kan zélf ook MCP-server zijn (`mcp_serve.py`, stdio) zodat andere agents zijn messaging-capabilities kunnen gebruiken.

### Oordeel

**Hergebruiken als patroon:**
- **MCP-tools in hetzelfde registry als native tools**: als GrowKit ooit tools van buiten wil (fase 5+, niet fase 4), is "één registry, één naamruimte-conventie" de juiste vorm.
- De supply-chain-regels van de catalogus (exacte pins, geen auto-update, secrets naar .env): in het verlengde van GrowKit's eigen bewijscultuur, relevant zodra GrowKit externe profielen/hubs aanbiedt.
- Unicode-TAG-stripping van tool-output: een kleine, concrete prompt-injectie-afweer die goedkoop meegaat in een eigen `shell_check`-output-sanitizer. (Het ontwerpdoc noemt injectie-afweer "buiten scope voor nu, relevant zodra het harnas bestaat" — dit is de eerste goedkope stap.)

**Bewust niet overnemen:**
- Hele MCP-client in het harnas zelf. Fase 4 heeft vier bewijs-checktools en geen externe servers; de optionele-deps + no-op-graceful-degradation-les is meegenomen, de rest is framework-gewicht.
- Sampling-config (server-geïnitieerde LLM-aanroepen), OAuth-HTTP-MCP, SSE, reconnect-backoff: allemaal buiten GrowKit's scope-poort.

---

## 8. (g) Hooks- en config-mechanismen

### Opzet

Twee gescheiden hook-systemen:

1. **Gebeurtenis-hooks** (`gateway/hooks.py`, `HookRegistry`): mappen in `~/.hermes/hooks/` met `HOOK.yaml` (metadata + eventlijst) + `handler.py` (`async def handle(event_type, context)`). Events: `gateway:startup`, `session:start/end/reset`, `agent:start/step/end`, `command:*`. Expliciet contract: hook-fouten worden gelogd maar blokkeren nooit de hoofdpipeline.
2. **Plugin-hooks** (`hermes_cli/plugins.py`, PluginManager): `VALID_HOOKS` als centrally documented taxonomy, `invoke_hook(name, **kwargs)` op de fire-site. O.a. `pre_tool_call`/`post_tool_call` (rond elke tool-executie), approval-lifecycle-hooks, streaming-observers (asynchroon, off het token-pad, immutable payloads), gateway pre-dispatch, STT-transform, kanban-lifecycle. `gateway/builtin_hooks/` is een leeg, bewust extension point ("none shipped" — geen speculatieve hooks).

Config-mechanisme:

- **Eén YAML**: `~/.hermes/config.yaml` als bron van waarheid voor alle gedrag; defaults + migratie in `hermes_cli/config.py` (`DEFAULT_CONFIG`, `OPTIONAL_ENV_VARS`).
- **Beleid** (hard in AGENTS.md): `.env` is uitsluitend voor secrets; alle gedragsinstellingen (timeouts, thresholds, flags) in config.yaml; nieuwe `HERMES_*`-env-vars voor niet-secrets worden afgewezen.
- **Profiel-isolatie**: elk Hermes-profiel (`hermes -p <naam>`) krijgt een eigen HERMES_HOME (config, geheugen, sessies, gateway-PID) — meerdere profielen draaien naast elkaar.
- **Plugin-config-naamruimte**: `plugins.<plugin-id>.*` in config.yaml (zo leest agent-brain zijn `brain_path` via `cfg_get(config, "plugins", "agent-brain")`).
- Gestructureerde lagen zichtbaar in de echte config.yaml: `model`, `agent`, `terminal`, `browser`, `tool_loop_guardrails` (warn/hard-stop per categorie), `compression`, `prompt_caching`, `memory` (provider-selectie + limieten), `delegation`, `skills`, `code_execution` — alles typed en gedocumenteerd.

### Oordeel

**Hergebruiken als patroon:**
- **"config.yaml voor gedrag, .env uitsluitend voor secrets"**: adopteer dit woordelijk in GrowKit. Het voorkomt de env-var-soep die het ontwerpdoc's "reviewer-rol configureren zonder leveranciers-binding" (open punt 5) anders dreigt te worden.
- **Hook-fouten blokkeren nooit de pipeline**: elke extensie in het harnas (loggen, UI-notificaties, toekomstige poort-controles) moet vallen-bij-fout zijn zonder de bewijsketting te breken.
- `pre_/post_tool_call`-vorm rond executie: voor GrowKit is dit de natuurlijke plek waar append-only logging en bewijs-verificatie hangen — elke stap: pre-check (scope-poort) → execute → post-check (bewijs) → log. Dat is letterlijk de fase-4-loop uit §11.4/§3.
- Één platte naamruimte per extensie (`plugins.<id>.*`): schaalbaar zonder nieuw mechanisme.

**Bewust niet overnemen:**
- Twee parallelle hook-systemen (event-hooks + plugin-hooks): voor een harnas is één simpel punt (pre/post rond de stap) genoeg; een tweede systeem is onderhoud zonder consument (Hermes' eigen AGENTS.md noemt speculatieve hooks expliciet ongewenst).
- Config-migratie-mechanisme, profielen-isolatie, skin-engine en de ±100KB `cli-config.yaml.example`: platformproduct-gewicht.

---

## 9. De 5 belangrijkste patronen om te hergebruiken

1. **Eén wire-formaat als smalste punt (`chat_completions`) + declaratieve mini-profielen.** Provider-agnosticisme door alles OpenAI-compatibels in één mode te doen en provider-verschil te reduceren tot (name, base_url, api_key, model)-data. GrowKit-vertaling: rollen (`uitvoerder`, `reviewer`) die naar (endpoint, key, model) mappen in één eigen config-bestand — §9/open punt 5 uit het ontwerpdoc zijn hiermee gedekt.
2. **De loop-invarianten**: OpenAI-berichtformaat intern, strikte rol-alternatie, tool-resultaten in call-volgorde, onderbreekbare API-aanroep met discard-bij-interrupt, en een iteratie-/falingsbudget dat uitmondt in "stop en vat samen" (bij GrowKit: stop en roep de mens). Dit is het skelet van `loop.py` in ±150 regels.
3. **Bewijs-gefundeerde tool-executie met guards**: idempotent/mutating-classificatie per tool (→ GrowKit's `idempotent`-veld), per-categorie warn/hard-stop-drempels (→ `bij_falen`: één alternatief, dan mens), error-bounding van tool-output vóórdat het het model bereikt, en state-mutaties (het logboek) afgedwongen door de loop zelf in plaats van aangeboden als model-tool. Hermes' `agent/tool_guardrails.py` is hier het referentie-ontwerp, en het is bewust *pure* (side-effect-vrije) code — makkelijk over te zetten.
4. **Memory-ABC in Agent-Brain-vorm**: alleen-lezen bron + append-only VOORSTEL-inbox + mens als curator, met budgeteerde prompt-injectie (<2k) en triviaal-invoer-gating. Dit is de motor van het groeivliegwiel (§11.2) in twee ABC-methodes (lees/voorstel), bewezen in productie bij de gebruiker.
5. **Config-discipline**: één YAML voor alle gedrag, .env alleen voor secrets, één naamruimte per extensie, fallibele hooks die nooit de pijplijn blokkeren, en — bovenal — een *smalle taille*: capaciteit groeit door documenten (skills/profielen) en rand-tools, niet door de kern te verbreden. GrowKit's Scope-poort (§11) is dit principe toegepast op invoer.

## 10. Wat ik afraad over te nemen

- **De god-files**: `run_agent.py` (427 KB) en `cli.py` (1 MB) zijn de anti-voetstukken van "paar honderd regels". Niets van hun omvang is nodig voor het harnas; als het harnas meer dan ±500 regels wordt, is het fase-4-doel al geschonden.
- **Drie api-modes + per-leverancier adapters** (anthropic/gemini/codex-native): klinkt als "meer provider-agnostisch", is in werkelijkheid 10× onderhoud voor 5% dekking bovenop OpenAI-compatibel. Groeit pas als een concreet profiel erom vraagt.
- **Contextcompressie en prompt-caching-infrastructuur**: noodzakelijk voor 500-turn-gesprekken, doodgewicht voor bewijs-per-stap-taken. Ook: het schema-bewijs van GrowKit stelt juist dat de *volledige* stap-geschiedenis leesbaar blijft.
- **Auto-discovery (AST-scans), parallelle tool-executie, sessie-DB met FTS5, MCP-client, skills-hub met trust-levels, tweede hook-systeem**: allemaal oplossingen voor problemen die GrowKit in fase 4 niet heeft. Het ontwerpdoc zegt het zelf: geen harnas-investering vóór fase-2-bewijs, en "geen framework".
- **Hermes' generöze retry/fallback-ketens** als gedragsmodel: GrowKit's faalcontract (één alternatief, dan mens, altijd append-only gelogd) is bewust strenger en moet de loop blijven beheersen — de guardrail-logica overnemen, de retry-geduldigheid niet.

## 11. Bronnen

- Lokaal: `~/.hermes/hermes-agent/` (v0.20.5, editable git-install) — `run_agent.py`, `agent/` (memory_provider.py, tool_guardrails.py, prompt_builder.py, skill_commands.py, conversation_loop.py), `tools/` (registry.py, mcp_tool.py, approval.py), `providers/base.py`, `hermes_cli/` (runtime_provider.py, plugins.py, mcp_catalog.py, config.py), `gateway/hooks.py`; `~/.hermes/` (config.yaml-structuur, skills/, plugins/agent-brain/).
- Docs: hermes-agent.nousresearch.com/docs — developer-guide (architecture, agent-loop, provider-runtime, tools-runtime), user-guide/features (skills, mcp).
- Publiek: github.com/NousResearch/hermes-agent (MIT).
- GrowKit: `docs/superpowers/specs/2026-09-03-growkit-design.md` (§3–§5, §8 fase 4, §9, §11).
