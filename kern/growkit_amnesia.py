"""Amnesia-kern voor GrowKit — inbouw van Amnesia Protocol Lite.

Inbouw van parvenuprompting/amnesia-protocol-lite (MIT, Tiëndo Welles)
als GrowKit-kernmodule. Lokale detectoren vinden gevoelige waarden in
tekst; de mens keurt per vondst; geaccepteerde waarden worden markers
(EMAIL_1); een aparte synthetische laag maakt van markers fictieve
waarden. Alles lokaal, stdlib-only.

Kernprincipes (uit het origineel):
- Detectie is nooit garantie: de mens beoordeelt elke kandidaat.
- Dezelfde waarde krijgt binnen één sessie hetzelfde token.
- Laag 2 ontvangt uitsluitend markers, nooit bronwaarden.
- Mapping leeft sessiegebonden; de zaad-parameter maakt haar testbaar.

Publieke functies:
    detecteer(tekst)            — kandidaten (context- + patroonregels)
    detecteer_terminal(tekst)   — + secrets/JWT/private keys/URL's
    bouw_markers(vondsten)      — token-map voor geaccepteerde waarden
    veilige_tekst(tekst, …)     — geaccepteerde waarden → markers
    parse_markers(tekst)        — markers in laag-2-tekst
    synthetische_waarde(…)      — één fictieve waarde
    bouw_synthetische_map(…)    — map voor alle markers
    vervang_markers(tekst, map) — markers → fictieve waarden
"""
from __future__ import annotations

import hashlib
import random
import re
from typing import Optional

MAX_INVOER_LENGTE = 1_000_000

# ---------------------------------------------------------------------------
# Patronen — overgenomen uit detectors.ts (regel voor regel vertaald)
# ---------------------------------------------------------------------------

# (type, regex, zekerheid). Namen in het Nederlands, zoals in de UI.
_PATRONEN = [
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), 0.99),
    ("telefoon", re.compile(
        r"(?<!\d)(?:\+31[ -]?(?:[1-9]\d{0,2}|[89]00)[ -]?\d{3,4}[ -]?\d{3,4}"
        r"|0[1-9]\d{1,2}[ -]?\d{3,4}[ -]?\d{3,4}|0[89]00[ -]?\d{4,7}|06[ -]?\d{8})(?!\d)", re.I), 0.96),
    ("iban", re.compile(r"\bNL\s?\d{2}\s?[A-Z]{4}\s?(?:\d{4}\s?){2}\d{2}\b", re.I), 0.99),
    ("bsn", re.compile(r"(?<!\d)\d{9}(?!\d)"), 0.97),
    ("ip", re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"), 0.92),
    ("postcode", re.compile(
        r"(?<![\dA-Z])\d{4}\s?[A-Z]{2}(?:\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)?(?![A-Z])"), 0.92),
    ("adres", re.compile(
        r"\b[A-Z][a-z]+(?:straat|weg|laan|plein|gracht|kade|dijk|steeg|singel|dreef|berg|dorp|hof|pad|allee|ring)\s+\d+\s?[a-zA-Z]?(?!\d)"), 0.93),
    ("datum", re.compile(
        r"(?<!\w)(?:0?[1-9]|[12]\d|3[01])\s+(?:januari|februari|maart|april|mei|juni|juli"
        r"|augustus|september|oktober|november|december|jan|feb|mrt|apr|jun|jul|aug|sep|okt|nov|dec)"
        r"\.?\s+(?:\d{4}|'\d{2}|\d{2})\b", re.I), 0.94),
    ("datum", re.compile(
        r"(?<!\d)(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.](?:\d{4}|\d{2})(?!\d)"), 0.9),
    ("datum", re.compile(
        r"(?<!\d)\d{4}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])(?!\d)"), 0.9),
    ("persoon", re.compile(
        r"\b[A-Z]\.(?:[A-Z]\.)+\s+(?:(?:van|de|den|der|het|t'|von|le|la)\s+)*[A-Z][a-zA-Z-]+\b"), 0.95),
    ("persoon", re.compile(
        r"\b[A-Z][a-z]{2,}\s+(?:van\s+(?:der\s+|den\s+)?|de\s+|het\s+)[A-Z][a-z]{2,}\b"), 0.85),
    ("referentie", re.compile(r"\bNL\s?[\d.]{9,12}\s?B\s?\d{2}\b", re.I), 0.96),
    ("referentie", re.compile(r"\b\d{2}\.\d{3}\.\d{3}\b"), 0.9),
    ("link", re.compile(r"\bhttps?://[^\s<>\"{}|\\^`]+(?<![.,;!?:)])", re.I), 0.96),
]

