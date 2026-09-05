"""Centrale verbinding-constanten voor de agent-bridges (audit 5 sept 2026).

Het SSH-doel van de agent-familie staat hier op precies één plek.
Omleidbaar via de omgeving, zelfde patroon als de GROWKIT_*-overrides:

    GROWKIT_HOST=gebruiker@voorbeeld.test python3 adapter.py status

De drift-guard-regel (§13: ssh-doeleinden blijven lokaal per boom) geldt
onverminderd; deze constante is alleen de standaardwaarde voor de
agent-bridges (agenttaak, agentcontrole, agentstatus, graaf, observaties).
"""
import os

HOST = os.environ.get("GROWKIT_HOST", "root@168.119.248.208")
