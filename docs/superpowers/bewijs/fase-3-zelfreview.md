# Fase 3 — zelfreview (taak 8, afsluiting)

Datum: 3 september 2026. Alles hieronder is op de afsluitdatum uitgevoerd;
uitvoer letterlijk, niet samengevat.

## 1. §9 volledig gedekt

**Rol ≠ leverancier.** Scan op `model|provider|leverancier|anthropic|openai|claude|gpt`
over `kern/`, `seed.py` en `reviewconfig.voorbeeld.json`: treffers alleen in de
schema-controle zelf (`_VERBODEN_VELDEN` in growkit_review.py:13) en de
voorbeeld-commentaarregels. Geen enkele echte binding. Het echte
`reviewconfig.json` staat in .gitignore (vóór het eerste echte bestand).

**Onduidelijk → mens.** E2E Test 3 criterium 2: reviewer "onduidelijk" →
`wacht_op_mens`, klassieke mens-instructie. In code: elke exceptie/timeout
in `roep_reviewer` → `"onduidelijk"`, en alleen exact-match op de drie
oordelen telt — alles anders is twijfel, twijfel is de mens.

**Machine-bewijs eerst.** Enige codepad naar de reviewer loopt via
`_behandel_mensstap`, bereikt uitsluitend stappen met `mens_nodig:`
(growkit_motor.py:92-93). Een shell/file/json/http-check-stap kan niet in
de review-laag terechtkomen.

## 2. Open punten afgehandeld

| Punt | Waar | Bewijs |
|---|---|---|
| §11.1 slijper-schuring | taak 5, `d4f9b8c` | 8 tests (`test_slijper.py`): concept exact drie velden + bron.ruwe_invoer; alleen vragen over wat ontbreekt; enige invul = gelabelde standaardwaarde (`standaardwaarde: true` + bron); einddoel nooit ingevuld |
| §11.4 mijlpaal | taak 6, `83f3e21` | 8 tests (`test_mijlpaal.py`): drempel dynamisch uit profiel (mijlpaal_drempel, standaard 10), vast formaat (begrepen/afgesproken+bewijsverwijzing/bewijs/hierna), precies één bevestiging, append-only gelogd; 8-stappenprofiel raakt drempel niet |
| §12.3 ssh per profiel | taak 7, `b321e34` | `_vps-doel.example.json` (placeholders), noot in INDEX.md + SEED.md; sleutels uitsluitend op de doelmachine |
| §12.5 reviewconfig | taak 1-2, `acdeeed`/`9abedc3` | rollen zonder leveranciers; verboden velden = schema-fout |

## 3. Regressie (eindstand, letterlijk uitgevoerd)

- Unit-tests: `Ran 61 tests — OK`
- E2E Test 1 (schone-pleg-plant): 7/7
- E2E Test 2 (poort): 5/5
- E2E Test 3 (review-laag): 5/5
- E2E plant (basisrooktest): alle stappen geslaagd of wacht_op_mens

De review-laag raakt niets aan fase 1-2-gedrag behalve `mens_nodig`-stappen
mét `review`-veld — Test 3 criterium 4 (7× geslaagd ongewijzigd) bewijst dit.

## 4. Externe audit (Claude) — kritisch gewogen

| Punt | Oordeel | Verwerking |
|---|---|---|
| A: uitvoerder-onsduid in SEED.md | terecht; regel 2 was verouderd | SEED.md regel 2 herschreven: motor voert uit, geleende agent bedient (`b321e34`) |
| B: resumability / state-reconstructie | correct, maar bekénd (spec §14); profiel-stappen hebben al `idempotent`-veld | vastgelegd als harde fase-4-vereiste (digest); níet nu gebouwd |
| C: vrije-tekst-omgeving niet herkend | beperking is bewust (poort = veldaanwezigheid, nooit inhoud); gelabelde standaard + mens-moment vangt het op | vastgelegd als fase-4-vereiste (omgevingsdetectie §11.3-3b, gelabelde bron) |
| D: omgevings-drift in het oerwoud | deels al in §11.2/§13; de harde regel ontbrak | één zin toegevoegd aan §13 |
| pytest-aanbeveling | geweigerd | stdlib-unittest is ontwerpkeuze; geen pip-dependencies |

Kanttekening: het audit-snapshot was verouderd (45 tests, taken 1-4, slijper
nog open) — zijn "open vraag" over de slijper was al beantwoord door taak 5.

## 5. Bekende valkuilen gecontroleerd

- E2E-3 gebruikt alleen een cli-testreviewer (echo); geen externe dienst.
- Oordelen zijn exact-match op drie waarden; alles anders = `"onduidelijk"`.
- `.gitignore` bevat `reviewconfig.json` sinds taak 1 — het echte bestand
  kan dus nooit meegecommitteerd raken.
- Mijlpaal-drempel wordt uit het profiel gelezen; geen test faalt op een
  hardcoded 10.