# Contextregels: het label bepaalt het type ('klantnummer: 883746').
_CONTEXT = [
    ("klantnummer", re.compile(
        r"\b(?:klantnummer|klantnr\.?|customer\s*(?:number|id)?|lid-?\/?relatienummer"
        r"|lidnummer|lidnr\.?|relatienummer|relatienr\.?|accountnummer|accountnr\.?"
        r"|polisnummer|polisnr\.?|gebruikersid|personeelsnummer|medewerkersnummer)"
        r"\s*[:#-]?\s*(?P<waarde>[A-Z0-9][A-Z0-9-]{3,})\b", re.I), 0.98),
    ("klantnummer", re.compile(
        r"[\"']?(?:customer|customer[_ -]?number|klant[_ -]?nr\.?)[\"']?\s*[:=]\s*"
        r"[\"']?(?P<waarde>[A-Z0-9][A-Z0-9-]{3,})[\"']?", re.I), 0.96),
    ("transactie", re.compile(
        r"\b(?:transactie(?:nummer|id)?|ordernummer|bestelnummer|factuurnummer"
        r"|facturnr\.?|ticketnummer|interactienummer|betalingskenmerk|rekeningnummer)"
        r"\s*[:#-]?\s*(?P<waarde>[A-Z0-9][A-Z0-9-]{3,})\b", re.I), 0.98),
    ("serienummer", re.compile(
        r"\b(?:serienummer|serial\s*number|apparaat-?id|device\s*id|contractnummer"
        r"|chassisnummer)\s*[:#-]?\s*(?P<waarde>[A-Z0-9][A-Z0-9-]{3,})\b", re.I), 0.98),
    ("referentie", re.compile(
        r"\b(?:dossier(?:nummer)?|zaaknummer|referentie(?:nummer)?|case\s*id"
        r"|kvk\s*(?:nr\.?|nummer)?|btw\s*(?:nr\.?|nummer)?|vat\s*(?:nr\.?|number)?)"
        r"\s*[:#-]?\s*(?P<waarde>[A-Z0-9.-]{3,})\b", re.I), 0.96),
    ("persoon", re.compile(
        r"\b(?:naam|heer|mevrouw|dhr\.?|mvr\.?|geadresseerde|t\.a\.v\.?|tav"
        r"|contactpersoon|patient|cliënt|client)\s*[:#-]?\s*"
        r"(?P<waarde>[A-Z][a-zA-Z.-]+(?:\s+(?:van|de|den|der|het|t'|von|le|la)\b)*\s+[A-Z][a-zA-Z-]+)\b", re.I), 0.96),
    ("datum", re.compile(
        r"\b(?:factuurdatum|geboortedatum|vervaldatum|datum|periode)\s*[:#-]?\s*"
        r"(?P<waarde>(?:0?[1-9]|[12]\d|3[01])\s+(?:januari|februari|maart|april|mei|juni|juli"
        r"|augustus|september|oktober|november|december|jan|feb|mrt|apr|jun|jul|aug|sep|okt|nov|dec)"
        r"\.?\s+(?:\d{4}|\d{2})|(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.](?:\d{4}|\d{2}))\b", re.I), 0.98),
    ("telefoon", re.compile(
        r"\b(?:telefoon(?:nummer)?|tel\.?|mobiel|phone|fax|t:)\s*[:#-]?\s*"
        r"(?P<waarde>(?:\+31[ -]?(?:[1-9]\d{0,2}|[89]00)[ -]?\d{3,4}[ -]?\d{3,4}"
        r"|0[1-9]\d{1,2}[ -]?\d{3,4}[ -]?\d{3,4}|0[89]00[ -]?\d{4,7}|06[ -]?\d{8}))\b", re.I), 0.98),
    ("link", re.compile(
        r"\b(?:internet|website|web|url|site)\s*[:#-]?\s*"
        r"(?P<waarde>https?://[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:/[^\s]*)?)\b", re.I), 0.95),
    ("adres", re.compile(
        r"\b(?:adres|straat|woonadres|postadres|vestigingsadres)\s*[:#-]?\s*"
        r"(?P<waarde>[A-Z][a-zA-Z0-9\s.-]+?\s+\d+\s?[a-zA-Z]?)\b", re.I), 0.95),
    ("geheim", re.compile(
        r"\b(?:password|passwd|secret|token|api[_-]?key|access[_-]?key)\s*[=:]\s*"
        r"[\"']?(?P<waarde>[^\s\"']{8,})[\"']?", re.I), 0.94),
]

