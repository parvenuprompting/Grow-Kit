# Ontwerp — GrowKit

Datum: 3 september 2026
Status: goedgekeurd in brainstorm (Tiëndo + Mac Hermes); v2 na externe review (Claude) — model-switch, harnas-beslissing, groeifases-roadmap, keuze eerste profiel

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

- `shell_check` — commando draait, output moet aan een voorwaarde voldoen (bevat / matcht)
- `http_check` — URL reageert met verwachte status
- `file_exists` — pad bestaat
- `json_valid` — bestand is valide JSON (optioneel: tegen een schema)

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
    "slaagt_als": "bevat 'Up'"
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

De echte stappen van dit profiel worden in het implementatieplan uitgewerkt (open punt 2 uit §11).

## 11. Open punten voor het implementatieplan

1. Implementatie van per-fase bestandsontsluiting (§5): directe content-injectie door seed.py (voorkeur) vs. kopiëren naar werkmap.
2. De concrete stappen + bewijs-checks van het generieke tweede-brein-profiel — de échte commando's en checks, geen voorbeelden.
3. ssh-configuratie voor een VPS-doel: vastleggen per profiel (herbruikbaar) vs. opvragen tijdens het planten.
4. Meetbare slaag/faal-criteria voor Test 1 (tweede-brein op schone plek) en Test 2 (vrije beschrijving).
5. Hoe de `reviewer`-rol praktisch wordt geconfigureerd (config-bestand? omgevingsvariabelen?) zonder leveranciers-binding.

## 12. Buiten scope (voor nu)

- Eigen harnas vóór fase 2-bewijs (fase 4 is de roadmap).
- Sandboxing, prompt-injectie-afweer van tool-output, harnas-resumability — reëel, maar pas relevant zodra het harnas gebouwd wordt.
- Router-domeinen, zware governance, multi-team-permissions.
- Cloud sync, mobiel, web-UI.
- "Oerwoud"-modus (meerdere bomen samenwerkend).
