# Grow Kit — zes verbeteringen

Branch: `codex/grow-kit-six-improvements`. Elke slice krijgt een eigen commit.
Na een onderbreking: lees dit bestand, `git status`, `git log -8 --oneline`.

## Volgorde en acceptatie
- [x] Slice 1 (advies 2): mens-wachtstatus blokkeert vervolgstappen; panic vóór elke stap/poging; onleesbare panic blokkeert; shell-bewijs vereist exitcode. Regressietests.
- [x] Slice 2 (advies 4): transactionele gebeurtenissen/opslag, behoud en import bestaande logs, crash/concurrentietests.
- [x] Slice 3 (advies 3): expliciete acceptatiecriteria en afzonderlijk technisch bewijs, inhoudelijk oordeel, menselijke goedkeuring.
- [x] Slice 4 (advies 1): één opdrachtpagina en compacte navigatie; bestaande hulpmiddelen blijven bereikbaar.
- [x] Slice 5 (advies 5): drie lokale voorbeeldopdrachten met plan, bevestiging, uitvoering en bewijs zonder VPS.
- [ ] Slice 6 (advies 6): gegevensroute en verzonden inhoud zichtbaar; cloudtoestemming afdwingen; documentatie corrigeren.

## Validatie
Voer gerichte regressietests per slice uit, daarna de volledige Python-suite en macOS-build indien beschikbaar. Geen externe agents/servers aanroepen tijdens tests. Leg fouten en beperkingen hier vast.

## Stand
Repository opgehaald vanaf GitHub; werkboom schoon bij start. Graph-index aangemaakt (Verify): Users-tiendo-Projects-astra-vangrail-Grow-Kit. Eén bekende parse-gap: app/Sources/Koppelingen.swift:90; docs/scripts uitgesloten. Bronfallback waar nodig.

### Slice 1
39 gerichte tests groen; zes nieuwe regressietests eerst rood. Mens-wachtstappen zijn nu ratificeerbaar en stoppen de motor. PANIC blokkeert nieuwe commando’s en bewijscommando’s; lopende processen worden niet afgebroken (de UI moet dit expliciet tonen). Bestaande review-ok/bulk-ratificatie blijft behouden. Volledige suite gestart, resultaat volgt.

### Slice 2
69 gerichte tests groen. JSON-compatibiliteit behouden via flock + tempbestand/fsync/atomic replace/map-fsync; append-only mutaties weigeren historische wijzigingen. Motor, panic, ratificatie, mijlpalen, taak- en boomgebeurtenissen gebruiken gedeelde opslag. Automatiek bewaart plannen + gebeurtenissen in één transactionele store met legacy-import en JSON-exports; revisies voorkomen stale updates. Concurrentietest met vier processen bewaart alle 60 gebeurtenissen. Volledige suite signaleerde oude tests die een mens-pauze nog als succes verwachten, plus ontbrekende cryptography en sandbox/gebruikersmap-afhankelijkheden; integratie-aanpassingen volgen.

### Slice 3
12 tests groen. Bewijsrapport projecteert acceptatiecriteria en drie afzonderlijke oordelen per stap; technische checks geven geen inhoudelijke of menselijke goedkeuring. JSON-bewijs kan exacte veldwaarden/type controleren. Adaptercommando bewijsrapport beschikbaar; taakpagina in slice 4 gebruikt dezelfde projectie.

### Slice 4
4 gerichte tests groen (dossier van concept tot goedkeuring, wachten en hervatten, gelijktijdige uitvoering geweigerd, geen pad-ontsnapping via het id). Zijbalk: 00 Vandaag, 01 Opdrachten, 02 Bibliotheek, de rest onder Gereedschappen — nummering strikt oplopend, geen dubbele nummers meer. HomeView is opgegaan in het Vandaag-scherm (begroeting met ZT-3-variant, vier cijfers, knowledge graph) en daarna verwijderd: dat bestand was de enige echte buildbreker (`await MainActor.run` met een await erin). macOS-build groen met HomeView verwijderd. Let op: `opdrachten nieuw` werkt vandaag alleen met profiel tweede-brein; autonome-fabriek en dev-werkplaats hebben nog een leeg stappenplan (slice 5).

### Pauze is geen fout (rechtzetting van slice 1)
Slice 1 liet een mens-moment de motor stoppen — goed — maar de adapter las die stop als motor-faal (exit 2). Een pauze werd zo als fout gemeld en zes bestaande tests werden rood. Nu benoemt `uitkomst()` de uitkomst (geslaagd | wacht_op_mens | gepauzeerd | gefaald) en `machine_deel_voltooid()` of alleen nog een mens-stap open is. Adapter, loop.py en seed.py: pauze → exit 0 met status wacht_op_mens en, als de machine-kant af is, wordt de boom volmaakt en geregistreerd; PANIC → eigen melding; een echt gefaalde stap houdt exit 2. 4 nieuwe guardtests; volledige suite 794 groen (was 790 met 6 rood).

### Slice 5
Drie voorbeeldopdrachten, elk volledig lokaal (geen VPS, geen netwerk, geen sleutel): `projectcontrole`, `documentenoverzicht`, `terugkerend-rapport`. Elk profiel draagt zijn eigen `voorbeeld`-blok (titel, uitleg, criteria) — één bron, dus de lijst in de app kan niet losraken van het plan dat draait. De voorbeelden staan op status `voorbeeld`, niet `bewezen-vorm`, zodat de profielenlijst eerlijk blijft. Adapteractie `opdrachten actie=voorbeelden`; het scherm toont de drie onder OPDRACHTEN (links). Eén bevestiging volstaat nu als eindresultaat: keur je de laatste mens-stap goed en is er daarna niets meer te draaien, dan is de opdracht `goedgekeurd` (met een acceptatie-entry in het logboek) in plaats van een tweede herstart-ronde. 8 nieuwe tests: contract (drie voorbeelden, plan, mens-stap, bekend bewijstype, geen externe aanroepen), echte uitvoering van alle drie met de beloofde bestanden, afwijzen → herziening_nodig, en de adapteractie. Volledige suite 802 groen; macOS-build groen.
