# Bouwplan: Skills-beheer · Telegram Connect · Eigen LLM (CyberSeed)

**Status:** plan (6 sept 2026) — uitvoering in fases, elke fase apart
commitbaar en CI-bewaakt. Prioriteit in deze volgorde.

---

## Functie A — Skills-beheer (scherm 20 · SYSTEEM)

**Wat:** alle geïnstalleerde skills inzien, lezen, bewerken — en een AI
een skill laten herschrijven op basis van een prompt.

**Achtergrond:** skills staan lokaal in `~/.hermes/skills/<naam>/SKILL.md`
en op de VPS in `/root/.hermes/profiles/<profiel>/skills/`. De app leest
ze via SSH; de AI-bewerking loopt via de chat-pijplijn (KairOS), zodat
de gouverneur-kosten en het faalcontract gelden.

**Fase A1 — kern (TDD):**
- `kern/growkit_skills.py`:
  - `lijst_bron()` → paden van beide locaties (Mac-lokaal via direct,
    VPS via SSH `ls`);
  - `lees(bron, naam)` → SKILL.md-inhoud;
  - `schrijf(bron, naam, inhoud)` → schrijft NIEUWE inhoud; maakt eerst
    een backup `SKILL.backup-<ts>.md` (append-only geest);
  - `valideer(inhoud)` → heeft frontmatter, minstens één kop; secrets-
    scanner weigert keys.
- Adapter: `skillslijst`, `skillslees`, `skillsschrijf` (met backup),
  `skillsvoorstel` (prompt → KairOS herschrijft, antwoord = volledige
  SKILL.md als markdown-codeblok; app toont diff vóór opslaan).

**Fase A2 — scherm:** lijst links, inhoud rechts (monospace), knoppen:
[Bewerk met AI] (prompt-veld erboven) → diff-weergave → [Pas toe] /
[Wegwerp]. Backup terugdraaien kan vanuit hetzelfde scherm.

---

## Functie B — Telegram Connect (scherm 21 · SYSTEEM)

**Wat:** de gebruiker stap voor stap begeleiden bij het koppelen van een
eigen Telegram-bot aan de Agent-Brain.

**Fase B1 — wizard-scherm (statisch, 6 stappen):**
1. Praat met @BotFather → `/newbot` → naam + gebruikersnaam → token.
2. Plak de token in het veld (toon alleen laatste 4 tekens; bewaar via
   `security add-generic-password` in de Sleutelhangar — nooit in de repo).
3. Vraag je chat-ID op via @userinfobot (of stuur /start naar de nieuwe bot).
4. Vul `config.yaml` van het profiel: `telegram.token`,
   `telegram.allowed_chat_ids`, `home_channel`.
5. Herstart de gateway (knop toont het exacte commando; uitvoeren blijft
   bij de gebruiker — systeemgrens).
6. Test: stuur "/status" naar de bot → verwacht een antwoord van de agent.

**Fase B2 — levende status:** de app toont of de bot reageert (levens-
signaal via de bestaande agentstatus) en toont de laatste fout uit het
gateway-logboek als hij niet reageert. Connectiestatus-kleuren: groen
(online), oranje (token gezet, geen reactie), grijs (niet ingesteld).

**Geen automatische bot-aanmaak** — BotFather vraagt interactie in
Telegram zelf; de wizard begeleidt, de mens doet de stappen.

---

## Functie C — Eigen lokaal LLM "CyberSeed" (scherm 22 · SYSTEEM)

**Wat:** een lokaal draaiend LLM op de Mac (via Ollama, dat er al staat)
dat een **eigen, automatisch bijgewerkte SOUL.md** krijgt — een samenge-
vatte, actuele snapshot van wie Tiëndo is, wat hij doet en waar hij aan
werkt. Zo voelt elk nieuw gesprek als een vervolg op hetzelfde lange
gesprek, zonder context-window-problemen.

**Bronnen (Drive, gelezen):**
- *Strategisch Implementatieplan: Transitie naar Lokale AI-Infrastructuur*
  (Ollama-engine, keep_alive 24h, context ≥32k, lokale stack, ongecensureerde
  varianten als optie);
- *AI-agenten op de Mac — naslagwerk* (Ollama praat OpenAI-compatibel HTTP —
  GrowKit kan er rechtstreeks langs; `~/.ollama/models/` staat al op deze Mac).

**Fase C1 — fundament (TDD):**
- `kern/growkit_lokaalmodel.py`:
  - `ollama_bereikbaar()` → GET `http://localhost:11434/api/tags`;
  - `model_getrouw()` → herkent een "cyberseed"-model in de tag-lijst
    (downloadsuggestie als het ontbreekt: bijv. `qwen3:8b` of `gemma3:8b`, daarna lokaal getagd als `cyberseed:8b`);
  - `soul_snapshot()` → genereert de actuele SOUL-snapshot uit bestaande
    GrowKit-bronnen (géén nieuwe infra):
    profiel (`profiel lees`) + laatste N logboekregels (`audit`) +
    openstaande ratificaties (`ratificeer lijst`) + saldo (`saldo`) +
    actieve bomen (`bomen`) + samenvatting van de laatste chatdraad.
    Vast formaat, ≤ 4k tokens, gestructureerd (kopjes + bullets);
  - `soul_snapshot_bewaar()` → `~/.growkit/cyberseed/SOUL.md`;
  - `chat(bericht)` → POST naar Ollama `/api/chat` met
    `system: inhoud van SOUL.md` + `keep_alive: 24h`;
  - `verfris_soul_cron()` → idempotente functie voor de Mac-cron:
    elke 48h (of handmatig) snapshot opnieuw genereren.
- Tests: snapshot-formaat, determinisme bij vaste invoer, Ollama-mock
  (HTTP-fout = nette fout), contextgrootte-bewaking (>4k → afkappen met
  melding).

**Fase C2 — Mac-cron:** `launchd`/cron-item (elke 48h om een rustig uur)
dat `verfris_soul_cron()` draait. Aan/uit-knop in het scherm.

**Fase C3 — scherm (SYSTEEM):**
- Statuskaart: Ollama draait? model aanwezig? SOUL-leeftijd (uren)?
- Knoppen: [Genereer SOUL nu] [Chat openen] [Model-suggestie tonen].
- Chatvenster in dezelfde stijl als Agent Chat (met Thought-blok uit),
  maar lokaal: het `van`-veld heet hier de gebruikersnaam uit het profiel.
- Privacybord: "Dit model draait volledig op deze Mac. Niets verlaat het
  huis." (dat is de kern van je Drive-bron.)

**Fase C4 — later (optioneel):** VPS-koppeling (CyberSeed ook op de
server), fijn-afstemming op eigen chatgeschiedenis (LoRA) — bewust **niet**
in dit plan; eerst het basis-loopje bewijzen.

---

## Volgorde van uitvoering

| Fase | Inhoud | Bewijs |
|---|---|---|
| A1 | Skills-kern + adapter | unittests |
| A2 | Skills-scherm | build + visueel |
| B1 | Telegram-wizard (statisch) | build + visueel |
| B2 | Levende status | agentstatus-integratie |
| C1 | Lokaalmodel-kern + SOUL-snapshot | unittests + E2E tegen echte Ollama |
| C2 | Mac-cron | launchd aan/uit bewezen |
| C3 | CyberSeed-schermirOS-mini-scherm | build + visueel + eerste lokaal gesprek |

Elke fase: eigen commit, CI moet groen, push pas na akkoord.
