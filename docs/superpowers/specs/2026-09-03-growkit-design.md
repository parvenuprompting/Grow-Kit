# Ontwerp — GrowKit

Datum: 3 september 2026
Status: goedgekeurd in brainstorm (Tiëndo + Mac Hermes); v2 na externe review (Claude) — model-switch, harnas-beslissing, groeifases-roadmap, keuze eerste profiel; v3 — spelling GrowKit, naamcollisie definitief, fase-1-naam, Scope-poort (§11)

## 1. Wat het is

GrowKit (spelling: GrowKit; repo- en mapnamen blijven lowercase `growkit/`, volgens code-conventie) is een **zelfstandig product**: een repo die na installatie vanzelf "ontkiemt". Een AI-agent leest een korte geboortebrief, laat de gebruiker een groeiprofiel kiezen, voert een stappenplan uit mét machine-geverifieerd bewijs, en zet daarna een levenslange groeilaag op. De gebruiker plant met één actie; de agent doet de rest en vraagt de mens alleen bij echte mens-momenten.

**Belangrijke grens:** GrowKit staat volledig los van Tiëndo's eigen omgeving (Agent-Brain, VPS-configuratie). Het is géén kopie of kloon van zijn setup — zijn tweede-brein-werkwijze inspireert de *vorm* van het eerste profiel, niet de inhoud. GrowKit schrijft nooit terug naar bestaande systemen van de gebruiker.

Metafoor: zaadje → kiemkeuze → plant → boom. Later mogelijk meerdere bomen (oerwoud).

Kernprincipes:

- De mens is de baas; de agent executeert.
- **Machine-toetsbaar bewijs** — seed.py verifieert het resultaat zelf; de agent claimt nooit zelf succes (§3).
- Append-only loggen; de agent stelt voor, de mens keurt goed.
- Leesroute wordt **afgedwongen door het script**, niet alleen afgeraden in de brief (§5).
- **Provider-agnostisch** — geen enkele binding aan één AI-leverancier; de gebruiker mapt modellen via zijn eigen configuratie (OpenRouter of anders).

## 2. Naam en positionering

- Productnaam: **GrowKit** (Engels, herbruikbaar buiten het Nederlandstalige ecosysteem).
- De inhoud — profielen, geboortebrief, logboek — blijft Nederlandstalig.
- Naamcheck 3 sept 2026, definitief: `grokit` op PyPI bestaat, maar is een **onofficiële Grok-chat-client** (bèta, laatste release okt 2024, ±17 stars) — ander domein dan agent-tooling, geen actieve concurrent. Eén-letter-typorisico (`pip install grokit`) is reëel; mitigatie: GrowKit verspreidt zich in fase 1–2 **als git-repo** (`git clone`), niet als PyPI-pakket — zolang er geen pip-distributie is, is de collisie praktisch niet aan de orde. Bij een toekomstige PyPI-release opnieuw checken. GrowKit.com (paddenstoelen) en Pimoroni "Grow Kit" (hardware) zijn andere markten.

## 3. Bewijs: machine-toetsbaar, niet zelf-gerapporteerd

Risico bij zelf-gerapporteerd bewijs: de agent die uitvoert is dezelfde die het bewijs interpreteert, en kan een foutmelding als succes lezen omdat het plan dat verwacht.

Oplossing: bewijs is waar mogelijk een expliciete check die **seed.py zelf uitvoert**, met een vaste set types en eigen verificatiefuncties:

- `shell_check` — commando draait, output bevat een gecodeerde voorwaarde (`verwacht_substr`)
- `http_check` — URL reageert met verwachte status (`verwacht_status`)
- `file_exists` — pad bestaat (optioneel: `bevat`-tekst)
- `json_valid` — valide JSON met gecodeerde voorwaarden (`top_level`, `exacte_lengte`, `verplicht_veld`)
- `file_equals` — bestand is byte-voor-byte gelijk aan een sjabloon uit `profielen/<profiel>/sjablonen/`

Twee harde regels: voorwaarden zijn altijd **gecodeerd** (vaste velden), nooit vrije tekst die een interpreter moet lezen. En bestandsinhoud wordt aangeleverd via **sjabloonbestanden** die met deterministische commando's worden gekopieerd — geen heredocs in JSON.

