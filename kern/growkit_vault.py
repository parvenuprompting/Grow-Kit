"""Secure Vault-kern voor GrowKit — inbouw van SecureVault v2.

Inbouw van parvenuprompting/secure-vault-v2 (MIT, Tiëndo Welles) als
GrowKit-kernmodule. De encryptie doet macOS zelf: hdiutil met AES-256 op
APFS. GrowKit is de hand, niet het slot. Geen externe libraries —
stdlib-only, zoals de rest van de kern.

Huisregels die hier gelden (zelfde zero-trust als de rest van het huis):
- Het wachtwoord reist nooit in het commando, alleen via stdin (-stdinpass).
- Bestaande kluizen worden nooit stilletjes overschreven.
- Elke kluis-actie (maken, openen, sluiten) krijgt een append-only
  audit-entry.
- Wachtwoorden mogen in de macOS Sleutelhangar (security CLI).

Publieke functies:
    KLUIS_VORMEN                    — de drie vormen (UDZO, UDRW, UDSB)
    extentie_voor(vorm)             — .dmg of .sparsebundle
    valideer_bron(pad) / valideer_doel(pad)
    controleer_overschrijven(pad, toestaan)
    wachtwoord_sterkte(pw) / genereer_wachtwoord(lengte)
    keychain_sla_op / keychain_lees / keychain_verwijder
    maak_kluis(bron, doelmap, naam, wachtwoord, vorm, overschrijven)
    open_kluis(pad, wachtwoord) / sluit_kluis(mountpunt) / open_kluizen()
    zoek_kluizen()                  — Spotlight (mdfind) kluiszoeker
"""
from __future__ import annotations

import json
import os
import secrets
import string
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Fouttype
# ---------------------------------------------------------------------------


class KluisFout(Exception):
    """Gewijigerde kluis-actie: duidelijke Nederlandse reden."""


# ---------------------------------------------------------------------------
# De drie kluisvormen (uit SecureVault v2)
# ---------------------------------------------------------------------------

KLUIS_VORMEN: dict[str, dict[str, str]] = {
    "UDZO": {
        "naam": "Gecomprimeerd archief",
        "omschrijving": "Vaste omvang, gecomprimeerd en alleen-lezen — ideaal voor veilige archivering.",
    },
    "UDRW": {
        "naam": "Lees & schrijf",
        "omschrijving": "Bestanden toevoegen of verwijderen direct vanuit Finder.",
    },
    "UDSB": {
        "naam": "Meegroeiend pakket",
        "omschrijving": "Neemt alleen gebruikte schijfruimte en groeit mee bij nieuwe bestanden.",
    },
}


def extentie_voor(vorm: str) -> str:
    """De kluis-extentie hoort bij de vorm (UDSB = .sparsebundle, rest .dmg)."""
    if vorm == "UDSB":
        return ".sparsebundle"
    if vorm in ("UDZO", "UDRW"):
        return ".dmg"
    raise ValueError(f"Onbekende kluisvorm: {vorm!r} — kies uit {sorted(KLUIS_VORMEN)}")


# ---------------------------------------------------------------------------
# Padvalidatie (zoals validate_paths in SecureVault v2)
# ---------------------------------------------------------------------------


def valideer_bron(pad: str) -> str:
    """De bron moet een bestánde map zijn — een los bestand of niets faalt."""
    p = Path(pad).expanduser()
    if not p.exists():
        raise KluisFout(f"Bronmap bestaat niet: {pad}")
    if not p.is_dir():
        raise KluisFout(f"Bron is geen map: {pad}")
    return str(p.resolve())


def valideer_doel(pad: str) -> str:
    """De doelmap moet bestaan; we maken nooit stilletjes mappen aan."""
    p = Path(pad).expanduser()
    if not p.is_dir():
        raise KluisFout(f"Doelmap bestaat niet: {pad}")
    return str(p.resolve())


def controleer_overschrijven(pad: str, toestaan: bool) -> bool:
    """Bestaande kluis + geen expliciete toestemming = weigeren."""
    if os.path.lexists(os.path.expanduser(pad)):
        if not toestaan:
            raise KluisFout(
                f"Er bestaat al een kluis op: {pad}. "
                "Kies een andere naam, of bevestig overschrijven expliciet."
            )
        return True
    return False


