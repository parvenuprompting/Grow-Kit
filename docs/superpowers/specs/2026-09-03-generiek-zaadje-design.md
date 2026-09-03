# Ontwerp — Het Generieke Zaadje

Datum: 3 september 2026
Status: goedgekeurd in brainstorm (Tiëndo + Mac Hermes)

## 1. Wat het is

Een repo die na installatie vanzelf "ontkiemt": een AI-agent (zoals Hermes) leest een korte geboortebrief, kiest met de gebruiker een groeiprofiel, voert een stappenplan uit mét bewijs, en zet daarna een levenslange groeilaag op. De gebruiker plant met één actie; de agent doet de rest en vraagt de mens alleen als het echt niet anders kan.

Metafoor: zaadje → kiemkeuze → plant → boom. Later mogelijk meerdere bomen (oerwoud).

Kernprincipes (afkomstig uit PECL / Agent-Brain-werkwijze):

- De mens is de baas; de agent executeert.
- Bewijs bij elke afgevinkte taak — nooit "het zal wel gelukt zijn".
- Append-only loggen; de agent stelt voor, de mens keurt goed.
- Context zuinig: per groeifase alleen de benodigde instructies lezen.

## 2. Doelgroep & eerste bewijs

- Eerste gebruiker: Tiëndo zelf. Zijn tweede-brein-setup is het eerste, bewezen groeiprofiel.
- Vrij-beschrijven-profielen zijn expliciet gelabeld "onbewezen"; de agent stelt onderweg vragen.

## 3. Structuur van de repo

```
zaadje/
├── SEED.md            ← geboortebrief: eerste wat de agent leest
├── seed.py            ← opstartscript (python seed.py)
├── profielen/         ← standaard-bomen (JSON-stappenplannen)
│   ├── tweede-brein/      (eerste bewezen profiel — kopie van Tiëndo's werkwijze)
│   ├── autonome-fabriek/  (VPS-dienst, geïnspireerd op nightly-builder)
│   └── dev-werkplaats/    (codeeromgeving)
└── groei/             ← levenslange laag ná installatie
```

## 4. SEED.md — de geboortebrief

Kort en streng, in agent-taal. Bevat:

- Wie de agent is vanaf dit moment (rol: tuinier) en wat het einddoel is.
- De harde regels: bewijs vereist, alleen lezen wat genoemd wordt, mens vragen alleen bij mens-momenten, nooit zonder bewijs claimen dat iets gelukt is.
- Een leesroute: per fase precies welk bestand de agent dan pas leest — zodat het contextvenster nooit volloopt.

## 5. seed.py — het planten

1. Eén vraag aan de gebruiker: "Wat wil je ooit laten groeien?"
   - Kies een standaardprofiel uit `profielen/`, óf
   - Beschrijf vrij (optie C): script maakt een nieuw profiel aan met status `onbewezen` en waarschuwt eerlijk.
2. Bepaal omgeving: lokaal of VPS (met eigen configuratie & uitgebreide uitleg).
3. Maak de mappen aan, start de leesroute en geef het stappenplan aan de agent.
4. Initialiseer `groei/` (logboek, takenlijst, inzichten-inbox).

## 6. Stappenplannen (profielen)

JSON per profiel. Elke stap heeft:

- `commando` — wat er draait
- `verwacht` — wat het resultaat moet zijn
- `bewijs` — hoe geverifieerd wordt (bijv. "poort 8787 reageert", "bestand bestaat en is valide JSON")
- `mens_nodig` (optioneel) — browser-auth-popup of API-sleutel-invoer, altijd op de doelmachine zelf, nooit secrets in de chat

Agent-gedrag bij stappen: uitvoeren → echte output vastleggen → afvinken mét bewijs. Bij falen: één alternatief proberen, anders de mens roepen. Voortgang in `groei/logboek.json` zodat een crash of nieuwe sessie kan hervatten waar hij was.

## 7. groei/ — de groeilaag (zaadje → boom)

Bestaat na installatie permanent en blijft de levensonderhoudslaag:

- `logboek.json` — append-only log van alles wat de boom doet.
- `takenlijst.md/json` — taken die de agent zelf oppakt en afdwingt mét bewijs.
- `inzichten-inbox/` — voorstellen van de agent (status VOORSTEL), de mens curatieert. Zelflerend zonder ongecontroleerde mutatie: nooit overschrijven, alleen toevoegen; promotie doet de mens.

Zo is de boom zelfvoorzienend (logt), zelflerend (inbox + curatie) en zelfcorrigerend (taakcontrole + bewijs).

## 8. Testen / bewijsvoering

- Test 1: het zaadje plant het tweede-brein-profiel op een schone plek (verse map of VPS); het resultaat moet matchen met de referentie-setup.
- Test 2: het vrij-beschrijven-pad met een simpele opdracht levert een werkend (klein) profiel op.
- Pas als beide bewezen zijn, is het een zaadje en geen presentatie.

## 9. Buiten scope (voor nu)

- Router-domeinen, zware governance, multi-team-permissions (de oude PECL-v3-ambities).
- Cloud sync, mobiel, web-UI.
- "Oerwoud"-modus (meerdere bomen samenwerkend).

## 10. Open punten voor het implementatieplan

- Exacte naam van het product (AI Scratchpad? Zaadje? iets anders).
- Hoe een VPS-doel benaderd wordt (ssh-config in het profiel vs. tijdens het planten).
- Taal van de profielen en logboek (Nederlands eerst, zoals Agent-Brain).