Kan een stap niet machine-toetsbaar, dan is de stap expliciet gemarkeerd **mens_verificatie** en telt niet als automatisch bewijs; zo'n stap kan een reviewer-model als eerste blik krijgen (§9).

## 4. Stappen-schema (JSON)

```json
{
  "id": "stap-003",
  "commando": "docker compose up -d",
  "verwacht": "container 'growkit-sync' draait",
  "bewijs": {
    "type": "shell_check",
    "check": "docker ps --filter name=growkit-sync --format '{{.Status}}'",
    "verwacht_substr": "Up"
  },
  "mens_nodig": null,
  "bij_falen": {
    "alternatief_commando": "docker compose up -d --force-recreate",
    "anders": "roep_mens"
  },
  "idempotent": true,
  "review": null
}
```

- `bewijs.type` — een van de vaste set uit §3; de agent claimt niet zelf succes.
- `mens_nodig` — `null` tenzij de stap browser-auth of API-sleutel-invoer vereist. Altijd op de doelmachine zelf, nooit secrets in de chat.
- `bij_falen` — precies één alternatief; lukt dat ook niet → mens. Geen verdere retries zonder mens.
- `idempotent` — of seed.py de stap bij hervatting veilig opnieuw mag draaien of eerst moet controleren of hij al (deels) is uitgevoerd. Elke stap die bestanden aanmaakt, mappen initialiseert of externe diensten aanroept zet dit veld expliciet.
- `review` — `null` voor stappen met machine-bewijs; een **rolverwijzing** (`"reviewer"`) voor mens_verificatie-stappen (§9). Nooit een hardcoded leveranciers-modelnaam.

## 5. Leesroute-afdwinging

De leesroute is geen gedragsadvies maar een **grens die het script afdwingt**: seed.py ontsluit profielbestanden pas per fase. Voorkeursimplementatie (voor het implementatieplan): seed.py injecteert de inhoud rechtstreeks aan de agent per fase, in plaats van te verwijzen naar een pad — wat de agent niet kan zien, kan hij niet lezen. Implementatiekeuze wordt vastgelegd in het plan.

## 6. Repo-structuur

```
growkit/
├── SEED.md            ← geboortebrief: eerste wat de agent leest
├── seed.py            ← opstartscript (python seed.py)
├── profielen/
│   ├── INDEX.md           ← kiemkeuze: welke boom? (standaard + vrij beschrijven)
│   ├── tweede-brein/      ← eerste profiel — GENERIEK (§10)
│   ├── autonome-fabriek/
│   └── dev-werkplaats/
└── groei/             ← levenslange laag ná installatie
```

### SEED.md — skeleton

```markdown
# Geboortebrief

Jij bent vanaf nu de tuinier van dit zaadje. Je rol: dit stappenplan
uitvoeren, bewijs verzamelen, nooit claimen dat iets gelukt is zonder bewijs.

## Regels
1. Lees alleen het bestand dat de leesroute op dit moment aanwijst.
2. Voer een stap pas uit na het lezen van het bijbehorende profiel-JSON.
3. Bij falen: probeer het alternatief_commando, anders roep de mens.
4. Log elke stap in groei/logboek.json vóór je verdergaat.

## Leesroute
- Fase 0 (nu): dit bestand
- Fase 1: profielen/INDEX.md (kiemkeuze — welke boom?)
- Fase 2: profielen/<gekozen-profiel>/stappenplan.json
- Fase 3: groei/SETUP.md (initialiseren van de groeilaag)

Lees niets buiten deze route tenzij een stap dat expliciet vraagt.
```

## 7. groei/ — de groeilaag

Blijft na installatie permanent bestaan:

- `logboek.json` — append-only log van elke stap, inclusief het machine-geverifieerde bewijs. Bij crash of nieuwe sessie leest de agent dit om te bepalen waar hij was en welke stappen (op basis van `idempotent`) veilig herhaald kunnen worden.
- `takenlijst.md/json` — taken die de agent zelf oppakt en afdwingt mét bewijs, volgens hetzelfde schema als §4.
- `inzichten-inbox/` — voorstellen van de agent (status VOORSTEL); de mens curatieert. Nooit overschrijven, alleen toevoegen; promotie doet de mens.

