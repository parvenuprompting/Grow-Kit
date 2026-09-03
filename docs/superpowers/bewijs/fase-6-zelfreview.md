# Fase 6 — zelfreview (taak 9, afsluiting)

Datum: 4 september 2026. Evidence letterlijk uitgevoerd op de afsluitdatum.

## 1. Bedienaar-contract bewezen

- `tests/test_adapter_contract.py` (8 tests): geen `subprocess`/`shell`/
  `os.system`/`os.popen` in `adapter.py`; geen gedupliceerde poort- of
  motor-logica (`def beoordeel_invoer`, `def voer_uit`, `def controleer`,
  checktypes ontbreken in de adapter-bron); de adapter importeert uitsluitend
  `from kern`.
- Vrije tekst is nooit een commando: shell-meta in profielnaam (ook mét
  bevestiging) → nette weigering, geen uitvoering, geen side-effects.
- Confirmatie is expliciet en stateless: `plant` zonder `"bevestig"` retourneert
  het concept en laat de doelmap weg (E2E-6 criterium 2a); twee identieke
  concept-aanroepen geven byte-identieke output (geen sessie-staat).
- `Runner.swift` gebruikt `Process` rechtstreeks — scan: geen
  `NSAppleScript`/`osascript`/shell.

## 2. Poort en motor onaangetast

`git log -- kern/growkit_poort.py` → laatste wijziging fase 3 (`83f3e21`);
`kern/growkit_motor.py` → laatste wijziging fase 3 (`43591d4`). Fase 6 voegde
`status_data` toe aan `kern/growkit_oerwoud.py`, extraheerde ratificatie-logica
naar het nieuwe `kern/growkit_ratificatie.py`, en refactoreerde `loop.py`
(status/ratificeer gebruiken nu de kern-functies — één bron met de adapter).

## 3. Mijlpaal-beslissing (7) bewezen

Een profiel dat de mijlpaal-drempel raakt wordt door de adapter netjes geweigerd
— ook mét bevestiging (`test_adapter_plant.TestFaalEnMijlpaal.test_mijlpaal_
profiel_wordt_net_geweigerd_ook_met_bevestiging`). Geen stilzwijgende
midden-staat; fase 6.1 levert het twee-staps-protocol.

## 4. Provider-agnostisch

Scan op `anthropic|openai|gpt-|claude-|model=` over `adapter.py` en `app/Sources/`:
**leeg**. Reviewconfig-inhoud lekt niet in adapter-uitvoer
(`test_adapter_contract.TestGeenSecrets`, met een geïnjecteerd geheim-token).

## 5. Huisstijl

Fraunces + Inter (SIL OFL, licentiebestanden meegeleverd) ingebed in de bundle
(E2E-6 criterium 1); kleuren uit de mockup-CSS (papier/inkt/zacht/gedempt/lijn);
kiemplant-icoon 1024px gegenereerd via `app/Scripts/genereer-icon.swift`;
drie schermen gerenderd in `docs/superpowers/bewijs/fase-6-schermen/`.

## 6. Regressie (eindstand, letterlijk uitgevoerd)

- Unit-tests: `Ran 206 tests — OK` (fase 1-5: 171 → fase 6: +35)
- E2E 1-5 + rooktest: groen; E2E 6 (app): alle criteria groen
- Poort-/motor-regressie gedekt door de ongewijzigde bestanden + de suite

## 7. Vondsten tijdens de uitvoering (bewaard in de digest)

1. **ImageRenderer + ScrollView:** ImageRenderer rendert ScrollView-inhoud
   leeg — eerste renders waren identiek wit (md5-identiek!). De views kregen
   een `metScroll`-parameter; les: bewijs-beelden checken op pixel-diversiteit,
   nooit alleen op aanwezigheid.
2. **Status als één bron:** `status_data` (kern) voedt nu loop.py én de
   adapter — en ving onderweg een latente crash op een corrupt boom-logboek.
3. **E2E-1-kloon-les herhaald:** protocol-uitbreidingen zijn pas in verse
   klonen zichtbaar na commit — commit-volgorde is onderdeel van het contract.
4. **Realpath-nuance:** mktemp (/var/folders) vs. resolve() (/private/var/
   folders) — E2E-vergelijkingen van locaties gebruiken realpaths.
