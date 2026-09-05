# Zen van Reticulum — lessen voor GrowKit

> Bron: "Zen of Reticulum" door Mark Qvist (begin 2026), in de Reticulum-repo.
> Gelezen op 5 september 2026. Dit is geen samenvatting om te citeren, maar een
> vertaling naar wat het betekent voor GrowKit.

## Wat Reticulum is (context)

Reticulum is een bouwpakket voor eigen communicatienetwerken: versleuteld,
zonder centrale server, werkend over alles — van LoRa-radio tot wifi. De maker
schreef er een filosofiedocument bij: korte hoofdstukken over hoe je over
netwerken móét denken als je ermee bouwt. Dat document is eigenlijk het
leerrijkste deel van het hele project.

## De vijf lessen die voor GrowKit tellen

### 1. De code ís de specificatie
Reticulum zegt expliciet: er komt nooit een apart officieel document dat het
protocol beschrijft. De werkende, geteste, draaiende code is dé definitie.
Waar het bij GrowKit over gaat: een claim bestaat pas als hij toetsbaar is.
Dat is precies waarom seed.py bestaat — de agent claimt nooit zelf succes;
het script toetst. Reticulum bewijst dat dit op grote schaal werkt.

### 2. Ontwerp voor de slechtste omstandigheid
Reticulum begint niet bij snelle verbindingen; het werkt óók op 5 bits per
seconde. "Als je systeem een vijandige omgeving niet overleeft, overleeft het
niets." Voor het harnas (fase 4): ga ervan uit dat de agent soms halve
antwoorden geeft, context kwijtraakt of vastloopt — en maak elke stap zo klein
en goedkoop dat de sessie dat overleeft.

### 3. Elke stap een prijs
Een versleutelde verbinding opzetten kost 3 pakketjes van samen 297 bytes.
Ze meten de kosten van hun eigen protocol. Les: meet wat een groei-sessie
kost (stappen, tokens, tijd) en houd de eenheid klein.

### 4. Vertrouwen is wiskunde, niet een belofte
Geen vertrouwen op basis van "iemand zegt dat het klopt", maar op basis van
bewijs dat je zelf kunt controleren. GrowKit doet dit al met
machine-toetsbaar bewijs; dit bevestigt de richting.

### 5. Een korte Zen-tekst geeft een product zijn karakter
Het document noemt de grenzen in plaats van ze te impliceren ("niet één
netwerk", "geen kill-switch"). Wie het leest weet meteen wat het níet is.
Les voor SEED.md: schrijf de grenzen van GrowKit expliciet op, kort en
treffend, niet alleen de features.

## Conclusie

Voor GrowKit is het *ontwerp* van Reticulum waardevol, niet de code. De
patronen (kleine stappen, toetsbaar bewijs, harnas dat slechte omstandigheden
overleeft) sluiten aan op de hermes-harnas-analyse: patronen lenen, geen
god-files overnemen.
