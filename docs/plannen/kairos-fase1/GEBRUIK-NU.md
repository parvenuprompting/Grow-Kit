# Gebruik nu: fase-1 voorbereiding vandaag

## Wat je vandaag in handen krijgt

Deze map bevat de **voorbereiding van KairOS OS fase 1** die zonder
Raspberry Pi gebouwd kon worden. Er is bewust niets geïnstalleerd of
gepusht: dit zijn beslissingen, definities en een geteste poortwachter.

| Bestand | Wat het is |
|---|---|
| `bouwplan-fase1.md` | Het plan: beslissingen + bouwstappen + bewijs-checklist |
| `kairos-agent.service` | De dienstdefinitie voor de Pi (systeemdienst, niet losse app) |
| `netwerkmonitor.py` | Poortwachter die externe AI-verkeer vangt (getest, unittest) — staat in `scripts/kairos/` |
| `test_netwerkmonitor.py` | De unittest van de poortwachter |
| `vangnet-testset.md` | Testvragen + modelkeuze voor de Vangnet-specialist |
| `bewijs/` | De bewijsstukken van vandaag (runs op de Mac) |

## Wat er vandaag al bewezen is (op de Mac, zelfde gereedschap als de Pi)

1. **Poortwachter**: unittest groen (10/10); live-run ving op de Mac vier
   `:cloud`-modellen in Ollama als externe afhankelijkheid — inclusief de
   positieve test (de monitor slaat wél alarm als het fout gaat).
   Bewijs: `bewijs/netwerkmonitor-mac-2026-09-06.json`.
2. **Lokaal model**: gemma3:1b en gemma3:4b staan al op deze Mac en
   antwoorden via de Ollama-API (127.0.0.1) op de testset — volledig
   lokaal. Bewijs: `bewijs/ollama-demo-2026-09-06.log`.
   Eerlijke kanttekening: het 1b-model antwoordt soms warrig (schreef in
   de demo "Tiébedo" i.p.v. Tiëndo). Dat is precies waarom gemma3:4b de
   primaire keuze is; de 1b is alleen het snelle reservemodel.

## Wat de Pi-strategie is (kort)

- Raspberry Pi OS Lite (64-bit) als fundament; boot vanaf NVMe-ssd.
- GrowKit Agent als systemd-dienst (`kairos-agent.service`).
- Vangnet-specialist: gemma3:4b (primair) / gemma3:1b (snel antwoord).
- Bewijs per stap volgens de drie verificatie-eisen uit de fase-1 opdracht.

Volledige uitleg en volgorde: zie `bouwplan-fase1.md`.