## 8. Groeifases — roadmap van het product zelf

De roadmap volgt de eigen metafoor. Elke fase bewijst iets voordat de volgende begint:

| Fase | Naam | Wat | Bewijst |
|---|---|---|---|
| 1 | Stappenplan | Echte stappenplannen (geen voorbeelden), uitgevoerd via een bestaande agent van de gebruiker | Dat het stappenplan-formaat in de praktijk werkt |
| 2 | Kieming | seed.py met machine-bewijs + Test 1 (tweede-brein op schone plek) en Test 2 (vrije beschrijving) | Dat bewijs-afdwinging en leesroute werken |
| 3 | Review-laag | `review`-rol voor mens_verificatie-stappen (§9) | Dat de mens minder vaak nodig is |
| 4 | Eigen harnas | Dunne provider-agnostische orchestratieloop (paar honderd regels, geen framework) — alléén na fase 2 | Dat GrowKit een zelfstandig product is zonder agent-dependency |
| 5 | Oerwoud | Meerdere bomen (instanties) registreren bij één gedeeld tweede-brein; identiteit, voorkeuren en VOORSTELLEN syncen via dat ene brein (§13) | Dat één brein het centrum van een heel ecosysteem kan zijn |

Fase-namen zijn bewust géén metafoor-termen: "zaadje" is gereserveerd als metafoor voor het héle product, niet als fase-naam — dubbelzinnigheid voorkomen in plannen die code-agents lezen.

Beslissing: de **geleende-agent-modus is een feature, geen noodoplossing** — "werkt met je bestaande agent" is de lage instapdrempel. Het eigen harnas (fase 4) is de latere Pro-laat en wordt pas gebouwd nadat fase 2 is bewezen. Geen harnas-investering vóór bewijs.

## 9. Review door tweede model (provider-agnostisch)

Idee: tijdelijk een ander model voor review/checks, daarna terug naar het uitvoerende model.

- **Oplost:** onafhankelijke blik zonder gedeelde blinde vlekken; vermindert het aantal stappen dat bij de mens terechtkomt (mens_verificatie-stappen).
- **Lost níet op:** leest het reviewmodel dezelfde tekstuele output, dan interpreteert het dezelfde mogelijk misleidende data — interpretatie, geen verificatie. Machine-bewijs (§3) blijft daarom eerste keuze.
- **Provider-agnostisch:** de stap verwijst naar een **rol** (`"reviewer"`), niet naar een leveranciers-modelnaam. De gebruiker mapt rollen naar modellen in zijn eigen configuratie (bijv. OpenRouter). Wisselen van model is per stap, niet per sessie; na de reviewstap keert het uitvoerende model terug.
- **Gedrag:** reviewer krijgt alleen output + verwacht-omschrijving en oordeelt geslaagd/gefaald/onduidelijk. Bij "onduidelijk" wordt alsnog de mens geroepen — de reviewer vermindert mens-inzet, vervangt de mens niet.
- **Kosten/latency:** alleen zinvol als een profiel substantieel veel mens_verificatie-stappen heeft; voor profielen met overwegend machine-bewijs is de winst beperkt.

## 10. Eerste profiel: tweede-brein — GENERIEK

Beslissing (optie A): het eerste profiel is een **generieke tweede-brein** — de bewezen *vorm* (mappenstructuur met identiteit/kennis/projecten/inbox, append-only log, inbox met VOORSTEL-status, mens als curator), maar:

- geen enkele verwijzing naar Tiëndo's machines, zijn VPS, zijn brein of zijn synchronisatie-taken;
- het profiel staat op zichzelf en is herbruikbaar voor elke gebruiker;
- bij het schrijven wordt de inhoud van Agent-Brain niet geraakt — alleen de vorm, uit het hoofd en uit dit ontwerp, afgeleid.

