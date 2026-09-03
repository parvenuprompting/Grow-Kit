# Fase 5 — Test 5: het oerwoud op een schone plek (bewijs)

Datum: 3 september 2026. Script: `tests/e2e_test5_oerwoud.sh`. Protocol stond
vóór de run vast in het fase-5-plan (fase-2-les). Uitvoering: twee
opeenvolgende runs, beide 6/6.

## Wat het bewijst

Meerdere bomen onder één gedeeld brein (§13): een boom wordt bij het planten
het brein of meldt zich daar aan, stuurt VOORSTELLEN append-only door, en het
brein voedt de formulieren alleen-lezen. Geen enkele agent is betrokken —
uitsluitend bash + python3 met gepijpte antwoorden (criterium 6).

## Criteria, per protocol

| # | Criterium | Bewijs uit de run |
|---|---|---|
| 1 | Boom A wordt het brein | geboortebewijs volwaardig (uuid-formaat, géén placeholders); register-entry met `is_brein: true` waarvan het boom-id exact het geboortebewijs volgt; geboorte-systeem-entry in het boom-logboek |
| 2 | Boom B registreert zonder vraag | brein bekend op deze machine → geen extra vraag (beslissing 4); register bevat 2 entries met unieke boom-ids, `is_brein` precies één keer, en alle locaties bestaan |
| 3 | Doorstroom met drift-guard | `VOORSTEL-test-inzicht.md` van boom B arriveert als `VOORSTEL-<boom-id-b>-test-inzicht.md` in de brein-inbox; inhoud intact; REGELS.md onaangetast (template-kop + geen lekkage); precies één doorstroom-entry in het boom-logboek |
| 4 | Status voor beide bomen | identiteit (boom-id/profiel/geplant-op), register-status (`geboorte`) en tellers (`0 wachtend, 1 verzonden` na doorstroom) kloppen |
| 5 | Corrupt register | brein-register bewust corrupt gemaakt → exit 1, corrupt-melding, géén traceback — de mens wordt geroepen, nooit auto-reparatie |
| 6 | Geen agent | uitsluitend `printf ... \| python3 loop.py` met gepijpte antwoorden |

## Wat de E2E onderweg aantoonde (en het ontwerp verbeterde)

1. **Ontvangen VOORSTELLEN zijn geen eigen voorstellen:** het brein telt de
   binnenkomende `VOORSTEL-<ander-boom-id>-...`-bestanden niet als eigen
   wachtende voorstellen — machinetoetsbaar via het uuid-prefix (fase-5-taak 7).
2. **Teller na doorstroom:** de status toont na verzending de bijgewerkte
   stand (`0 wachtend, 1 verzonden`) in plaats van de stand vóór het aanbod.

## Aansluiting op het plan (v2, gat-review verwerkt)

- **Gat 1 (oude bomen):** migratie-path met terugrekening van `geplant_op`
  uit de eerste logboek-entry — getest in `tests/test_oerwoud_plant.py` en
  bereikbaar via de status-modus (taak 5).
- **Gat 2 (onbereikbaar brein):** foutstatus `brein_onbereikbaar` met
  pad-correctie of afbreken door de mens — getest in
  `test_oerwoud_plant.TestRegistreerNieuweBoom`.
- **Valkuil (e), geverifieerd:** E2E-1 kreeg zijn protocol-uitbreiding
  (9 entries + criterium 1.4b) vóór de fase-5-run; E2E-3 bleef onaangeroerd.
