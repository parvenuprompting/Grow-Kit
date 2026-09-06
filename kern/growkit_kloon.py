"""Digitale Kloon-kern voor GrowKit — inbouw van digitale-kloon-ios.

Inbouw van parvenuprompting/digitale-kloon-ios (MIT, Tiëndo Welles) als
GrowKit-kernmodule: een volledig lokale persoonlijke kluis.

Architectuur (getrouw aan het origineel):
- Vijf categorieën met vaste veldtemplates (VaultCategory.swift).
- Geheime velden AES-GCM-versleuteld; open velden plaintext.
- Master-sleutel (32 bytes, willekeurig) in de macOS Sleutelhangar —
  nooit in plaintext op schijf (MasterKeyService.swift).
- Data verlaat de kluis alleen door expliciete actie van de mens.
- Elke actie komt in het append-only log (huisregel van het huis).

Encryptie: AES-256-GCM via de `cryptography`-bibliotheek (industrie-
standaard, onderhoud door beveiligingsexperts). Dit is een bewuste,
gedocumenteerde uitzondering op de stdlib-only-regel: de directe
CommonCrypto-route via ctypes crashte hard (SIGSEGV) en het alternatief
zou de veiligheid van het origineel afzwakken. De bibliotheek leeft in
de repo-eigen omgeving (.venv), niet in het systeem.

Publieke functies:
    CATEGORIEEN                  — vijf categorieën met veldtemplates
    master_sleutel()             — lees of genereer de master-sleutel
    versleutel(tekst, sleutel)   — AES-GCM (nonce + cijfertekst)
    ontsleutel(data, sleutel)    — terug naar plaintext
    voeg_toe(titel, categorie, velden) — geheim opslaan
    lijst()                      — overzicht zonder geheimen
    lees_item(id)                — volledig item (met ontsleutelde velden)
    verwijder(id)                — geheim weg (met log-entry)
"""
from __future__ import annotations

import base64
import json
import secrets
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_LEN = 12

# ---------------------------------------------------------------------------
# Categorieën — letterlijk uit VaultCategory.swift
# ---------------------------------------------------------------------------

CATEGORIEEN: dict[str, dict] = {
    "wachtwoord": {
        "naam": "Wachtwoord",
        "velden": [("Gebruikersnaam", False), ("Wachtwoord", True)],
    },
    "apikey": {
        "naam": "API-key",
        "velden": [("Naam", False), ("Key", True)],
    },
    "bank": {
        "naam": "Bank / IBAN",
        "velden": [("IBAN", True), ("Naam rekeninghouder", False)],
    },
    "crypto": {
        "naam": "Crypto",
        "velden": [("Wallet", False), ("Private key / seed", True)],
    },
    "account": {
        "naam": "Account",
        "velden": [("Accountnaam", False), ("Wachtwoord", True)],
    },
    "notitie": {
        "naam": "Notities",
        "velden": [("Onderwerp", False), ("Notitie", True)],
    },
}

# ---------------------------------------------------------------------------
# Master-sleutel (Sleutelhangar) — zoals MasterKeyService.swift
# ---------------------------------------------------------------------------

_KEYCHAIN_SERVICE = "GrowKit Digitale Kloon: master"