De vaste kern van het profiel: `identiteit/`, `kennis/`, `projecten/`, `inbox/`, `logboek/` — vijf mappen. Alles daarbuiten (stem/, ideeën/, prompts/, configuraties/ …) is **optioneel** en duidelijk gemarkeerd; de twaalf-mappen-variant uit de review wordt niet overgenomen. Bestandsinhoud komt uit `profielen/tweede-brein/sjablonen/` en wordt gekopieerd met deterministische commando's; het bewijs is `file_equals`.

De echte stappen van dit profiel worden in het implementatieplan uitgewerkt (open punt 2 uit §12).

## 11. De Scope-poort — geen actie zonder heldere scope

Principe: **GrowKit voert niets uit zonder heldere scope.** De poort beoordeelt niet of een prompt "goed" of "dom" is — kwaliteitsbeoordeling is interpretatie en blijft bij de mens (§3-les). De poort controleert alleen of de **verplichte structuur** aanwezig is. Ontbreekt die, dan bestaat de opdracht als opdracht niet: het script weigert en doet niets.

| Invoer | Verplicht aanwezig | Anders |
|---|---|---|
| Kiemkeuze | gekozen profiel + doel-locatie | script voert niets uit |
| Vrije beschrijving (nieuwe boom) | einddoel + omgeving (lokaal/VPS) + slaag-criterium | weigering + concrete vragenlijst |
| Taak in de groeilaag | bewijs-check per taak (§4-schema) | taak is ongeldig en bestaat niet |

Weigeringstoon: vaste, droge maar nette weigeringsteksten (Nederlands) plus de concrete vragen die wél tot actie leiden. Voorbeelden:

> "Dit is nog geen opdracht — dit is een bui. Noem: wat wil je laten groeien, waar, en wanneer is het geslaagd. Dan plant ik."

> "Ik ga niet raden wat je bedoelt; ik ben een tuinier, geen helderziende. Drie vragen: doel, plek, slaag-criterium."

### 11.1 De Prompt-slijper — ruwe invoer wordt pas opdracht na schuring en goedkeuring

Aanvulling op de poort: een mechanisme dat elke vage prompt **optimaliseert vóór uitvoering** — zonder het §3-risico te lopen dat het systeem verzint wat de gebruiker "eigenlijk" bedoelde en dat dan uitvoert.

De werkwijze (in de geest van de kernregel: de agent stelt voor, de mens keurt):

1. **Ruwe prompt komt binnen** (bv. "maak me iets om m'n notities te ordenen of zo").
2. **De slijper schuurt een concept-versie:** einddoel expliciet, locatie ingevuld of als open vraag gemarkeerd, slaag-criterium geformuleerd. Hij mag alleen expliciet maken wat er al in zit, plus standaardwaarden die als zodanig gelabeld zijn — hij vult nooit een doel in dat er niet is, dan stelt hij een vraag.
3. **Eén mens-moment:** de geschuurde versie gaat terug naar de gebruiker ("Dit is wat ik begreep — klopt dit?"), die bevestigt of in één ronde verbetert.
4. **Pas na goedkeuring is er een opdracht**, die door de Scope-poort gaat zoals die al stond.

Loggen: ruwe versie + geschuurde versie + goedkeuring gaan append-only in groei/logboek.json — altijd terug te lezen wat er geïnterpreteerd is.

Grenzen, eerlijk:
- De slijper zelf blijft interpretatie en is dus nooit zo betrouwbaar als machine-bewijs; het mens-moment in stap 3 is daarom **niet onderhandelbaar**.
- Wat de slijper niet uit de invoer kan afleiden, wordt een vraag, geen aanname.
- In fase 4 (harnas) wordt dit hard afgedwongen: de loop voert niets uit dat niet de mensbevestiging heeft gehad.
- Neveneffect (bewust): de slijper werkt als spiegel/trainer — wie ziet hoe zijn prompt in een heldere versie vertaalt, leert vanzelf helderder formuleren.

### 11.2 De groeivliegwiel — het geplante brein voedt de slijper

De slijper raadt niet; hij haalt op. Wie via GrowKit een tweede-brein heeft geplant, heeft een groeiende bron van eigen context (identiteit, voorkeuren, beslissingen, projecten). De slijper gebruikt die als **alleen-lezen grondstof** bij het schuren: hoe voller het brein, hoe scherper de geschuurde versie, hoe kleiner de kans dat de mens moet corrigeren.

