"""Slice B — agentstatus: leeft de familie? (alleen-lezen)

De status komt van de VPS (systemd user services van de gateways).
Deze module voert het SSH-commando uit via een injectabele uitvoerder
zodat tests offline draaien; de adapter bedient alleen.

Leesbelofte: dit leest alleen toestand (`systemctl is-active` +
laatste journal-regel). Er wordt niets herstart, geschreven of
geconfigureerd — status is geen macht.
"""
import json
import subprocess

# Vaste, alleen-lezen diagnostiek. Geen variabelen van buitenaf in
# het commando — alleen de profielnamen uit het familie-register.
HOST = "root@168.119.248.208"
PROFIELEN = ("kairos", "riri", "vigil", "libra", "memoria", "codex", "genius")

_SERVICE = {
    # KairOS = hoofdprofiel, draait als systeem-service; kinderen als user-service.
    "kairos": "hermes-gateway",
    "riri": "hermes-gateway-researchos",
    "vigil": "hermes-gateway-vigil",
    "libra": "hermes-gateway-libra",
    "memoria": "hermes-gateway-memoria",
    "codex": "hermes-gateway-codex",
    "genius": "hermes-gateway-genius",
}
# kairos-label in de uitvoer (service heet hermes-gateway, agent heet kairos)
_LABEL = {"kairos": "hermes-gateway-kairos"}


def _standaard_uitvoerder(commando: list[str], timeout: int) -> tuple[int, str]:
    try:
        p = subprocess.run(commando, capture_output=True, text=True,
                           timeout=timeout)
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired:
        return 124, ""


def verzamel_status(uitvoerder=_standaard_uitvoerder, timeout: int = 20) -> dict:
    """Vraag alle gateway-statussen in één SSH-roundtrip op."""
    delen: list[str] = []
    for p in PROFIELEN:
        dienst = _SERVICE[p]
        label = _LABEL.get(p, dienst)
        query = ("systemctl is-active" if p == "kairos"
                 else "systemctl --user is-active")
        delen.append(f'printf \'{label} \'; {query} "{dienst}" 2>/dev/null '
                     f'|| echo onbekend')
    script = "; ".join(delen)
    code, uit = uitvoerder(["ssh", "-o", "BatchMode=yes",
                            "-o", f"ConnectTimeout={max(timeout - 5, 5)}",
                            HOST, script], timeout)
    if code != 0:
        return {"ok": False, "fout": "VPS onbereikbaar — status onbekend.",
                "agents": []}

    agents: list[dict] = []
    regels = [r for r in uit.strip().splitlines() if r.strip()]
    for profiel in PROFIELEN:
        dienst = _SERVICE[profiel]
        label = _LABEL.get(profiel, dienst)
        regel = next((r for r in regels if r.startswith(label + " ")), "")
        delen = regel.split()
        toestand = delen[-1] if len(delen) >= 2 else "onbekend"
        agents.append({"agent": profiel, "status": toestand})

    return {"ok": True,
            "fout": None if any(a["status"] == "active" for a in agents)
                    else "Geen enkele gateway meldt zich actief.",
            "agents": agents}
