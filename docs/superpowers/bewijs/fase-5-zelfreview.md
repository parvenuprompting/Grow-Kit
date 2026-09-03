# Fase 5 — zelfreview (taak 8, afsluiting)

Datum: 3 september 2026. Evidence letterlijk uitgevoerd op de afsluitdatum.

## 1. Drift-guard hard bewezen (§13)

Omgevings-specifieke staat reist nooit mee:

- `test_oerwoud_voorstellen.TestDriftGuard.test_zonder_prefix_reist_er_niets`:
  REGELS.md, root-bestanden en niet-gemarkeerde bestanden blijven thuis — de
  brein-inbox bevat na de run precies wat er vóór de run stond.
- `...test_logboeken_en_paden_reisen_nooit`: het boom-logboek en het
  geboortebewijs reizen nooit; uitsluitend de gemarkeerde VOORSTEL-kopie
  belandt in de brein-inbox.
- E2E-5 criterium 3 bewijst het end-to-end: REGELS.md in het brein blijft op
  de template-tekst, geen lekkage van VOORSTEL-inhoud.

## 2. Het brein is alleen-lezen behalve register/inbox-toevoegingen

- `test_oerwoud_opties.test_lezen_is_alleen_lezen`: brein-inhoud onaangetast
  na formuliergebruik.
- `test_oerwoud_voorstellen.TestVeiligheid.test_collisie_wordt_geweigerd_niet_
  overschreven`: naam-collisie → weigering, het bestaande brein-bestand blijft
  byte-voor-byte gelijk.
- `test_oerwoud_register`: het register kent alleen append (`_schrijf_entry`);
  deregistratie is een vervolg-entry, niets wordt verwijderd.

## 3. Append-only overal

Logboeken, register en inbox verlenen uitsluitend nieuwe entries. Geen enkele
functie in `kern/growkit_oerwoud.py` herschrijft een gevuld bestand — de
append-helpers lezen, voegen toe en schrijven de volledige lijst terug met de
bestaande entries als prefix (bewezen door de append-only-asserties in
`test_oerwoud_geboorte`, `test_oerwoud_register` en `test_oerwoud_voorstellen`).

## 4. Provider-agnostisch

Scan op `anthropic|openai|gpt-|claude-|model=` over `kern/growkit_oerwoud.py`
en `loop.py`: **leeg**. Het oerwoud kent boom-ids, paden en rollen — geen
leveranciers.

## 5. Regressie (eindstand, letterlijk uitgevoerd)

- Unit-tests: `Ran 171 tests — OK` (fase 1-4: 110 → fase 5: +61)
- E2E 1 (schone-pleg-plant, met protocol-uitbreiding 1.4b): groen
- E2E 2 (poort): groen · E2E 3 (review-laag): groen
- E2E 4 (harnas zonder agent + crash-herstart): groen
- E2E 5 (oerwoud): 6/6, twee keer gedraaid · E2E plant (rooktest): groen

## 6. Beslissingen uit het plan-review (Claude, 3 sept) — alle vijf verwerkt

| Beslissing | Waar bewezen |
|---|---|
| 1. oerwoud-staat in `~/.growkit` (env-override voor tests) | `test_oerwoud_plant.TestStaat`; E2E-5 draait in een geïsoleerde home |
| 2. registratie = machine-feit, direct gelogd | `meld_geboorte` vereist een gecontroleerd geboortebewijs; geen VOORSTEL |
| 3. `VOORSTEL-`-naamconventie | drift-guard-tests; ontvangen bestanden machinetoetsbaar via uuid-prefix |
| 4. doorstroom automatisch na plant + aanbod in status | `plant_profiel` (na registratie) + `toon_status` (één bevestiging, bijgewerkte teller) |
| 5. cross-machine sync uitgesteld | geen git-operaties in de kern; lokaal-only bewezen in E2E-5 |

**Gat 1 (oude bomen):** `is_voor_fase5` + migratie met `geplant_op` terugge-
rekend uit de eerste logboek-entry — `test_oerwoud_plant.TestMigratieOudeBomen`
en bereikbaar via de status-modus (`test_loop_status.TestStatus.test_niet_
geregistreerde_oude_boom_krijgt_migratie_aanbod`).

**Gat 2 (onbereikbaar brein):** `brein_onbereikbaar` — geen crash, géén
fallback naar nieuw brein, pad-correctie of afbreken alleen via de mens
(`test_oerwoud_plant.TestRegistreerNieuweBoom`).

**Valkuil (e):** E2E-1 protocol-uitbreiding (9 entries + criterium 1.4b)
vóór de run vastgelegd en uitgevoerd; E2E-3 onaangetast.

## 7. Vondsten tijdens de uitvoering (bewaard in de digest)

1. **Ontvangen ≠ eigen voorstellen:** het brein telt binnenkomende
   `VOORSTEL-<ander-boom-id>-...`-bestanden niet als eigen wachtende
   voorstellen — machinetoetsbaar via het uuid-prefix.
2. **Teller na doorstroom:** de status toont na verzending de bijgewerkte
   stand in plaats van de stand vóór het aanbod.
3. **Latente crash gedicht:** een vrij getypte kiemkeuze-naam die geen profiel
   is, gaf een FileNotFoundError — nu een nette weigering (taak 6).
4. **E2E-4 in een verse kloon:** de protocol-uitbreidingen van E2E-1 waren pas
   na commit zichtbaar in de kloon — commit-volgorde is onderdeel van het
   E2E-contract.