Terugkoppeling naar het brein: elke goedgekeurde schuring kan een inzicht opleveren ("blijkbaar wil deze gebruiker altijd X"). Zo'n inzicht gaat als VOORSTEL naar de inbox van het brein; de mens curatieert. Geen verborgen leerproces, geen model-training — groei door curatie, consistent met §7.

Daarmee ontstaat een zelfversterkende cirkel (het "oerwoud in het klein"):

    GrowKit plant het brein → het brein voedt de slijper → de slijper schuurt scherper → betere opdrachten → nieuwe VOORSTELLEN → het brein wordt voller → …

Consequentie voor het eerste profiel: het tweede-brein is niet zomaar de eerste boom — het is de **motor van de vliegwiel**, en daarmee extra rechtvaardiging voor de keuze in §10.

### 11.3 Het vragenformulier — de slijper vraagt met opties, niet met open tekst

De mens-momenten uit §11.1 worden niet als lopende tekst afgehandeld maar als een **klikbaar formulier**: vragen met opties, eventueel meerkeuze, en altijd een "iets anders"-veld. Voorbeeld van het formaat (vast JSON-schema, agent-onafhankelijk):

```json
{
  "vragen": [
    {
      "vraag": "Wat wil je laten groeien?",
      "opties": ["tweede-brein", "autonome-fabriek", "dev-werkplaats", "iets anders (beschrijf)"]
    },
    {
      "vraag": "Waar moet het groeien?",
      "opties": ["deze machine (lokaal)", "een VPS", "iets anders (beschrijf)"]
    }
  ]
}
```

Waarom formulier i.p.v. vrije tekst:

1. **Minimale actie, heldere scope** — aanwijzen in plaats van formuleren; antwoorden vullen de verplichte velden (doel, plek, slaag-criterium) één-op-één in.
2. **Deterministische samenvoeging** — formulier-antwoorden mergeen zonder her-interpretatie in de opdracht; de onbetrouwbare slijp-stap wordt korter.
3. **Opties uit drie bronnen:** (a) de profiel-catalogus met gelabelde standaardwaarden, (b) omgevingsdetectie (lokaal/VPS), (c) **het eigen geplante brein** (projecten, voorkeuren van de gebruiker) — hoe voller het brein, hoe persoonlijker de opties (§11.2 in de praktijk).
4. **Agent-onafhankelijk:** het formulier is een vast JSON-formaat. Fase 11–3: de geleende agent presenteert het met zijn eigen interface (Hermes-vragenlijst, Claude Code-terminal). Fase 4: het harnas tekent het zelf (terminal-UI). Zelfde inhoud, elke omgeving.
5. **Eén ronde, één klik:** formulier → samengevoegde concept-opdracht → "klopt dit? (ja / pas aan)". De slotbevestiging blijft niet-onderhandelbaar (§11.1), maar is zelf ook één klik.

De weigeringsteksten uit §11 worden waar mogelijk vervangen door dit formulier: de poort stuurt niet alleen vragen mee, maar direct de opties waaruit gekozen kan worden.

### 11.4 Mijlpaal-bevestiging — bij grote scope altijd samenvatten en bevestigen vóór definitief

De slijper bewaakt de ingang (11.1-11.3); dit mechanisme bewaakt het verloop. Lange of grote taken drijven af; een vaste tussen-controle vangt dat op voordat iets definitief wordt.

Wanneer actief — een taak geldt als "groot" als die:
- meer stappen omvat dan een configureerbare drempel,
- meerdere sessies kan omvatten,
- of stappen bevat die niet meer terug te draaien zijn (bijv. promoties, publicaties).

Wat de agent bij elke mijlpaal toont, in vast formaat:
1. **Wat ik begrepen heb** — het begrip van de agent op dat moment, niet de wens van de gebruiker.
2. **Wat we afgesproken hebben** — met verwijzing naar groei/logboek.json (controleerbaar, geen "volgens mij was dat zo").
3. **Het bewijs tot nu toe** — welke stappen machine-geverifieerd zijn geslaagd.
4. **Wat hierna komt** — het pad tot de volgende mijlpaal.

