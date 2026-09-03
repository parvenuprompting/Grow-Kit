# Kiemkeuze — welke boom wil je laten groeien?

Elke boom hieronder is een stappenplan: een vast pad van commando's met
machine-bewijs per stap. Jij kiest en bevestigt; de agent plant en bewijst.

| Boom | Wat het is | Status |
|---|---|---|
| **tweede-brein** | Een gecontroleerd geheugen naast je AI-agent: de agent leest en stelt voor, jij keurt goed. Vijf kernmappen, append-only logboek, inbox met VOORSTEL-status. | bewezen-vorm |
| **autonome-fabriek** | Een VPS-dienst die 's nachts zelfstandig bouwt en rapporteert. | in-ontwikkeling |
| **dev-werkplaats** | Een codeeromgeving met je tools, regels en configuraties. | in-ontwikkeling |

## Vrij beschrijven

Wil je een andere boom? Beschrijf dan in eigen woorden: (1) wat het einddoel is,
(2) waar het moet groeien (deze machine of een VPS), en (3) wanneer het geslaagd
is. De Prompt-slijper schuurt je beschrijving tot een concept-profiel — maar
let op: een vrij beschreven boom is nog niet bewezen; de agent stelt onderweg
vragen.

## VPS-doel per profiel (§12.3)

Een boom die op een VPS groeit, legt zijn ssh-doel vast in het profiel
(`profielen/<boom>/vps-doel.json`, herbruikbaar) — nooit opgevraagd tijdens
het planten: planten blijft één klik. Zie `profielen/_vps-doel.example.json`
voor de vorm (`host`, `gebruiker`, `poort`). Vuistregel: ssh-sleutels leven
uitsluitend op de doelmachine in `~/.ssh/config`; er staan geen sleutels of
secrets in GrowKit-bestanden of de chat.