# Terminal-regels: secrets in logs en shell-uitvoer.
_TERMINAL_CONTEXT = [
    ("accesstoken", re.compile(
        r"\b(?:authorization|proxy-authorization)\s*:\s*bearer\s+(?P<waarde>[A-Za-z0-9._~+/-]{12,})", re.I), 0.99),
    ("geheim", re.compile(
        r"\b(?:password|passwd|secret|token|api[_-]?key|access[_-]?key)\s*[=:]\s*"
        r"[\"']?(?P<waarde>[^\s\"']{8,})[\"']?", re.I), 0.94),
    ("account", re.compile(r"(?:/Users/|/home/)(?P<waarde>[A-Za-z0-9._-]{2,})"), 0.96),
]

_TERMINAL = [
    ("privatekey", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"), 1.0),
    ("jwt", re.compile(
        r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), 0.99),
    ("apikey", re.compile(
        r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b|\bgh[pousr]_[A-Za-z0-9_]{20,}\b"
        r"|\bxox[baprs]-[A-Za-z0-9-]{20,}\b"), 0.99),
    ("cloudresource", re.compile(r"\barn:(?:aws|azure|gcp):[^\s]+\b", re.I), 0.95),
    ("gitremote", re.compile(
        r"\b(?:https?://[^\s/@]+(?::[^\s/@]+)?@github\.com/[^\s]+|git@github\.com:[^\s]+|"
        r"https?://[^/\s@]+@github\.com/[^\s]+)\b", re.I), 0.995),
    ("credentialurl", re.compile(
        r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s]+", re.I), 0.98),
    ("pad", re.compile(r"(?<![\w])(?:/Users/[^\s]+|/home/[^\s]+)"), 0.8),
]

# Markernamen (laag 2 ziet ALLÉÉN deze korte codes, nooit bronwaarden).
MARKER_SOORTEN = {
    "EMAIL": "email", "PHONE": "telefoon", "IBAN": "iban", "BSN": "bsn",
    "IP": "ip", "POSTCODE": "postcode", "ADDRESS": "adres", "DATE": "datum",
    "CUSTOMER": "klantnummer", "TRANSACTION": "transactie", "SERIAL": "serienummer",
    "REFERENCE": "referentie", "PERSON": "persoon", "LINK": "link",
    "OTHER": "overig", "APIKEY": "apikey", "ACCESSTOKEN": "accesstoken",
    "JWT": "jwt", "PRIVATEKEY": "privatekey", "CREDENTIALURL": "credentialurl",
    "SECRET": "geheim", "ACCOUNT": "account", "PATH": "pad",
    "GITREMOTE": "gitremote", "CLOUDRESOURCE": "cloudresource",
}
_MARKER_NAAR_SOORT = {soort: code for code, soort in MARKER_SOORTEN.items()}


# ---------------------------------------------------------------------------
# Validatie (mod-97 IBAN, elfproef BSN, IP-bereik, echte datums)
# ---------------------------------------------------------------------------


def _normaal(waarde: str) -> str:
    return re.sub(r"[\s-]", "", waarde).upper()


def is_geldig_iban(waarde: str) -> bool:
    n = _normaal(waarde)
    if not re.fullmatch(r"NL\d{2}[A-Z]{4}\d{10}", n):
        return False
    herschud = n[4:] + n[:4]
    numeriek = "".join(
        str(ord(c) - 55) if c.isalpha() else c for c in herschud
    )
    rest = 0
    for cijfer in numeriek:
        rest = (rest * 10 + int(cijfer)) % 97
    return rest == 1


def is_geldig_bsn(waarde: str) -> bool:
    cijfers = re.sub(r"\D", "", waarde)
    if not re.fullmatch(r"\d{9}", cijfers) or len(set(cijfers)) == 1:
        return False
    som = sum(
        int(c) * (-1 if i == 8 else 9 - i) for i, c in enumerate(cijfers)
    )
    return som % 11 == 0


def _geldig_ip(waarde: str) -> bool:
    return all(int(deel) <= 255 for deel in waarde.split("."))


_MAANDEN = ("januari", "februari", "maart", "april", "mei", "juni", "juli",
            "augustus", "september", "oktober", "november", "december",
            "jan", "feb", "mrt", "apr", "jun", "jul", "aug", "sep", "okt",
            "nov", "dec")


def _geldig_datum(waarde: str) -> bool:
    if any(m in waarde.lower() for m in _MAANDEN):
        return True
    delen = re.split(r"[-/.]", waarde)
    if len(delen) != 3:
        return False
    try:
        a, b, c = (int(d) for d in delen)
    except ValueError:
        return False
    dag, maand, jaar = (c, b, a) if a > 1000 else (a, b, c)
    if jaar < 100:
        jaar += 2000
    try:
        import datetime
        datetime.date(jaar, maand, dag)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Detectie
# ---------------------------------------------------------------------------


def _context_kandidaten(tekst: str, regels) -> list[dict]:
    kandidaten = []
    for soort, rx, zekerheid in regels:
        for m in rx.finditer(tekst):
            ruw = m.group("waarde")
            if not ruw or not ruw.strip():
                continue
            begin = m.start("waarde") + (len(ruw) - len(ruw.lstrip()))
            waarde = ruw.strip()
            kandidaten.append({
                "start": begin, "einde": begin + len(waarde),
                "waarde": waarde, "type": soort,
                "zekerheid": zekerheid, "bron": "regex",
                "besluit": "open",
            })
    return kandidaten


def _patroon_kandidaten(tekst: str, regels) -> list[dict]:
    kandidaten = []
    for soort, rx, zekerheid in regels:
        for m in rx.finditer(tekst):
            waarde = m.group(0)
            geldig = True
            z = zekerheid
            if soort == "iban":
                geldig = is_geldig_iban(waarde)
            elif soort == "bsn":
                geldig = is_geldig_bsn(waarde)
            elif soort == "ip":
                geldig = _geldig_ip(waarde)
            elif soort == "datum":
                geldig = _geldig_datum(waarde)
            if not geldig:
                if soort in ("iban", "bsn"):
                    z = 0.45
                else:
                    continue
            kandidaten.append({
                "start": m.start(), "einde": m.end(),
                "waarde": waarde, "type": soort,
                "zekerheid": z, "bron": "regex",
                "besluit": "open",
            })
    return kandidaten


def _los_overlap_op(kandidaten: list[dict]) -> list[dict]:
    """Hoogste zekerheid wint; bij gelijkspel de langste match (zoals het origineel)."""
    gesorteerd = sorted(
        kandidaten, key=lambda k: (k["start"], -(k["einde"] - k["start"]))
    )
    resultaat: list[dict] = []
    for k in gesorteerd:
        vorige = resultaat[-1] if resultaat else None
        if not vorige or k["start"] >= vorige["einde"]:
            resultaat.append(k)
        elif k["zekerheid"] > vorige["zekerheid"]:
            resultaat[-1] = k
        elif (k["zekerheid"] == vorige["zekerheid"]
              and k["einde"] - k["start"] > vorige["einde"] - vorige["start"]):
            resultaat[-1] = k
    resultaat.sort(key=lambda k: k["start"])
    for i, k in enumerate(resultaat, 1):
        k["id"] = f"vondst-{i}"
    return resultaat


def _detecteer(tekst: str, terminal: bool) -> list[dict]:
    if len(tekst) > MAX_INVOER_LENGTE:
        raise ValueError(
            f"Tekst is te groot om veilig te analyseren. Maximum is {MAX_INVOER_LENGTE:,} tekens.".replace(",", ".")
        )
    kandidaten = _context_kandidaten(tekst, _CONTEXT) + _patroon_kandidaten(tekst, _PATRONEN)
    if terminal:
        kandidaten += _context_kandidaten(tekst, _TERMINAL_CONTEXT)
        kandidaten += _patroon_kandidaten(tekst, _TERMINAL)
    return _los_overlap_op(kandidaten)


def detecteer(tekst: str) -> list[dict]:
    """Kandidaat-vondsten in gewone tekst (review in de app beslist)."""
    return _detecteer(tekst, terminal=False)


def detecteer_terminal(tekst: str) -> list[dict]:
    """Kandidaten in terminal-uitvoer: + secrets, JWT, keys, URL's, paden."""
    return _detecteer(tekst, terminal=True)


def detecteer_token(tekst: str) -> list[dict]:
    """Alias voor terminal-detectie op losse tokens (leesbaarheid in tests/UI)."""
    return detecteer_terminal(tekst)


# ---------------------------------------------------------------------------
# Markers (laag 1 → veilige tekst)
# ---------------------------------------------------------------------------


def bouw_markers(vondsten: list[dict], zaad: Optional[int] = None) -> dict[str, str]:
    """Token-map voor geaccepteerde/aangepaste vondsten.

    Zelfde waarde → zelfde token binnen de sessie. Tokens zijn sessie-
    gebonden: met een ander zaad krijgen nieuwe sessies andere tokens.
    """
    tokens: dict[str, str] = {}
    tellers: dict[str, int] = {}
    for v in vondsten:
        if v.get("besluit") not in ("geaccepteerd", "aangepast"):
            continue
        waarde = v["waarde"]
        if waarde in tokens:
            continue
        soort = _MARKER_NAAR_SOORT.get(v["type"], "OTHER")
        tellers[soort] = tellers.get(soort, 0) + 1
        tokens[waarde] = f"{soort}_{tellers[soort]}"
    return tokens


def veilige_tekst(tekst: str, vondsten: list[dict], tokens: dict[str, str]) -> str:
    """Vervang alleen geaccepteerde/aangepaste waarden door hun marker."""
    vervangen = [
        v for v in vondsten
        if v.get("besluit") in ("geaccepteerd", "aangepast")
    ]
    resultaat = tekst
    for v in sorted(vervangen, key=lambda k: k["start"], reverse=True):
        marker = tokens.get(v["waarde"], v["waarde"])
        resultaat = resultaat[:v["start"]] + marker + resultaat[v["einde"]:]
    return resultaat


# ---------------------------------------------------------------------------
# Synthetische laag (laag 2: markers → fictieve waarden)
# ---------------------------------------------------------------------------

_VOORNAMEN = ("Liam", "Emma", "Lucas", "Mila", "Noah", "Sofia", "Daan",
              "Julia", "Sem", "Anna", "Milan", "Lotte")
_ACHTERNAMEN = ("de Vries", "Jansen", "van den Berg", "Bakker", "Visser",
                "Smit", "Meijer", "de Boer", "Mulder", "Bos")
_DOMEINEN = ("voorbeeldmail.nl", "voorbeeld.nl", "fictiefbedrijf.nl",
             "voorbeeldorg.nl", "demosite.nl")
_STRAATNAMEN = ("Dorpsstraat", "Kerkweg", "Molenlaan", "Schoolstraat",
                "Lindenlaan", "Beukenhof")


def parse_markers(tekst: str) -> list[dict]:
    """Welke markers zitten in laag-2-tekst (dubbele eruit)?"""
    gevonden: list[dict] = []
    gezien: set[str] = set()
    for m in re.finditer(r"\b([A-Z]+)_(\d+)\b", tekst):
        token = m.group(0)
        soort = MARKER_SOORTEN.get(m.group(1))
        if not soort or token in gezien:
            continue
        gezien.add(token)
        gevonden.append({"token": token, "type": soort})
    return gevonden


def synthetische_waarde(soort: str, token: str, zaad: int) -> str:
    """Deterministische fictieve waarde voor één marker (zelfde zaad = zelfde waarde)."""
    ruw = f"{soort}:{token}:{zaad}"
    zaad_hash = int(hashlib.sha256(ruw.encode()).hexdigest()[:12], 16)
    r = random.Random(zaad_hash)

    def cijfers(n: int) -> str:
        return "".join(r.choice("0123456789") for _ in range(n))

    def letters(n: int) -> str:
        return "".join(r.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(n))

    if soort == "email":
        return (f"{r.choice(_VOORNAMEN).lower()}."
                f"{r.choice(_ACHTERNAMEN).lower().replace(' ', '.')}@{r.choice(_DOMEINEN)}")
    if soort == "persoon":
        return f"{r.choice(_VOORNAMEN)} {r.choice(_ACHTERNAMEN)}"
    if soort == "telefoon":
        return f"06-{cijfers(8)}"
    if soort == "iban":
        return f"NL{cijfers(2)}{letters(4).upper()}{cijfers(10)}"
    if soort == "bsn":
        while True:
            c = cijfers(9)
            som = sum(int(x) * (-1 if i == 8 else 9 - i) for i, x in enumerate(c))
            if som % 11 == 0 and len(set(c)) > 1:
                return c
    if soort == "ip":
        return f"10.{r.randint(0, 255)}.{r.randint(0, 255)}.{r.randint(0, 255)}"
    if soort == "postcode":
        return f"{cijfers(4)} {letters(2).upper()}"
    if soort == "adres":
        return f"{r.choice(_STRAATNAMEN)} {r.randint(1, 200)}"
    if soort == "datum":
        return f"{r.randint(1, 28)}-{r.randint(1, 12)}-{r.randint(1950, 2025)}"
    if soort == "klantnummer":
        return cijfers(9)
    if soort == "transactie":
        return f"2003{cijfers(7)}"
    if soort == "serienummer":
        return f"{letters(4).upper()}-{cijfers(4)}-{letters(4).upper()}"
    if soort == "referentie":
        return f"{cijfers(2)}.{cijfers(3)}.{cijfers(3)}"
    if soort == "link":
        return f"https://www.{r.choice(_DOMEINEN)}/pagina"
    if soort == "apikey":
        return f"AKIA{letters(16).upper()}"
    if soort == "accesstoken":
        return f"tok_{letters(28)}{cijfers(4)}"
    if soort == "jwt":
        return f"eyJ{letters(18)}.{letters(24)}.{letters(32)}"
    if soort == "privatekey":
        return "[REDACTED PRIVATE KEY]"
    if soort == "credentialurl":
        return "postgresql://fictief:***@localhost:5432/voorbeeld"
    if soort == "geheim":
        return f"secret_{letters(18)}"
    if soort == "account":
        return f"{r.choice(_VOORNAMEN).lower()}.{r.choice(_ACHTERNAMEN).lower().replace(' ', '-')}"
    if soort == "pad":
        return f"/Users/{r.choice(_VOORNAMEN).lower()}/project"
    if soort == "gitremote":
        return "git@github.com:voorbeeld-org/demo-repo.git"
    if soort == "cloudresource":
        return f"arn:aws:s3:::synthetic-bucket-{cijfers(6)}"
    return token  # 'overig' en onbekend: marker blijft staan


def bouw_synthetische_map(markers: list[dict], zaad: int) -> dict[str, str]:
    """Voor elke marker één deterministische fictieve waarde."""
    return {
        m["token"]: synthetische_waarde(m["type"], m["token"], zaad)
        for m in markers
    }


def vervang_markers(tekst: str, vervangingen: dict[str, str]) -> str:
    """Markers → fictieve waarden; onbekende markers blijven staan."""
    return re.sub(
        r"\b([A-Z]+)_\d+\b",
        lambda m: vervangingen.get(m.group(0), m.group(0)),
        tekst,
    )