Dan één bevestigingsklik (of correctie in één ronde, net als het formulier in 11.3). Pas na bevestiging is de mijlpaal definitief; de bevestiging zelf wordt append-only gelogd.

Gevolgen:
- Achteraf is altijd te reconstrueren welke afspraak op welk moment bevestigd is.
- Bij een sessie-onderbreking of crash is de laatste bevestigde mijlpaal het herstartpunt (samen met 7: het logboek bepaalt waar de agent was).
- "Definitief" is in GrowKit dus altijd een bevestigde toestand, nooit een veronderstelde.

Afdwingbaarheid per fase:

- **Fase 1–3 (geleende agent):** de poort zit in het *formaat* — seed.py weigert invoer zonder verplichte velden; een taak zonder bewijs-check is schema-ongeldig. Dit is hard: zonder geldige invoer draait er niets. De toon-uitvoering (de weigeringstekst) gebeurt wel door de geleende agent en is dus om te praten — al bereikt de gebruiker dan nog steeds niets zonder geldig stappenplan.
- **Fase 4 (eigen harnas):** pas dan is de poort volledig onomzeilbaar, want loop.py bepaalt wat uitgevoerd wordt — dezelfde reden als bij de leesroute (§5).

## 12. Open punten voor het implementatieplan

1. Implementatie van per-fase bestandsontsluiting (§5): directe content-injectie door seed.py (voorkeur) vs. kopiëren naar werkmap.
2. De concrete stappen + bewijs-checks van het generieke tweede-brein-profiel — de échte commando's en checks, geen voorbeelden.
3. ssh-configuratie voor een VPS-doel: vastleggen per profiel (herbruikbaar) vs. opvragen tijdens het planten.
4. Meetbare slaag/faal-criteria voor Test 1 (tweede-brein op schone plek) en Test 2 (vrije beschrijving).
5. Hoe de `reviewer`-rol praktisch wordt geconfigureerd (config-bestand? omgevingsvariabelen?) zonder leveranciers-binding.
6. Exacte verplichte velden en weigeringsteksten van de Scope-poort (§11), en of de vragenlijst per invoertype (kiemkeuze / vrije beschrijving / taak) verschilt.

## 13. Het Oerwoud — meerdere bomen, één brein

Beslissing (3 sept 2026): het oerwoud wordt niet alleen metafoor maar architectuur-doel. Wanneer een gebruiker één instantie (boom) heeft opgezet — bijvoorbeeld het tweede brein — moet die daarna een tweede, derde, vierde kunnen opzetten (autonome fabriek, dev-werkplaats, eigen bomen), waarbij **het geplante tweede-brein het hart is**: alles synct daarheen voor elke nieuwgeboren boom.

Kernidee:

- **Eén brein, vele bomen.** Het tweede-brein is de enige plek waar identiteit, voorkeuren en vastgelegde kennis van de gëruiker leven. Elke nieuwe boom leest daaruit (bijv. voor de Prompt-slijper en de formulier-opties, §11.2) en schrijft er alleen VOORSTELLEN naartoe.
- **Boom-register.** Elke boom krijgt bij het planten een geboortebewijs (boom-id, profiel, machine, locatie, aanmaakdatum). Het brein houdt een register van alle bomen. Zo weet het oerwoud altijd wie er bestaat en waar.
- **Sync = append-only + git**, nooit muterend — de gëruiker blijft overal curator. Eén inbox, één mens, hoeveel bomen er ook staan.

Fase-volgorde (poort blijft staan): het oerwoud is fase 5 en wordt pas gebouwd na het harnas. MAAR: de geboortebewijs-structuur wordt nu al ontworpen en meegeplant in fase 1, zodat geen enkele boom ooit hoeft te worden "nageplaatst" in het register. Voorbereiden ≠ bouwen.

## 14. Buiten scope (voor nu)

- Eigen harnas vóór fase 2-bewijs (fase 4 is de roadmap).
- Sandboxing, prompt-injectie-afweer van tool-output, harnas-resumability — reëel, maar pas relevant zodra het harnas gebouwd wordt.
- Router-domeinen, zware governance, multi-team-permissions.
- Cloud sync, mobiel, web-UI.
