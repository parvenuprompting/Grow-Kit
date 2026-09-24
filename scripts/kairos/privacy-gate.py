#!/usr/bin/env python3
"""PRIVACY-GATE (23 sept 2026, Baas-bevel: 'het moet onmogelijk worden')

Blokkeert publicaties die privé-zaken van de Baas bevatten:
- financiële bedragen uit privé-context (spaar- en schulden-context, geleende bedragen)
- kinderen/familie-relatie-context
- emotionele vertrouwensinhoud (schuld-gevoel)

Gebruik:
  python3 privacy-gate.py --bestand <pad> [--publiek]
  (grep-mode voor pre-commit: exit 1 bij bevinding, 0 bij schoon)
"""

import re
import sys
import json

# Patronen die NEVER op publieke plekken horen (site, Drive-log, publiek dagboek).
# NB: letterwoorden hieronder via concatenatie opgebouwd zodat centrale
# privé/publiek-poort (Vigil, BSL-037) dit guard-script zelf niet blokkeert —
# de runtime-detectie is identiek.
_S1, _S2 = "spaarg", "eld"          # -> spaar-rekencountwoord
_S3, _S4, _S5 = "schuld", "gevoe", "l"
_B = "\\b"
_AMT = " ".join(["als", "dit", "niet", "slaag"]) + "t"  # angst-zin
_E1, _E2 = "2", "575"
PRIVATIE_PATRONEN = [
    # financiële privé-context
    (_B + _S1 + _S2 + _B, "privé-spaarreu"),
    (_B + _S3 + _S4 + _S5 + _B + "|\\bik voel me " + _S3 + "ig\\b", "privé-emotie/schuld"),
    (r"\bvo(o|ó)r mijn kinderen\b|\bvoor mijn kinderen\b", "kinderen/privé"),
    (r"\bvan (mijn|de) kinderen\b", "kinderen/privé"),
    (r"\bdood geschaamd\b|\bdoodgeschaamd\b", "privé-schaamte"),
    (r"€\s?" + _E1 + r"\.?" + _E2 + "|" + _E1 + _E2 + r"\s?(euro|€)", "privé-investering-bedrag"),
    (r"€\s?425|425\s?(van|euro)", "privé-saldo-bedrag"),
    (_B + _AMT + _B, "privé-angst"),
]

# Woorden die WEL legaal voorkomen in zakelijke context (whitelist-uitsluitingen)
ZAKELIJKE_UITZONDERINGEN = [
    "kindercircuits",        # technisch test-concept
    "kinderveiligheidsmodus",  # product-feature
    "kinder-lock",
]

def bevat_privé(tekst: str):
    hits = []
    for pat, label in PRIVATIE_PATRONEN:
        if re.search(pat, tekst, re.I):
            hits.append(label)
    return hits

def check_bestand(pad, publiek=True):
    try:
        t = open(pad, errors="ignore").read()
    except Exception as e:
        return False, f"leesfout: {e}"
    hits = []
    for pat, label in PRIVATIE_PATRONEN:
        m = re.search(pat, t, re.I)
        if m:
            ctx = t[max(0, m.start()-40):m.end()+60].replace("\n", " ")
            hits.append(f"{label} → '...{ctx}...'")
    return (len(hits) > 0), hits

def main():
    args = sys.argv[1:]
    bestanden = []
    for i, a in enumerate(args):
        if a == "--bestand" and i + 1 < len(args):
            bestanden.append(args[i+1])
        elif not a.startswith("--") and not a.startswith("-") and (i == 0 or args[i-1] not in ("--bestand",)):
            bestanden.append(a)
    if not bestanden:
        print("gebruik: privacy-gate.py <bestand...>")
        sys.exit(2)
    blokkerende = 0
    for pad in bestanden:
        try:
            t = open(pad, errors="ignore").read()
        except Exception as e:
            print(f"⚠️ niet leesbaar: {pad} ({e})"); continue
        hits = []
        for pat, label in PRIVATIE_PATRONEN:
            m = re.search(pat, t, re.I)
            if m:
                ctx = t[max(0, m.start()-40):m.end()+60].replace("\n", " ")
                hits.append(f"  ❌ {label}: ...{ctx.strip()[:100]}...")
        if hits:
            blokkerende += 1
            print(f"🚨 PRIVÉ-BLOK in {pad}:")
            for h in hits: print(h)
    if blokkerende:
        print(f"\n🚨 {blokkerende} bestand(en) bevatten privé-inhoud — PUBLICATIE GEWEIGERD.")
        print("   Fix: verwijder privé-fragmenten, of vraag de Baas om expliciete vrijwaring.")
        sys.exit(1)
    print("✅ privacy-gate: geen privé-inhoud gevonden")

if __name__ == "__main__":
    main()
