#!/usr/bin/env python3
"""CyberSeed SOUL-verfrissing (LaunchAgent, standaard elke 48u).

Draait user-scoped (geen sudo). Logt één regel naar cron.log.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/tiendo/Documents/Code 7/growkit")
from kern import growkit_cyberseed as cs  # noqa: E402

leeftijd = cs.verfris_soul()
log = cs._basis_pad() / "cron.log"
with log.open("a") as f:
    f.write(f"{cs._nu().isoformat(timespec='seconds')} SOUL ververst "
            f"(leeftijd nu {leeftijd:.0f}h)\n")
print("SOUL ververst")
