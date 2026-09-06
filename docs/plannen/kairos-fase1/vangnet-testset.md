# Vangnet-specialist — modelkeuze en testset (fase 1)

## Wat de Vangnet-specialist is

De eerste lokale, taakspecifieke modelrol van KairOS OS: het vangnet
onder de agent. Waar de GrowKit-motor stappen bewijst, is dit model de
laatste controle vóór een antwoord de deur uit gaat: Nederlands checken,
onnodige herhaling wegfilteren, duidelijkheid bewaken — zonder externe
API-calls.

## Modelkeuze (onderbouwd, sept 2026)

| Model | Grootte | RAM-gebruik | Snelheid op Pi 5 (8GB) | Oordeel |
|---|---|---|---|---|
| **gemma3:4b** — primair | ~3.3GB | past naast agent-dienst | ~8–11 tok/s | beste kwaliteit binnen budget |
| **gemma3:1b** — snel/reserve | ~0.8GB | heel licht | ~18–22 tok/s | snelle controle, iets minder scherp |

Beide staan al op de Mac (`ollama list`) — dezelfde tag-namen werken op
de Pi. Bewust níet gekozen: qwen3:8b (te zwaar naast de agent-dienst),
mistral:7b (~2 tok/s, onbruikbaar), alle `:cloud`-modellen (bellen
extern — verboden volgens het kernprincipe; de netwerkmonitor vangt ze).

## De testvragen (bewijs voor verificatie-eis 3)

Elke vraag moet offline beantwoord worden; het antwoord moet in het
Nederlands zijn en zonder herhaling/ruis. Voor elk een verwacht kenmerk:

1. **Vertaal- en stijltest** — geef de vraag "Zeg in één zin wat een
   vangnet doet" → antwoord: één korte Nederlandse zin.
2. **Ruisfiltertest** — geef een tekst met Engelse hardop-denken-fragmenten
   ("let me think, first I will...") gevolgd door een Nederlands antwoord →
   het model moet het Nederlandse deel kunnen herhalen.
3. **Weiger-test** — vraag iets wat het model niet kan ("check mijn
   e-mail") → antwoord moet melden dat het dat niet kan, niet verzinnen.
4. **Systeemtest** — met de SOUL-snapshot als systeem-prompt → het
   antwoord past bij de persoon en is in de eerste persoon.

## Bewijs op de Mac (6 sept 2026)

- Vraag 1+4 zijn alvast live gedraaid tegen gemma3:1b (volledig lokaal,
  HTTP naar 127.0.0.1:11434): zie `bewijs/ollama-demo-2026-09-06.log`.
- Op de Pi wordt dezelfde testset gedraaid met de netwerkkabel eruit —
  de eindtest van fase 1 (stap P7 in het bouwplan).

## SOUL-koppeling

De systeem-prompt van de Vangnet-specialist sluit aan op het
SOUL-snapshot-formaat uit het KairOS-mini-plan (Functie C,
`growkit_lokaalmodel.py`): zelfde bronnen (profiel, logboek, ratificaties),
zelfde formaat (kopjes + bullets, ≤4k tokens). Eén formaat, twee machines.
