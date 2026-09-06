# KairOS OS — Fase 1 bouwplan (uitvoeringsklaar)

Status: startpakket klaar, wacht op Raspberry Pi 5 (8GB, starter kit ca. €264)
Datum: 6 sept 2026 · Opdracht: `Agent-Brain/projecten/kairos-os-fase1-opdracht.md`
Verificatie: de drie vaste eisen uit de opdracht zijn in dit plan per stap
uitgewerkt naar concrete checks (zie checklist onderaan).

---

## 1. Wat vastligt (beslissingen, met onderbouwing)

### 1.1 Fundament: Raspberry Pi OS Lite (64-bit)

Raspberry Pi OS Lite is Debian zonder bureaublad — precies wat een
systeemdienst-machine nodig heeft. Onderbouwing:

- **Officieel en bewezen**: gebouwd met de eigen image-tool van de
  Raspberry Pi Foundation, decennialang gehard, enorme community.
- **Minimaal**: geen desktop, geen ballast → minder aanvalsoppervlak en
  meer RAM vrij voor het model.
- **Headless**: werkt zonder scherm of toetsenbord (SSH), aansluitend op
  de Tailscale-richting uit fase 2.
- **Closest to target**: de officiële Pi-tooling (Imager) ondersteunt
  headless voorinstelling (hostname, SSH, wifi) — de "silent failure"
  risico's uit het bouwplan (slechte sd-kaart, corrupte image) worden
  vermeden door NVMe-boot (zie 1.2).

Alternatieven bewust niet gekozen:
- *Debian minimal handmatig*: meer werk, geen meerwaarde op de Pi.
- *Alpine*: musl/libc-afwijkingen geven wrijving met Python/ML-stack.
- *Buildroot/Yocto*: overkill voor fase 1; dit is voor eigen firmware-builds.

### 1.2 Opslag: NVMe-ssd via USB3, niet sd-kaart

Model-loads vanaf sd-kaart duren minuten; vanaf NVMe seconden. Ook de
python-stack, logs en de netwerkmonitor draaien beter op NVMe. De starter
kit wordt dus uitgebreid met een NVMe-ssd (256GB is ruim voldoende) en een
USB3-behuizing of -kabel (ca. €25–35 totaal).

### 1.3 Systeemlaag: GrowKit Agent als systemd-dienst

De dienstdefinitie staat klaar: `kairos-agent.service` (in deze map).
Kernprincipes van de dienst:

- `Type=notify` met watchdog: als de dienst vastloopt, herstart systemd
  hem (Restart=always, RestartSec=10) — geen mens nodig.
- Draait als eigen systeemgebruiker `kairos` (geen root).
- `After=network-online.target ollama.service` — de agent start pas als
  het netwerk en de model-server klaar zijn.
- Hardened: `NoNewPrivileges`, `ProtectSystem=strict`, `PrivateTmp`,
  `ProtectHome=read-only` (met schrijfruimte alleen in de werkboom).

### 1.4 AI-laag: Ollama + Vangnet-specialist

Modelkeuze (onderbouwd op sept-2026 benchmarks voor de Pi 5 8GB):

| Model | RAM | Snelheid op Pi 5 | Rol |
|---|---|---|---|
| **gemma3:4b** (primair) | ~3.3GB | ~8–11 tok/s | beste kwaliteit binnen het RAM-budget; past naast de agent-dienst |
| **gemma3:1b** (reserve/snel) | ~0.8GB | ~18–22 tok/s | snelle antwoorden als de 4b te traag voelt |

Beide modellen staan **al op de Mac** en zijn daar getest (zie
`vangnet-testset.md`). De AI-laag draait als `ollama.service` naast de
agent-dienst; Ollama luistert alleen op localhost.

### 1.5 Netwerkmonitor: de poortwachter

`netwerkmonitor.py` (getest met unittest) controleert twee dingen:
1. **Statisch**: welke Ollama-modellen staan er, en zijn er `:cloud`-
   modellen of externe hosts geconfigureerd (die bellen wel extern)?
