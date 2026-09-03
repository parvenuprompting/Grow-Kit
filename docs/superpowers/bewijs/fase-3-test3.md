# Bewijs — Fase 3, Test 3: Review-laag in de praktijk

Datum: 3 september 2026
Plan: `docs/superpowers/plans/2026-09-03-growkit-fase-3.md` (task 4)
Script: `tests/e2e_test3_review.sh`
Uitvoerend: Mac Hermes (automatisch, geen mens tussen de stappen)

## Resultaat: 5/5 criteria geslaagd

```
OK 1: reviewer-geslaagd → review_ok_wacht_ratificatie, exit 0, motor door
OK 2: reviewer-onduidelijk → wacht_op_mens (klassiek mens-moment)
OK 3: geen reviewconfig → identiek fase-2-gedrag; géén review-velden in log
OK 4+5: machine-stappen onaangetast; log vermeldt rol + oordeel

TEST 3 OK: review-laag in de praktijk — 5/5 criteria geslaagd
```

## Wat er is gemeten

1. **Reviewer "geslaagd"** (cli-testreviewer): mens-stap-008 kreeg status
   `review_ok_wacht_ratificatie` mét `review_rol` en `review_oordeel` in het
   logboek; de motor ging door (7 machine-stappen allemaal geslaagd);
   exit-code 0.
2. **Reviewer "onduidelijk"** (antwoordde "misschien" — geen geldig oordeel):
   status `wacht_op_mens`, rol + oordeel wél gelogd — klassiek mens-moment.
3. **Zonder reviewconfig:** identiek aan fase-2; het log bevat géén
   review-velden (regressie-bewijs).
4. In alle drie de runs: de 7 machine-bewijs-stappen geslaagd en onaangetast —
   de reviewer krijgt uitsluitend mens_verificatie-stappen.
5. Log-vermelding van rol + oordeel hard gecheckt in run 1 en 2; afwezigheid
   daarvan hard gecheckt in run 3.

## Onderweg gevonden en opgelost (eerlijk gelogd)

- De E2E draaide de motor buiten seed.py om en struikelde over de
  `{GROWKIT}`-plaatshouders — de padsubstitutie bleek alleen in seed.py te
  leven. Oplossing: substitutie gecentraliseerd in
  `kern.growkit_motor.vervang_growkit_pad()`; seed.py en de E2E gebruiken
  dezelfde functie (één bron van waarheid). Alle fase 1-2 tests en E2E's
  daarna opnieuw groen (45 unit-tests + 3 E2E-scripts).
