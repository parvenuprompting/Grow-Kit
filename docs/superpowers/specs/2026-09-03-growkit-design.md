# Ontwerp — Growkit

Datum: 3 september 2026
Status: goedgekeurd in brainstorm (Tiëndo + Mac Hermes); technische doorwerking v1 (naam + machine-bewijs + leesroute-afdwinging)

## 1. Wat het is

Growkit is een **zelfstandig product**: een repo die na installatie vanzelf "ontkiemt". Een AI-agent (zoals Hermes) leest een korte geboortebrief, laat de gebruiker een groeiprofiel kiezen, voert een stappenplan uit mét machine-geverifieerd bewijs, en zet daarna een levenslange groeilaag op. De gebruiker plant met één actie; de agent doet de rest en vraagt de mens alleen bij echte mens-momenten.

**Belangrijke grens:** Growkit staat volledig los van Tiëndo's eigen omgeving (Agent-Brain, VPS-configuratie). Het is géén kopie of kloon van zijn setup — zijn tweede-brein-werkwijze inspireert hooguit het eerste profiel. Growkit schrijft nooit terug naar bestaande systemen van de gebruiker.

Metafoor: zaadje → kiemkeuze → plant → boom. Later mogelijk meerdere bomen (oerwoud).

Kernprincipes:

- De mens is de baas; de agent executeert.
- **Machine-toetsbaar bewijs** — seed.py verifieert het resultaat zelf; de agent claimt nooit zelf succes (zie §3).
- Append-only loggen; de agent stelt voor, de mens keurt goed.
- Leesroute wordt **afgedwongen door het script**, niet alleen afgeraden in de brief (zie §5).

## 2. Naam en positionering

- Productnaam: **Growkit** (Engels, herbruikbaar buiten het Nederlandstalige ecosysteem).
- De inhoud — profielen, geboortebrief, logboek — blijft Nederlandstalig, consistent met de werkwijze van de eerste gebruiker.
- Naamcheck 3 sept 2026: vrij op PyPI/npm (let op: het bestaande `grokit`-pakket is een ander product); GitHub kent geen vergelijkbaar product. Er bestaat een growkit.com (paddenstoelen) en Pimoroni "Grow Kit" (hardware) — andere markt; notitie voor eventueel later merkenonderzoek.

## 3. Bewijs: machine-toetsbaar, niet zelf-gerapporteerd

Risico bij zelf-gerapporteerd bewijs: de agent die uitvoert is dezelfde die het bewijs interpreteert, en kan een foutmelding als succes lezen omdat het plan dat verwacht.

Oplossing: bewijs is waar mogelijk een expliciete check die **seed.py zelf uitvoert**, met een vaste set types en eigen verificatiefuncties:

- `shell_check` — commando draait, output moet aan een voorwaarde voldoen (bevat / matcht)
- `http_check` — URL reageert met verwachte status
- `file_exists` — pad bestaat
- `json_valid` — bestand is valide JSON (optioneel: valideert tegen een schema)

Kan een stap niet machine-toetsbaar (bijv. "de pagina ziet er correct uit"), dan is de stap expliciet gemarkeerd **mens-verificatie** en telt niet als automatisch bewijs.

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
  "idempotent": true
}
```

- `bewijs.type` — een van de vaste set uit §3; de agent claimt niet zelf succes.
- `mens_nodig` — `null` tenzij de stap browser-auth of API-sleutel-invoer vereist. Altijd op de doelmachine zelf, nooit secrets in de chat.
- `bij_falen` — precies één alternatief; lukt dat ook niet → mens. Geen verdere retries zonder mens.
- `idempotent` — of seed.py de stap bij hervatting veilig opnieuw mag draaien of eerst moet controleren of hij al (deels) is uitgevoerd. Elke stap die bestanden aanmaakt, mappen initialiseert of externe diensten aanroept zet dit veld expliciet — geen impliciete aanname.

## 5. Leesroute-afdwinging

De leesroute is geen gedragsadvies maar een **grens die het script afdwingt**: seed.py ontsluit profielbestanden pas per fase, in plaats van de hele repo vanaf het begin beschikbaar te stellen. Concreet voorstel: `profielen/` pas naar de werkmap kopiëren nadat de kiemkeuze is gedaan, óf seed.py injecteert de inhoud rechtstreeks aan de agent in plaats van te verwijzen naar een pad. Implementatiekeuze staat in §8.

## 6. Repo-structuur

```
growkit/
├── SEED.md            ← geboortebrief: eerste wat de agent leest
├── seed.py            ← opstartscript (python seed.py)
├── profielen/
│   ├── INDEX.md           ← kiemkeuze: welke boom? (standaard + vrij beschrijven)
│   ├── tweede-brein/      ← eerste profiel (geïnapporteerd, niet gekoppeld aan Tiëndo's echte brein)
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

- `logboek.json` — append-only log van elke stap, inclusief het **machine-geverifieerde** bewijs. Bij crash of nieuwe sessie leest de agent dit om te bepalen waar hij was en welke stappen (op basis van `idempotent`) veilig herhaald kunnen worden.
- `takenlijst.md/json` — taken die de agent zelf oppakt en afdwingt mét bewijs, volgens hetzelfde schema als §4.
- `inzichten-inbox/` — voorstellen van de agent (status VOORSTEL); de mens curatieert. Nooit overschrijven, alleen toevoegen; promotie doet de mens.

Zo is de boom zelfvoorzienend (logt), zelflerend (inbox + curatie) en zelfcorrigerend (taakcontrole + machine-bewijs).

## 8. Open punten voor het implementatieplan

1. Implementatie van per-fase bestandsontsluiting (§5): kopiëren naar werkmap vs. directe content-injectie door seed.py.
2. De concrete `bewijs.type`-checks voor het eerste profiel (tweede-brein), afgeleid van generieke installatiestappen — niet van Tiëndo's specifieke machine.
3. ssh-configuratie voor een VPS-doel: vastleggen per profiel (herbruikbaar) vs. opvragen tijdens het planten.
4. Meetbare slaag/faal-criteria voor Test 1 (tweede-brein op schone plek) en Test 2 (vrije beschrijving).

## 9. Buiten scope (voor nu)

- Router-domeinen, zware governance, multi-team-permissions.
- Cloud sync, mobiel, web-UI.
- "Oerwoud"-modus (meerdere bomen samenwerkend).
