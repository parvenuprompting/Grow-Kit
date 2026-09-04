# Roadmap — Verticale slices naar de complete Boom-omgeving

> Vastgelegd 4 september 2026 door VPS-Hermes (KairOS), opdracht Tiëndo.
> Volgorde is bewust: elke slice bouwt op het bewijs van de vorige.
> Slices 1–4 zijn puur Mac-lokaal (geen netwerk). Elke slice: commit op main + groene tests als afsluiting.

## Uitgangspunt (bewezen stand, 4 sept 2026)

- Fase 1–6 bewezen: stappenplan, kieming, review-laag, harnas (`loop.py`, vijf modi), oerwoud, macOS-app (taken 1–9, 206 unit-tests + 7 E2E's).
- Laatste commits: homescherm + uitleg-schermen, instellingen (AI- en brein-providers), adapter 6.1 (hervat/taak/mijlpaal).

## Slice 1 — Boom-kiezer in de app

**Doel:** van "huidige boom" naar meerdere bomen beheerbaar in de app.
- Boom-registratielijst (boom-id, profiel, pad, laatste status) volgens het fase-5-oerwoud-formaat.
- Boom wisselen vanuit het homescherm; nieuwe boom planten start de bestaande kiemstroom.

**Bewijs:** app toont ≥ 2 bomen, wisselen werkt, unit- en E2E-tests groen.

## Slice 2 — Live status per boom

**Doel:** de waarheid zichtbaar, nooit zelf-rapportage.
- Per boom: lopende/hervatte taak, laatste bewijs-tijdstip, faalcontract-status (groen / rood / gestopt) — rechtstreeks uit `groei/logboek.json`.

**Bewijs:** crash-herstartscenario (Test 4-methode) nagebouwd in de UI: na `kill -9` toont de app de hervat-status uit het logboek.

## Slice 3 — Acties met poortjes

**Doel:** de vijf modi bedienbaar vanuit de app, zonder het poort-model te omzeilen.
- Knoppen voor planten, hervatten, taak, ratificatie, status.
- Gevaarlijke acties vragen bevestiging; `mens_nodig`-stappen openen de auth-actie op de doelmachine (nooit secrets in de app).

**Bewijs:** per knop een E2E die faalt zonder poort-goedkeuring en slaagt mét.

## Slice 4 — Inbox-curatiescherm

**Doel:** het curatiebeleid in de app (chat-goedkeuring IS curatie).
- VOORSTEL-items uit de groei-inbox tonen; goedkeuren = direct definitief boeken; afwijzen = markeren. Append-only, nooit overschrijven.

**Bewijs:** round-trip VOORSTEL → goedgekeurd → append-only logboekregel, geverifieerd met de bestaande validator-logica.

## Slice 5 — Breinkoppeling (oerwoud, fase 5)

**Doel:** meerdere bomen onder één gedeeld brein, vanuit de app.
- Registratie via geboortebewijs (boom-id, profiel, machine, locatie).
- Harde drift-guard blijft gehandhaafd: alleen universele context sync't; omgevings-specifieke staat (paden, poorten, ssh-doeleinden, sleutels) blijft lokaal per boom.

**Bewijs:** sync-test tussen twee bomen + brein-validator volledig groen.

## Slice 6 — Nachtfabriek-modus

**Doel:** de app als avond-controller van de autonome nachtronde.
- Boom + taken in de wachtrij zetten; 's nachts autonoom draaien via het harnas; ochtendrapport (bewezen / stilgevallen) in de huisstijl van Tiëndo.

**Bewijs:** één echte nachtronde op de Mac met een ochtendrapport als logboek-waardig resultaat.

## Verwijzingen

- Ontwerpbron: `docs/superpowers/specs/2026-09-03-growkit-design.md`
- Uitleg: `docs/HOE-HET-WERKT.md`
- Technische uitwerking v0.3: Drive — "Growkit — Technische uitwerking (v0.3)"
