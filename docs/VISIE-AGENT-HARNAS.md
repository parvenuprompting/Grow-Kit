# GrowKit Agent Harnas — De Eindvisie

> Vastgelegd 4 september 2026 door VPS-Hermes (KairOS), opdracht Tiëndo.
> Dit document is de leidende visie voor de samenvoeging van Tiëndo's projecten
> tot één agent-harnas. Wijzigingen alleen via dit document, append-only in de
> wijzigingsgeschiedenis.

## De visie in één zin

**GrowKit wordt het harnas: één macOS-app waarin Tiëndo's beste losse projecten
samenkomen en met elkaar praten via één backend — zonder dat er iets aan hun
bewezen kern wordt veranderd.**

## Architectuur: organen in een lichaam

```
┌──────────────────────────────────────────────────────────┐
│           GROWKIT AGENT HARNAS (macOS, SwiftUI)          │
│      één commandocentrum · één huisstijl · één brein     │
├─────────────┬─────────────┬─────────────┬────────────────┤
│  P.A.C.     │  Saldo      │  Brein      │  (volgt later) │
│  nacht-     │  OpenRouter │  Agent-     │  proof-coverage│
│  fabriek,   │  saldo +    │  Family-    │  Crumb,        │
│  bouw-      │  per-model  │  Brain:     │  Dossierklaar, │
│  rondes,    │  token-     │  kennis,    │  …             │
│  register   │  verbruik   │  curatie    │                │
├─────────────┴─────────────┴─────────────┴────────────────┤
│        BACKEND: GrowKit JSON-adapter-protocol            │
│   JSON in → JSON uit · poortjes · faalcontract · bewijs  │
└──────────────────────────────────────────────────────────┘
```

## De wetten (overgenomen en blijvend)

1. **Niets draait zonder bevestigde scope** — de poort weigert vage invoer.
2. **Succes is bewijs, nooit een claim** — deterministische controles, geen
   zelf-rapportage.
3. **De geschiedenis is append-only** — niets wordt overschreven of verwijderd.
4. **Secrets verlaten de doelmachine nooit** — API-keys staan lokaal
   (`~/.growkit`), nooit in de repo, chat of het brein.
5. **Losse apps blijven bestaan totdat hun paneel bewezen beter is** —
   integratie is aansluiten, niet slopen.

## De drie lagen

| Laag | Wat | Status |
|---|---|---|
| **Backend** | GrowKit JSON-adapter (17 commando's, bewezen in slices 1–6) | ✅ compleet |
| **Orgaan-bridges** | Per project een adapter-brug die zijn kern-data beschikbaar stelt | 🔨 te bouwen |
| **macOS-shell** | Eén SwiftUI-app in de huisstijl, panelen per orgaan | 🔨 te bouwen (Mac) |

## Fase A — Orgaan-bridges (backend, kan op de VPS)

Elke bridge volgt hetzelfde patroon als de bestaande adapter-commando's:
JSON in → JSON uit, poort eerst, bewijs in het logboek, append-only.

### A1 — Saldo-bridge (eerste, simpelste API, directe waarde)
- **Bron:** OpenRouter API (saldo + generatie-statistieken per model).
- **Commando's:** `saldo` (actueel saldo), `verbruik` (per-model/per-dag).
- **Key:** `OPENROUTER_API_KEY` uit `~/.growkit/` — nooit in de repo.
- **Bewijs:** tegen de live API getest; waarde-afwijkingen als nette fout.

### A2 — P.A.C.-bridge
- **Bron:** `fabriek/register/` (ideas.json, built.json), tijdlijn, ronde-verslagen.
- **Commando's:** `pac_register` (register-overzicht), `pac_rondes`
  (ronde-geschiedenis), `pac_status` (laatste nachtronde).
- **Regel:** register lezen mag, **schrijven alleen via het bestaande
  `portfolio.py`** — de P.A.C.-regels (nooit handmatig bewerken) blijven staan.

### A3 — Brein-bridge
- **Bron:** Agent-Family-Brain repo (kennis, curatie, wijzigingsregister).
- **Commando's:** deels al aanwezig (`inbox`, `curate`); nieuw: `brein_index`
  (document-overzicht), `brein_zoek` (FTS over het brein).
- **Regel:** lezen vrij; schrijven via curatie-laag (append-only, zoals bewezen).

## Fase B — macOS-shell (SwiftUI, bouwt op de Mac)

- Eén app in de huisstijl (Editorial Monochrome: papier, inkt, Fraunces/Inter).
- Panelen per orgaan: Home (overzicht van alles), Nachtfabriek (P.A.C.),
  Saldo, Brein, Boom-tuinen (GrowKit-kern).
- De bestaande GrowKit-app-code (fase 6, homescherm, instellingen) is het
  startpunt — panelen worden uitgebreid, niet herbouwd.
- Elke berryk met eigen bewijs, zoals de slices: commit op main + groene tests.

## Fase C — Overige kandidaten (later, pas als A+B bewezen zijn)

Kandidaten uit de repo-lijst die aansluiten, ieder via dezelfde bridge-route:
- `proof-coverage-ext` — bewijsdekking per taak (sluit direct aan op het
  bewijs-concept van het harnas).
- `Crumb` — cookie-beheer (eigen paneel, eigen poort).
- `Dossierklaar`, `Ideeen-archief` — kennis-panelen op het brein.
- Opname per project is een expliciete beslissing van Tiëndo, geen automatisch
  proces.

## Wat bewust NIET gebeurt

- Geen fusie van repositories — alle projecten blijven eigen repos met eigen
  historie en hun eigen regels.
- Geen monoliete backend — elke bridge is een los adapter-segment; valt er één
  weg, dan draait de rest door.
- Geen automatische overname — elk nieuw orgaan gaat via bewijs + beslissing.
- Geen secrets of persoonlijke gegevens tussen organen — de drift-guard geldt
  ook hier (§13-patroon: alleen gemarkeerde inhoud reist).

## Volgorde van aanpak

1. **Nu:** A1 Saldo-bridge (bewijs + commit op main).
2. **Daarna:** A2 P.A.C.-bridge.
3. **Dan:** A3 Brein-bridge (brein_index + brein_zoek).
4. **Parallel op de Mac:** B — SwiftUI-shell met Home-paneel dat de eerste
   bridges leest.
5. **Daarna:** Fase C per project, op beslissing.
