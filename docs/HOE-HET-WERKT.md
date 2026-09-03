# Hoe GrowKit werkt — de complete uitleg

Dit document legt de werkelijke, gebouwde werking uit (fase 1-4, bewezen met
machine-bewijs). Bron van waarheid voor het ontwerp:
`docs/superpowers/specs/2026-09-03-growkit-design.md`. Dit document beschrijft
hoe het *is*, niet hoe het ooit bedacht was.

## De kerngedachte in één alinea

GrowKit gaat er vanuit dat de AI fouten kan maken — zero-trust. Daarom ligt de
interpretatie van "is het gelukt?" nooit bij de AI, maar bij een deterministische
controlelaag die de AI niet kan omzeilen. De AI is de tuinier: hij plant, snoeit
en stelt voor. De mens is de curator: hij bevestigt, ratificeert en promoveert.
Elke stap produceert machine-bewijs of wordt expliciet een mens-moment. Er is
geen pad waar de AI "zegt dat het gelukt is" en dat als waarheid telt.

## De drie wetten

1. **Niets draait zonder bevestigde scope.** De Scope-poort weigert vage
   invoer; wat de poort niet vrijgeeft, kan de agent niet uitvoeren.
2. **Succes is bewijs, nooit een claim.** Vijf gecodeerde checktypes worden
   door de motor zelf uitgevoerd. De AI leest terminal-output en interpreteert
   — het bewijs-programma beslist.
3. **De geschiedenis is append-only.** Er wordt nooit overschreven of
   teruggedraaid; afkeuring leidt tot nieuwe status-entries, nooit tot mutatie
   van het verleden. Wat erop voortbouwt staat in het logboek en is zichtbaar.

## De stukken en hun rol

| Stuk | Wat het doet |
|---|---|
| `SEED.md` | Geboortebrief: rol, regels en leesroute voor de geleende agent. De motor voert uit; de agent bedient. |
| `seed.py` | Plant-mechanisme: kiemkeuze, vrije beschrijving, slijper-logboek, profiel laden, motor starten. |
| `loop.py` | Het harnas (fase 4): dunne orchestratieloop met vijf modi — planten, hervatten, taak, ratificatie, status. Draait zonder AI-agent (alleen Python + terminal-invoer). |
| `kern/growkit_poort.py` | Scope-poort: drie invoertypes, vaste weigeringsteksten, vragenlijst per ontbrekend veld, gelabelde standaardwaarden. Interpreteert nooit inhoud. |
| `kern/growkit_motor.py` | Stappen-motor: voert commando's uit, toetst bewijs, probeert precies één alternatief bij falen, logt append-only. |
| `kern/growkit_bewijs.py` | De vijf bewijscontroles (zie onder). De AI kan dit bestand niet "overtuigen" — het is code. |
| `kern/growkit_review.py` | Review-laag: leest rollen uit `reviewconfig.json`, roept de reviewer provider-agnostisch aan, vertaalt naar exact drie oordelen. |
| `kern/growkit_leesroute.py` | Leesroute-afdwinging: per fase injecteert de loop/seed alleen de content die toegestaan is. |
| `kern/growkit_hervat.py` | State-reconstructie: leest het logboek na een crash en beslist per stap: overslaan, heraanbieden of uitvoeren. |
| `kern/growkit_taken.py` | Takenlijst van de groeilaag: taken bestaan alleen mét bewijs-check. |
| `profielen/` | De bomen: `profiel.json` (stappenplan met gecodeerd bewijs) + `sjablonen/`. |
| `groei/` | Groeilaag-documentatie (`SETUP.md`) en het slijper-logboek. |
| `tests/` | 110 unit-tests (unittest) + vijf E2E-shellscripts. |

## De levensloop van een opdracht

```
vrije beschrijving ("dit is een bui")
  → poort: ontbrekende velden → vragenlijst (alleen over wat écht ontbreekt)
  → complete velden → concept (letterlijk samengevoegd, plus bron.ruwe_invoer)
  → ontbreekt alleen omgeving → gelabelde standaardwaarde (standaardwaarde: true + bron)
  → mens-bevestiging: "klopt dit? (ja / pas aan)" — pas na "ja" bestaat de opdracht
  → (≥ drempel stappen) mijlpaal-blok: begrepen / afgesproken / bewijs / hierna — één bevestiging
  → motor: per stap commando → bewijs-check → append-only logboek-entry
       geslaagd → volgende stap
       gefaald → precies één alternatief_commando → nog steeds faal → stop, exit 2, de mens
       mens_verificatie-stap → reviewer (indien geconfigureerd) of direct de mens
  → ratificatie in bulk: één bevestiging over alle review_ok-stappen
       "ja"           → per stap een vervolg-entry `geratificeerd`
       afkeur "1"     → `herziening_nodig` + doorloop-vermelding; géén auto-rollback
```

Bij een crash (bijv. `kill -9` of sessie-einde) neemt de hervat-modus over:
`reconstructie(logboek, profiel)` beslist per stap:

- `geslaagd` of `review_ok_wacht_ratificatie` of `geratificeerd` → **overslaan**
  (niet-idempotent geslaagde stappen krijgen de noot "nooit herdraaien" — hard);
- `wacht_op_mens`, `gefaald` of `herziening_nodig` → **heraanbieden** (na mens-fix);
- geen logregel → **uitvoeren**;
- onbekende status → heraanbieden mét noot (nooit stilzwijgend overslaan);
- corrupt logboek → `corrupt_logboek`: de mens, nooit auto-reparatie.