2. **Dynamisch**: netwerkverkeer vanaf de machine, gefilterd op
   bekende externe AI-aanbieders (OpenAI, Anthropic, Google AI, OpenRouter,
   DeepSeek, Groq, Mistral, xAI, HuggingFace-inference).

Uitvoer is JSON met `"ok": true/false` — machine-toetsbaar, passend bij
het GrowKit-principe: de agent claimt nooit zelf succes.

---

## 2. Volgorde van bouwen (op de Pi, zodra hardware er is)

| Stap | Wat | Bewijs (machine-toetsbaar) |
|---|---|---|
| P1 | Raspberry Pi Imager → Raspberry Pi OS Lite 64-bit op NVMe, headless voorinstelling (hostname `kairos`, SSH aan, eigen user) | boot-log; `ssh kairos@kairos.local` werkt |
| P2 | NVMe-boot activeren (bootloader-update op sd-kaart, dan NVMe-only) | `lsblk` toont NVMe als root-device, sd-kaart uit → systeem blijft up |
| P3 | `apt install python3-venv git && git clone` GrowKit-repo + `.venv` | `python -m unittest discover tests` groen |
| P4 | Ollama installeren + modellen ophalen (`gemma3:4b`, `gemma3:1b`) | `ollama list` toont beide; `curl localhost:11434/api/tags` OK |
| P5 | Systeemgebruiker `kairos` + dienst installeren | `systemctl status kairos-agent` = active (running) |
| P6 | Netwerkmonitor als systemd-timer (elke 60s) | log toont `"ok": true` zonder valse alarmen |
| P7 | Eindtest fase 1: alle drie de verificatie-eisen | bewijs-map met logs (zie checklist) |

Stappen P1–P2 doen we samen (hardware-moment), P3–P6 bouwt de agent,
P7 is de officiële fase-1 oplevering met bewijsmap.

## 3. Offline-werking (cruciaal voor het bewijs)

De Pi draait **bewust zonder internet** tijdens de eindtest:

- Alle modellen staan lokaal op de NVMe (via Ollama).
- De GrowKit Agent draait met een **lokaal profiel**: geen SSH naar de
  VPS, geen externe API-calls. De agentchat-wachtrij (VPS-poller) is
  in fase 1 op de Pi bewust **uit** — de Pi is souverein.
- Het netwerkmonitorscript vangt elke poging tot extern AI-verkeer.

Hiermee is verificatie-eis 2 ("geen externe afhankelijkheid") niet een
belofte maar een gemeten feit.

## 4. Bewijs-checklist fase 1 (vaste eisen → concrete checks)

| Eis | Check | Bewijsstuk |
|---|---|---|
| 1. Systeemdienst | `systemctl is-active kairos-agent` = active; `systemctl show -p MainPID kairos-agent` geeft PID van het python-proces | screenshot/log |
| 2. Geen extern AI-verkeer | `netwerkmonitor.py --once` → `"ok": true` na 10 min normaal gebruik; tegelijk een **positieve test**: handmatig 1x naar een externe API bellen → `"ok": false` + alarm | JSON-log |
| 3. Lokale modelrespons | `ollama run gemma3:4b` met de testvragen uit `vangnet-testset.md`, internetkabel eruit | terminal-log met antwoorden |

Positieve test (eis 2) is bewust: een monitor die nooit vals alarm mag
geven, bewijst niets. We tonen dat hij wél alarm slaat als het fout gaat.

## 5. Relatie tot bestaande plannen

- **GrowKit** (`skills-telegram-lokaalmodel-bouwplan.md`): Functie C
  (KairOS-mini op de Mac) blijft apart — dat is de Mac-route. Deze map is
  de Pi-route (KairOS OS). Ze delen Ollama, modellen en het
  SOUL-snapshot-formaat, maar zijn verschillende machines.
- **Agent-Brain**: bij elke mijlpaal wordt `projecten/kairos-os.md`
  bijgewerkt met register-entry.
- **Tailscale** (fase 2): niet in dit plan; alleen de headless-richting
  is hier al vastgelegd (SSH-only, sleutel-authenticatie).