# ---------------------------------------------------------------------------
# Wachtwoordsterkte + generator (zoals SecureVault v2)
# ---------------------------------------------------------------------------

STERKTE_GOED = 3  # drempel: score ≥ 3 = sterk genoeg


def wachtwoord_sterkte(pw: str) -> tuple[bool, str, int]:
    """Geef (sterk_geneg, reden, score 0-5) terug.

    Scoret lengte + soorten tekens, zoals check_password_strength in v2.
    """
    if not pw:
        return False, "Vul een wachtwoord in.", 0
    score = 0
    if len(pw) >= 12:
        score += 2
    elif len(pw) >= 8:
        score += 1
    soorten = 0
    if any(c.islower() for c in pw):
        soorten += 1
    if any(c.isupper() for c in pw):
        soorten += 1
    if any(c.isdigit() for c in pw):
        soorten += 1
    if any(c in string.punctuation for c in pw):
        soorten += 1
    score += soorten
    if len(pw) < 8:
        return False, "Wachtwoord is te kort (minimaal 8 tekens).", score
    if score >= STERKTE_GOED:
        return True, "Sterk genoeg.", score
    return False, "Voeg lengte, hoofdletters, cijfers of leestekens toe.", score


def genereer_wachtwoord(lengte: int = 20) -> str:
    """Cryptografisch sterk wachtwoord (secrets), zoals generate_secure_password."""
    alfabet = string.ascii_letters + string.digits + string.punctuation
    while True:
        pw = "".join(secrets.choice(alfabet) for _ in range(lengte))
        sterk, _, _ = wachtwoord_sterkte(pw)
        if sterk:
            return pw


# ---------------------------------------------------------------------------
# Sleutelhangar (macOS Keychain via de security CLI)
# ---------------------------------------------------------------------------


