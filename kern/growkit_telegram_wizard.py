"""GrowKit Telegram-wizard B1 (ZT-8) — wizard-staat voor de 6 stappen.

Begeleidt de gebruiker door de BotFather-stappen:
  1. bot maken      2. token plakken   3. chat-ID
  4. config-velden  5. herstart        6. /status-test

Geen automatische bot-aanmaak — de mens doet de stappen. De kern houdt
alleen de voortgang bij en maskt tokens: de volledige token verlaat
deze module nooit (alleen de laatste 4 tekens zijn zichtbaar, in de
staat én in log-regels).

Regels:
- stap n+1 is pas beschikbaar na afronden van stap n;
- token-masking: alleen laatste 4 tekens zichtbaar;
- config-voorbeeld bevat een token-placeholder, nooit een echte token;
- dump_staat()/herstart() slaan de voortgang op zonder tokens en
  herstellen netjes op dezelfde stap — geen halve staat.
"""
from __future__ import annotations

import json
import re

_STAP_LABELS = [
    "BotFather: bot maken (/newbot)",
    "Token plakken (alleen laatste 4 tekens worden getoond)",
    "Chat-ID bepalen (@userinfobot)",
    "Config-velden controleren (config.yaml)",
    "Gateway-herstart",
    "Test: /status naar de bot",
]

# BotFather-formaat: 6 cijfers, ':', daarna 30+ token-tekens.
_TOKEN_PATROON = re.compile(r"^\d{6}:[A-Za-z0-9_-]{30,}$")
_PLACEHOLDER = "<TELEGRAM-BOT-TOKEN>"


class TokenFout(Exception):
    """Ongeldig token of ongeldige wizard-staat."""


def nieuw() -> dict:
    """Nieuwe wizard-staat: 6 stappen, alleen stap 1 open."""
    stappen = [
        {"nr": i + 1, "label": label, "open": i == 0, "gedaan": False}
        for i, label in enumerate(_STAP_LABELS)
    ]
    return {
        "stappen": stappen,
        "huidige": 1,
        "afgerond": False,
        "token_gemaskt": None,
    }


def mask_token(token: str) -> str:
    """Alleen de laatste 4 tekens zichtbaar, met ellips vooraf."""
    if not isinstance(token, str) or len(token) < 4:
        return "…" + (token or "")
    return "…" + token[-4:]


def _zetter(w: dict, nr: int) -> dict:
    """Interne helper: markeer stap nr afgerond en open de volgende."""
    stappen = [dict(s) for s in w["stappen"]]
    for s in stappen:
        if s["nr"] == nr:
            s["gedaan"] = True
        elif s["nr"] == nr + 1:
            s["open"] = True
    volgende = min(nr + 1, 6)
    return {
        "stappen": stappen,
        "huidige": volgende,
        "afgerond": w["afgerond"] or nr >= 6,
        "token_gemaskt": w["token_gemaskt"],
    }


def stap_afgerond(w: dict, nr: int) -> tuple[bool, dict]:
    """Stap nr afronden. Alleen als alle eerdere stappen al afgerond
    zijn (sequentieel). Geeft (toegestaan, nieuwe_staat)."""
    if nr < 1 or nr > 6 or not isinstance(nr, int):
        return False, w
    # elke stap vóór nr moet al 'open' (afgerond) zijn
    for s in w["stappen"]:
        if s["nr"] < nr and not s["gedaan"]:
            return False, w
    if w["afgerond"] and nr <= 6:
        return False, w
    return True, _zetter(w, nr)


def token_zetten(w: dict, token: str) -> tuple[dict, dict]:
    """Token inlezen bij stap 2. Validatie op formaat; de volledige
    token komt NOOIT in de retourwaarde — alleen het gemaskte deel
    wordt in de staat gezet."""
    if not isinstance(token, str) or not _TOKEN_PATROON.match(token):
        raise TokenFout("token voldoet niet aan het BotFather-formaat")
    if not w["stappen"][1]["open"]:
        raise TokenFout("stap 2 is nog niet beschikbaar")
    nieuwe = _zetter(w, 2)  # token invullen is stap 2 afronden
    nieuwe["token_gemaskt"] = mask_token(token)
    resultaat = {
        "ok": True,
        "token_gemaskt": nieuwe["token_gemaskt"],
        "melding": "token ontvangen — hij leeft voortaan in de "
                   "Sleutelhangar, de app toont alleen de laatste 4 "
                   "tekens",
    }
    return nieuwe, resultaat


def log_regels_token(token: str) -> list[str]:
    """Log-regels bij token-invoer — altijd gemaskt, nooit de
    volledige token."""
    gemaskt = mask_token(token)
    return [
        "wizard: token ingevuld, zichtbaar als " + gemaskt,
        "wizard: token verplaatst naar Sleutelhangar (" + gemaskt + ")",
    ]


def config_voorbeeld(w: dict) -> str:
    """Config-voorbeeld met token-placeholder — géén echte token."""
    _ = w  # de staat bevat alleen de gemaskte token; placeholder is vast
    return (
        "# config.yaml — Telegram-velden\n"
        "telegram:\n"
        "  bot_token: " + _PLACEHOLDER + "   # uit de Sleutelhangar\n"
        "  chat_id: <TELEGRAM-CHAT-ID>\n"
        "  herstart: systemctl --user restart telegram-gateway\n"
    )


def dump_staat(w: dict) -> str:
    """Voortgang opslaan zonder tokens: labels, open-vlaggen, positie."""
    return json.dumps({
        "stappen": [
            {"nr": s["nr"], "label": s["label"], "open": s["open"],
             "gedaan": s["gedaan"]}
            for s in w["stappen"]
        ],
        "huidige": w["huidige"],
        "afgerond": w["afgerond"],
        "token_gemaskt": w["token_gemaskt"],
    })


def herstart(dump: str) -> dict:
    """Herstart een afgebroken wizard op dezelfde stap — geen halve
    staat: ongeldige dumps worden geweigerd, niet geraden."""
    try:
        data = json.loads(dump)
        stappen = data["stappen"]
        huidige = data["huidige"]
        afgerond = data["afgerond"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise TokenFout("wizard-staat is ongeldig of beschadigd") from e
    if (
        not isinstance(stappen, list)
        or len(stappen) != 6
        or not isinstance(huidige, int)
        or not 1 <= huidige <= 6
        or not isinstance(afgerond, bool)
    ):
        raise TokenFout("wizard-staat is ongeldig of beschadigd")
    for s in stappen:
        if (not isinstance(s, dict) or "nr" not in s or "open" not in s
                or "gedaan" not in s):
            raise TokenFout("wizard-staat is ongeldig of beschadigd")
    # geen halve staat: 'afgerond' impliceert alle stappen open
    if afgerond and not all(s["gedaan"] for s in stappen):
        raise TokenFout("wizard-staat is ongeldig of beschadigd")
    return {
        "stappen": [
            {"nr": s["nr"], "label": s["label"], "open": bool(s["open"]),
             "gedaan": bool(s["gedaan"])}
            for s in stappen
        ],
        "huidige": huidige,
        "afgerond": afgerond,
        "token_gemaskt": data.get("token_gemaskt"),
    }