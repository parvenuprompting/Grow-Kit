# Bouwplan: Automatiek in GrowKit

**Doel:** de gebruiker typt in gewone taal wat hij geautomatiseerd wil hebben
("elke ochtend een samenvatting van nieuwe Drive-bestanden in Telegram") en
KairOS zet dat via chat om in een compleet automation-plan. Daarna kan het
plan worden uitgevoerd, met dezelfde zero-trust-bewaking als alles in GrowKit.

**Bronnen:** `parvenuprompting/Automatiek` (zes-blokken-model, validatie,
markdown-export), de Google Workspace-skill (Drive/Docs-toegang die KairOS
al heeft via de gws-venv), en het Agent Chat-wachtrij-patroon.

---

## Fase 1 — Plannen-kern (TDD, lokaal)

**Module:** `kern/growkit_automatiek.py`

- Plandatamodel letterlijk uit `types.ts` overgenomen:
  doel+trigger (schema/webhook/handmatig/event), bronnen & data,
  stappen (nummer, omschrijving, invoer, uitvoer, foutscenario),
  kwaliteit, uitvoering, randvoorwaarden.
- Status `concept` → `klaar` alleen na valide zes blokken (zelfde
  validatieregels als `plan.ts`).
- Secrets-scanner ook op plannen (net als chat): een plan met een API-key
  erin is ongeldig — authenticatie hoort op de doelmachine.
- Opslag: `~/.growkit/automatiek/plannen.json` (append-only log eromheen).

**Tests:** ~20 (model, validatie, status-overgang, secrets-weigering, export).

## Fase 2 — Adapter + KairOS-chatkoppeling

**Adapter-commando's:**

| Commando | Wat |
|---|---|
| `automatiekplan` | nieuw plan uit één zin (via KairOS) of handmatig |
| `automatieklijst` | overzicht plannen (concept/klaar) |
| `automatieklees` | één plan volledig |
| `automatiekstatus` | concept → klaar na validatie |
| `automatiekexport` | markdown of JSON (zelfde formaat als de web-app) |
| `automatiekuitvoer` | plan → taak in de wachtrij van KairOS (bron=automatiek) |

**De KairOS-route (het nieuwe):** `automatiekplan` met alleen een zin:
1. Adapter haalt de zin + de Google Workspace-skill-context (beschikbare
   acties: Drive zoeken, Docs lezen/maken, Sheets lezen/schrijven, Gmail
   zoeken/sturen, Calendar lezen) op;
2. stuurt die als chatbericht (bron=automatiek, `van`=gebruiker) naar de
   KairOS-wachtrij;
3. de poller op de VPS voedt het aan KairOS met een speciaal prompt-venster:
   "Zet deze wens om in een Automatiek-plan volgens het zes-blokken-model.
   Antwoord alléén met geldige JSON.";
4. KairOS zijn antwoord (gepuurd) wordt gevalideerd tegen het model;
   ongeldig → nette fout + nieuw voorstel; geldig → plan opgeslagen als
   `concept`.

Zo is de planner dezelfde KairOS die de gebruiker al kent — met zijn
KairOS-stem en zijn kennis van de familie-infrastructuur.

## Fase 3 — Scherm (item 16 onder WERK)

`app/Sources/AutomatiekView.swift`:

- Kop: "Automatiek" — "Zet één zin om in een automation-plan. KairOS doet het voorstel; jij keurt."
- Eén groot invoerveld ("Wat wil je automatiseren?") + knop "Vraag KairOS".
- Terwijl KairOS denkt: dezelfde typing-stippen als Agent Chat.
- Concept-lijst eronder: plannen met status-badge (CONCEPT/KLAAR).
- Plan-detail: zes blokken, elk ingeklappt, met "Naar KLAAR"-knop (alleen
  actief bij geldige blokken) en "Exporteer markdown".
- KLAAR-plannen: knop "Geef aan KairOS" → wachtrij → KairOS voert uit met
  gouverneur-bewaking (max 2 taken, faalcontract).

## Fase 4 — CI/CD (GitHub Actions)

`.github/workflows/ci.yml`:

1. **Test-job** (elke push + PR): Ubuntu-runner, Python 3.12,
   `.venv` aanmaken, `cryptography` installeren, `python -m unittest discover tests`.
   Groen = merge toegestaan; rood = blokkeert.
2. **Build-job** (na tests, alleen op main): macOS-runner,
   `cd app && bash build.sh` — bewijst dat de app compileert.
3. **Secrets-scan** (elke push): eigen scanner die test op de patronen uit
   `growkit_contract._PATRONEN` over de diff — een echte key blokkeert de push.
4. Later uit te breiden: Release-runner (tag → .app-artifact + ZIP).

Reden: de repo is publiek; elke bijdrage (ook van andere agenten) moet
machinaal bewijzen dat de tests groen zijn vóór push. Dat past bij het
zero-trust-harnas: de CI is de machine-controle voorbij de mens.

---

## Volgorde & bewijs

| Stap | Bewijs |
|---|---|
| 1. Kern + tests (rood → groen) | unittest-suite |
| 2. Adapter-commando's + mock-SSH-tests | unittest + E2E via adapter |
| 3. VPS-poller: automatiek-prompt + JSON-validatie | E2E: zin → plan (concept) |
| 4. Scherm + build + installatie | visuele verificatie |
| 5. CI/CD-workflow | eerste groene run op GitHub |
| 6. Commit + push | alleen na akkoord van Tiëndo |

Elke fase apart commitbaar; niks half in de repo.