def keychain_lees(dienst: str = _KEYCHAIN_SERVICE) -> Optional[str]:
    try:
        r = subprocess.run(
            ["security", "find-generic-password", "-s", dienst, "-w"],
            capture_output=True, text=True,
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except OSError:
        return None


def keychain_sla_op(waarde: str, dienst: str = _KEYCHAIN_SERVICE) -> bool:
    try:
        subprocess.run(
            ["security", "add-generic-password", "-s", dienst,
             "-a", "master", "-w", waarde, "-U"],
            check=True, capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def master_sleutel() -> str:
    """Bestaande master-sleutel (base64) of genereer + bewaar één keer."""
    bestaande = keychain_lees()
    if bestaande:
        return bestaande
    nieuw = base64.b64encode(secrets.token_bytes(32)).decode()
    if not keychain_sla_op(nieuw):
        raise RuntimeError("Master-sleutel kon niet in de Sleutelhangar worden bewaard.")
    return nieuw


# ---------------------------------------------------------------------------
# AES-256-GCM (cryptography-bibliotheek, zie module-docstring)
# ---------------------------------------------------------------------------


def versleutel(tekst: str, sleutel: str) -> bytes:
    """AES-GCM-encryptie; geeft nonce (12) + cijfertekst (incl. tag) terug."""
    sleutel_bytes = base64.b64decode(sleutel)
    nonce = secrets.token_bytes(_NONCE_LEN)
    cijfertekst = AESGCM(sleutel_bytes).encrypt(
        nonce, tekst.encode(), None)
    return nonce + cijfertekst


def ontsleutel(data: bytes, sleutel: str) -> str:
    """AES-GCM-decryptie; faalt met ValueError bij verkeerde sleutel of
    gewijzigde data (authenticatie-tag)."""
    sleutel_bytes = base64.b64decode(sleutel)
    nonce, cijfertekst = data[:_NONCE_LEN], data[_NONCE_LEN:]
    if len(nonce) != _NONCE_LEN or not cijfertekst:
        raise ValueError("Versleutelde data te kort")
    try:
        plat = AESGCM(sleutel_bytes).decrypt(nonce, cijfertekst, None)
    except Exception as e:
        raise ValueError(
            "Ontsleutelen mislukt (verkeerde sleutel of gewijzigde data)") from e
    return plat.decode()


# ---------------------------------------------------------------------------
# Opslag + log
# ---------------------------------------------------------------------------


def _kluis_pad() -> Path:
    return Path.home() / ".growkit" / "kloon_kluis.json"


def _log_pad() -> Path:
    return Path.home() / ".growkit" / "kloon_log.json"


def _log(actie: str, detail: dict) -> None:
    """Append-only log: nooit overschrijven van het verleden."""
    pad = Path(_log_pad())
    pad.parent.mkdir(parents=True, exist_ok=True)
    lijst: list = []
    if pad.is_file():
        try:
            lijst = json.loads(pad.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            lijst = []
    lijst.append({
        "actie": actie,
        "moment": datetime.now(timezone.utc).isoformat(),
        **detail,
    })
    pad.write_text(json.dumps(lijst, ensure_ascii=False, indent=1), encoding="utf-8")


def _laad_kluis() -> dict:
    pad = _kluis_pad()
    if not pad.is_file():
        return {"items": []}
    return json.loads(pad.read_text(encoding="utf-8"))


def _bewaar_kluis(kluis: dict) -> None:
    pad = Path(_kluis_pad())
    pad.parent.mkdir(parents=True, exist_ok=True)
    pad.write_text(json.dumps(kluis, ensure_ascii=False, indent=1), encoding="utf-8")


def voeg_toe(titel: str, categorie: str, velden: dict[str, str]) -> dict:
    """Nieuw geheim: geheime velden versleuteld, open velden plaintext."""
    if categorie not in CATEGORIEEN:
        raise ValueError(f"Onbekende categorie: {categorie} — kies uit {sorted(CATEGORIEEN)}")
    if not titel.strip():
        raise ValueError("Titel mag niet leeg zijn")
    sleutel = master_sleutel()
    geheime_velden: dict[str, str] = {}
    open_velden: dict[str, str] = {}
    for naam, waarde in velden.items():
        is_geheim = any(naam == v[0] and v[1] for v in CATEGORIEEN[categorie]["velden"])
        if is_geheim:
            versleuteld = versleutel(waarde, sleutel)
            geheime_velden[naam] = base64.b64encode(versleuteld).decode()
        else:
            open_velden[naam] = waarde
    item_id = uuid.uuid4().hex[:8]
    item = {
        "id": item_id,
        "titel": titel.strip(),
        "categorie": categorie,
        "velden_open": open_velden,
        "velden_versleuteld": geheime_velden,
        "aangemaakt": datetime.now(timezone.utc).isoformat(),
    }
    kluis = _laad_kluis()
    kluis["items"].append(item)
    _bewaar_kluis(kluis)
    _log("toevoegen", {"id": item_id, "titel": item["titel"], "categorie": categorie})
    return item


def lijst() -> list[dict]:
    """Overzicht: titels, categorie en open velden — géén geheimen."""
    return [
        {
            "id": i["id"],
            "titel": i["titel"],
            "categorie": i["categorie"],
            "velden_open": i["velden_open"],
            "aangemaakt": i["aangemaakt"],
        }
        for i in _laad_kluis()["items"]
    ]


def lees_item(item_id: str) -> dict:
    """Volledig item met ontsleutelde geheime velden (expliciete actie)."""
    sleutel = master_sleutel()
    for i in _laad_kluis()["items"]:
        if i["id"] == item_id:
            ontsleuteld = {}
            for naam, data64 in i["velden_versleuteld"].items():
                ontsleuteld[naam] = ontsleutel(base64.b64decode(data64), sleutel)
            _log("lezen", {"id": item_id, "titel": i["titel"]})
            return {**i, "velden_ontsleuteld": ontsleuteld}
    raise ValueError(f"Onbekend item: {item_id}")


def verwijder(item_id: str) -> bool:
    kluis = _laad_kluis()
    nieuwe = [i for i in kluis["items"] if i["id"] != item_id]
    if len(nieuwe) == len(kluis["items"]):
        return False
    _bewaar_kluis({"items": nieuwe})
    _log("verwijderen", {"id": item_id})
    return True
