# Grow Kit — zes verbeteringen

Branch: `codex/grow-kit-six-improvements`. Elke slice krijgt een eigen commit.
Na een onderbreking: lees dit bestand, `git status`, `git log -8 --oneline`.

## Volgorde en acceptatie
- [ ] Slice 1 (advies 2): mens-wachtstatus blokkeert vervolgstappen; panic vóór elke stap/poging; onleesbare panic blokkeert; shell-bewijs vereist exitcode. Regressietests.
- [ ] Slice 2 (advies 4): transactionele gebeurtenissen/opslag, behoud en import bestaande logs, crash/concurrentietests.
- [ ] Slice 3 (advies 3): expliciete acceptatiecriteria en afzonderlijk technisch bewijs, inhoudelijk oordeel, menselijke goedkeuring.
- [ ] Slice 4 (advies 1): één opdrachtpagina en compacte navigatie; bestaande hulpmiddelen blijven bereikbaar.
- [ ] Slice 5 (advies 5): drie lokale voorbeeldopdrachten met plan, bevestiging, uitvoering en bewijs zonder VPS.
- [ ] Slice 6 (advies 6): gegevensroute en verzonden inhoud zichtbaar; cloudtoestemming afdwingen; documentatie corrigeren.

## Validatie
Voer gerichte regressietests per slice uit, daarna de volledige Python-suite en macOS-build indien beschikbaar. Geen externe agents/servers aanroepen tijdens tests. Leg fouten en beperkingen hier vast.

## Stand
Repository opgehaald vanaf GitHub; werkboom schoon bij start. Graph-index aangemaakt (Verify): Users-tiendo-Projects-astra-vangrail-Grow-Kit. Eén bekende parse-gap: app/Sources/Koppelingen.swift:90; docs/scripts uitgesloten. Bronfallback waar nodig.