De restdraai draait uitsluitend de heraanbieden/uitvoeren-stappen door de
ongewijzigde motor. Het herstartpunt is de laatste bevestigde mijlpaal.

## De vijf bewijs-types

| Type | Mechanisme | Vangt af |
|---|---|---|
| `shell_check` | check-commando draait; output moet `verwacht_substr` bevatten (letterlijke substring) | foutpatronen in terminal-output |
| `file_exists` | pad bestaat (optioneel `bevat`-tekst) | missende bestanden/mappen |
| `json_valid` | valide JSON met `top_level` / `exacte_lengte` / `verplicht_veld` | kapotte of incomplete data |
| `file_equals` | byte-voor-byte gelijk aan het sjabloon (SHA256 via `hashlib`) | stiekeme wijzigingen — "stealth-hallucinaties" |
| `http_check` | URL reageert met `verwacht_status` | onbereikbare of foutieve diensten |

Voorwaarden zijn altijd gecodeerde vaste velden — nooit vrije tekst die een
model moet interpreteren. Bestandsinhoud komt via sjabloonbestanden en
deterministische kopieer-commando's (geen heredocs in JSON).

## Het faalcontract

Eén stap, één poging, één alternatief, dan de mens. Er is geen retry-teller,
geen "nog één keer proberen", geen creatieve bash-hack. Daarmee zijn de twee
klassieke agent-falen — self-reported success en oneindige herstellussen —
structureel onmogelijk. Exit-codes: `0` geslaagd, `1` geen opdracht of geen
bevestiging, `2` motor-faal (mens geroepen).

## De Scope-poort in detail

Drie invoertypes, elk met vaste weigeringsteksten:

1. **Kiemkeuze** — profiel + doelmap verplicht; anders: "Ik ga niet raden wat
   je bedoelt; ik ben een tuinier, geen helderziende."
2. **Vrije beschrijving** — `einddoel`, `omgeving`, `slaag_criterium`
   verplicht. Ontbreekt er iets, dan krijg je uitsluitend vragen over wat écht
   ontbreekt. De enige invul die de slijper mag doen: de gelabelde
   standaardwaarde voor omgeving (`standaardwaarde: true` + bronvermelding).
   Het einddoel wordt **nooit** ingevuld — dan volgt een vraag. Omgevingsdetectie
   (§11.3-3b) mag deze standaard aanbieden op basis van aanwezigheid van
   `profielen/<boom>/vps-doel.json` — de inhoud daarvan wordt nooit gelezen.
3. **Taak** — zonder bewijs-check bestaat de taal-taak niet; de poort weigert
   en er wordt niets uitgevoerd.

## De review-laag in detail

- Configuratie: `reviewconfig.json` (repo-niveau, in `.gitignore` — per-machine).
  Vorm: `{"rollen": {"reviewer": {"type": "cli" | "http", ...}}}`. Velden als
  `model`, `provider` of `leverancier` zijn een **schema-fout** — GrowKit kent
  alleen rollen, geen leveranciers.
- Transport: cli-reviewers via `shlex.split` + `shell=False` + stdin (de
  uitvoer van een eerdere stap komt nooit in een shell-string); http via POST.
- Oordeel: exact-match op `geslaagd` / `gefaald` / `onduidelijk`. Time-out of
  crash → `onduidelijk` → de mens. Geen vrije tekst-parsing.
- Ratificatie-semantiek: `review_ok_wacht_ratificatie` stopt de motor niet —
  latere stappen mogen voortbouwen (logbaar). Definitief is de stap pas na de
  bulk-ratificatie door de mens. Afkeuring → `herziening_nodig`, geen rollback.

## Wat GrowKit bewust níét doet

- **Geen model-aanroepen in de kern.** De enige LLM-contactpunten zijn de
  geleende agent (die seed.py/loop.py bedient) en de reviewer via jouw eigen
  reviewconfig. GrowKit heeft geen leverancier en geen pip-dependencies.
- **Geen sandboxing of prompt-injectie-afweer van tool-output** (spec §14,
  fase-5+ materiaal). De huidige grens: alleen gecodeerde stappen uit
  poort-gevalideerde profielen/taken worden uitgevoerd, en stap-output wordt
  nooit als commando geïnterpreteerd.
- **Geen auto-rollback, geen auto-reparatie.** Interpretatie is voor de mens;
  het systeem raadt niet.
- **Sessie-beheer van de omringende agent** (sessie-reset, toolsets, contexthygiëne)
  leeft buiten GrowKit — elke omgeving mapt dat zelf.

## De groeilaag en het oerwoud

Na het planten blijft `groei/` (in de boom) permanent bestaan: append-only
logboek, takenlijst (alleen taken mét bewijs) en de inbox met VOORSTEL-status.
Fase 5 (oerwoud) registreert meerdere bomen bij één gedeeld brein via het
geboortebewijs (boom-id, profiel, machine, locatie). Harde drift-guard: het
brein bevat uitsluitend universele context; omgevings-specifieke staat (paden,
poorten, ssh-doele, sleutels) blijft lokaal per boom en wordt nooit gesynct.

## Bewijs-status (3 sept 2026)

Fase 1-4 bewezen: Test 1 (schone-pleg-plant) 7/7 · Test 2 (vrije beschrijving)
5/5 · Test 3 (review-laag) 5/5 · Test 4 (harnas zonder agent + crash-herstart)
6/6. Eindstand: 110 unit-tests groen, vijf E2E-scripts groen. Zelfreviews:
`docs/superpowers/bewijs/fase-3-zelfreview.md` en `fase-4-zelfreview.md`.