def keychain_sla_op(kluispad: str, wachtwoord: str) -> bool:
    """Sla het kluiswachtwoord op in de Sleutelhangar."""
    try:
        subprocess.run(
            [
                "security", "add-generic-password",
                "-s", f"GrowKit SecureVault: {kluispad}",
                "-a", os.getlogin(),
                "-w", wachtwoord,
                "-U",  # update als het item al bestaat
            ],
            check=True, capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def keychain_lees(kluispad: str) -> Optional[str]:
    """Lees het kluiswachtwoord; geen item = None (geen fout naar buiten)."""
    try:
        r = subprocess.run(
            [
                "security", "find-generic-password",
                "-s", f"GrowKit SecureVault: {kluispad}",
                "-w",
            ],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            return None
        return r.stdout.strip()
    except OSError:
        return None


def keychain_verwijder(kluispad: str) -> bool:
    try:
        subprocess.run(
            ["security", "delete-generic-password",
             "-s", f"GrowKit SecureVault: {kluispad}"],
            check=True, capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


# ---------------------------------------------------------------------------
# Audit-spoor (append-only, huisregel)
# ---------------------------------------------------------------------------


def _audit_pad() -> str:
    """Het audit-logboek van de kluis leeft per machine in ~/.growkit/."""
    return str(Path.home() / ".growkit" / "vault_audit.json")


def _audit_boek(actie: str, detail: dict) -> None:
    """Append-only audit-entry (nooit overschrijven van het verleden)."""
    pad = Path(_audit_pad())
    pad.parent.mkdir(parents=True, exist_ok=True)
    lijst: list = []
    if pad.is_file():
        try:
            lijst = json.loads(pad.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            lijst = []  # corrupt register → fris beginnen, nooit crashen
    lijst.append({
        "actie": actie,
        "moment": datetime.now(timezone.utc).isoformat(),
        **detail,
    })
    pad.write_text(json.dumps(lijst, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------------------
# Kluis maken / openen / sluiten (hdiutil)
# ---------------------------------------------------------------------------


def maak_kluis(
    bron: str,
    doelmap: str,
    naam: str,
    wachtwoord: str,
    vorm: str = "UDZO",
    overschrijven: bool = False,
) -> tuple[bool, str]:
    """Maak een AES-256/APFS-kluis via hdiutil.

    Het wachtwoord gaat via stdin (-stdinpass), nóóit in het commando.
    Geeft (gelukt, pad-of-melding) terug.
    """
    try:
        bronpad = valideer_bron(bron)
        doelpad = valideer_doel(doelmap)
        sterk, reden, _ = wachtwoord_sterkte(wachtwoord)
        if not sterk:
            return False, f"Wachtwoord te zwak: {reden}"
        extentie = extentie_voor(vorm)
        kluispad = os.path.join(doelpad, f"{naam}{extentie}")
        try:
            controleer_overschrijven(kluispad, toestaan=overschrijven)
        except KluisFout as e:
            return False, str(e)

        cmd = [
            "hdiutil", "create",
            "-srcfolder", bronpad.rstrip("/"),
            "-format", vorm,
            "-fs", "APFS",
            "-encryption", "AES-256",
            "-volname", naam,
            "-stdinpass",
            kluispad,
        ]
        r = subprocess.run(cmd, input=wachtwoord, capture_output=True, text=True)
        if r.returncode != 0:
            bericht = (r.stderr or "onbekende fout").strip()
            return False, f"Encryptie mislukt: {bericht}"
        _audit_boek("maken", {"kluis": kluispad, "vorm": vorm})
        return True, kluispad
    except KluisFout as e:
        return False, str(e)


def open_kluis(kluispad: str, wachtwoord: str) -> tuple[bool, str]:
    """Koppel een kluis aan (hdiutil attach). Geeft (gelukt, mountpunt-of-fout)."""
    cmd = [
        "hdiutil", "attach",
        "-stdinpass",
        "-readonly",  # veilige standaard: lezen eerst, schrijven expliciet
        kluispad,
    ]
    r = subprocess.run(cmd, input=wachtwoord, capture_output=True, text=True)
    if r.returncode != 0:
        stderr = (r.stderr or "").lower()
        if "authentication" in stderr or "wachtwoord" in stderr:
            return False, "Ontgrendelen mislukt: verkeerd wachtwoord."
        return False, f"Aankoppelen mislukt: {(r.stderr or 'onbekende fout').strip()}"
    mountpunt = ""
    for regel in r.stdout.splitlines():
        delen = regel.split("\t")
        if len(delen) >= 2 and "/Volumes/" in delen[-1]:
            mountpunt = delen[-1].split(" ")[0]
            break
    if not mountpunt:
        return False, "Aankoppelen gelukt, maar geen mountpunt gevonden."
    _audit_boek("openen", {"kluis": kluispad, "mount": mountpunt})
    return True, mountpunt


def sluit_kluis(mountpunt: str) -> bool:
    """Ontkoppel een open kluis (hdiutil detach)."""
    r = subprocess.run(
        ["hdiutil", "detach", mountpunt], capture_output=True, text=True,
    )
    if r.returncode == 0:
        _audit_boek("sluiten", {"mount": mountpunt})
        return True
    return False


def open_kluizen() -> list[str]:
    """Welke SecureVault-kluizen zijn nu open (hdiutil info)?"""
    r = subprocess.run(["hdiutil", "info"], capture_output=True, text=True)
    if r.returncode != 0:
        return []
    mounts: list[str] = []
    for regel in r.stdout.splitlines():
        if "APFS" in regel and "/Volumes/" in regel:
            pad = regel.split("\t")[-1].split(" ")[0]
            if pad.startswith("/Volumes/"):
                mounts.append(pad)
    return mounts


# ---------------------------------------------------------------------------
# Kluiszoeker (Spotlight via mdfind) — zoals v2.2.0
# ---------------------------------------------------------------------------


def zoek_kluizen() -> list[str]:
    """Vind SecureVault-kluizen op deze Mac via Spotlight."""
    r = subprocess.run(
        ["mdfind", "(kMDItemFSName == '*.dmg' || kMDItemFSName == '*.sparsebundle')"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return []
    gevonden = [
        regel.strip()
        for regel in r.stdout.splitlines()
        if regel.strip().endswith((".dmg", ".sparsebundle"))
    ]
    return gevonden
