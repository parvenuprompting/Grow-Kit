# De groeilaag — leven na de installatie

De boom is geplant. Vanaf nu blijft deze map de levensonderhoudslaag van je
boom: alles wat er daarna gebeurt, wordt hier gelogd, voorgesteld en bijgehouden.

## Onderdelen

- `logboek/logboek.json` (in de plant) — append-only log van elke stap en
  gebeurtenis, inclusief het machine-geverifieerde bewijs. Bij een crash of
  nieuwe sessie leest de agent dit om te bepalen waar hij was.
- `takenlijst.md` (in de plant) — taken die de agent zelf oppakt en afdwingt
  mét bewijs, volgens hetzelfde stappen-schema als het profiel.
- `inbox/` (in de plant) — voorstellen van de agent (status VOORSTEL); jij
  curateert. Nooit overschrijven, alleen toevoegen; promotie doe jij.

## Regels voor de agent (ook ná de installatie)

1. Bij elke taak: check eerst het logboek (waar waren we?) en de inbox
   (welke voorstellen liggen er?).
2. Nieuwe inzichten worden VOORSTELLEN in inbox/, nooit directe wijzigingen.
3. Bewijs blijft verplicht: een taak is pas klaar als de check dat zegt.
4. Grote of langdurige taken: vat op (begrepen/afgesproken/bewezen/volgende)
   en vraag bevestiging vóór iets definitief wordt (spec §11.4).

## Voor de mens

- Je curateert de inbox op je eigen tempo; niets verandert zonder jou.
- Het geboortebewijs (geboortebewijs.json in de plant) registreert deze boom
  in het toekomstige oerwoud (spec §13): meerdere bomen, één brein.
