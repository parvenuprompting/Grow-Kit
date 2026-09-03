# Bewijs — Fase 2, Test 1: Schone-pleg-plant

Datum: 3 september 2026
Protocol: `docs/superpowers/testprotocol-fase-2.md`
Script: `tests/e2e_test1_schoon.sh`
Uitvoerend: Mac Hermes (automatisch, geen mens tussen de stappen)

## Resultaat: 7/7 criteria geslaagd

```
OK 1.1: verse kloon plant zonder fout
OK 1.7: draait op python3.14, geen pip-install
OK 1.5: geen schrijfactie buiten de doelmap (kloon nog schoon)
OK 1.2: 8 stappen — 7 geslaagd, 1 wacht_op_mens
OK 1.3: vijf kernmappen + INDEX.md + geboortebewijs bestaan
OK 1.4: alle gekopieerde bestanden byte-voor-byte gelijk aan sjablonen
OK 1.6a: niet-idempotente stap dynamisch gevonden: stap-005 (geen hardcode)
OK 1.6b: herstart faalt niet onnodig; logboek (16 entries) bevat nul 'gefaald'

TEST 1 OK: schone-pleg-plant — 7/7 criteria geslaagd
```

## Plantverloop in de kloon (machine-bewijs per stap)

```
[OK] stap-001 — shell_check: zocht 'MAPPEN-OK', kreeg: 'MAPPEN-OK'
[OK] stap-002 — file_equals: INDEX.md = sjabloon
[OK] stap-003 — file_equals: identiteit/AGENT-ROL.md = sjabloon
[OK] stap-004 — file_equals: inbox/REGELS.md = sjabloon
[OK] stap-005 — json_valid: logboek/logboek.json OK
[OK] stap-006 — shell_check: zocht 'GITKEEP-OK', kreeg: 'GITKEEP-OK'
[OK] stap-007 — file_equals: geboortebewijs.json = sjabloon
[mens-moment] stap-008: Lees de drie getoonde bestanden … (wacht_op_mens — correct)
```

## Methodenotities

- De kloon was vers (`git clone` naar tmp) en bleef ná de run onveranderd
  (`git status --porcelain` leeg vóór én na) — de plant schreef uitsluitend
  in de doelmap.
- De herstart-run (1.6) voerde hetzelfde plan opnieuw uit op dezelfde doelmap:
  het logboek groeide append-only naar 16 entries zonder één "gefaald" — de
  niet-idempotente stap-005 herstelde zijn eigen voorwaarde (lege array) en
  slaagde daarmee opnieuw.
- Python: gevonden door het script zelf (python3.14), geen pip-installatie
  nodig — alleen stdlib.
