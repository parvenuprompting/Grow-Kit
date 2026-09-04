#!/usr/bin/env python3
"""GrowKit Vangnet — opvanglaag voor trainingsdata (ontwerp Vangnet 0.1, fase 1).

Vangt wat de loop toch al doet (review-aanroepen, stap-uitkomsten,
taak-gebeurtenissen) op in een lokaal SQLite-logboek per boom:
    <doel>/vangnet/vangnet.db

Drie harde regels uit het ontwerp:
1.  Nul handmatige stappen — alles wordt vastgelegd uit gedrag dat al bestaat.
2.  Fail-open — valt het vangnet om, dan gaat de loop gewoon door. Dit
    module gooit NOOIT een exception naar boven.
3.  Eén aansluitpunt — de bestaande kern roept alleen `vang(...)` aan;
    verder verandert er niets aan de loop.

Fase 1 van Vangnet: alleen vastleggen, geen oordeel. Labels (afgeleid of
hand) komen in een latere fase. Het logboek is append-only en zit in de
boom-map, zodat het meeverhuist met één map-kopie.
"""
import datetime
import hashlib
import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS vangsten (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    bron TEXT NOT NULL,          -- review | stap | taak | ratificatie
    taak TEXT,                   -- profiel/taak/stap-id, eerste-klas veld
    input_json TEXT,             -- geredigeerde payload
    output_json TEXT,            -- geredigeerd antwoord
    oordeel TEXT,                -- ruwe waarneming (geslaagd/gefaald/...), nog geen label
    input_hash TEXT,             -- sha256 van de ruwe input
    output_hash TEXT,            -- sha256 van het ruwe antwoord
    extra_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_vangsten_bron ON vangsten(bron, ts);
"""

# Sleutels die vóór opslag uit payloads worden gehaald (redactie vóór opslag).
_REDACTED = ("api_key", "apikey", "token", "secret", "authorization", "wachtwoord")


def _nu() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _redigeer(data) -> str:
    """JSON-dump met secrets vervangen door hun hash — nooit de waarde zelf."""
    def schoon(obj):
        if isinstance(obj, dict):
            return {k: (hashlib.sha256(str(v).encode()).hexdigest()[:16]
                        if k.lower() in _REDACTED else schoon(v))
                    for k, v in obj.items()}
        if isinstance(obj, list):
            return [schoon(x) for x in obj]
        return obj
    return json.dumps(schoon(data), ensure_ascii=False, default=str)


def _hash(tekst: str | None) -> str | None:
    if tekst is None:
        return None
    return hashlib.sha256(tekst.encode("utf-8")).hexdigest()


def vang(vangnet_pad: Path, bron: str, taak: str | None, input_data,
         output_data=None, oordeel: str | None = None, extra: dict | None = None) -> None:
    """Leg één waarneming vast. Fail-open: elke fout wordt stil genegeerd —
    het vangnet mag nooit de oorzaak zijn van een mislukte run."""
    try:
        vangnet_pad = Path(vangnet_pad)
        vangnet_pad.mkdir(parents=True, exist_ok=True)
        invoer = (_redigeer(input_data) if not isinstance(input_data, str)
                  else input_data)
        uitvoer = None
        if output_data is not None:
            uitvoer = (_redigeer(output_data)
                       if not isinstance(output_data, str) else output_data)
        con = sqlite3.connect(vangnet_pad / "vangnet.db", timeout=5)
        try:
            con.executescript(SCHEMA)
            con.execute(
                "INSERT INTO vangsten (ts, bron, taak, input_json, output_json, oordeel,"
                " input_hash, output_hash, extra_json) VALUES (?,?,?,?,?,?,?,?,?)",
                (_nu(), bron, taak, invoer, uitvoer, oordeel,
                 _hash(invoer), _hash(uitvoer),
                 json.dumps(extra, ensure_ascii=False) if extra else None))
            con.commit()
        finally:
            con.close()
    except Exception:
        pass  # fail-open: het vangnet zwijgt, de loop gaat door


def vang_review(vangnet_pad: Path, rol: str, stap: dict, uitvoer: str, antwoord: str) -> None:
    """Opvangpunt voor review-aanroepen (§9): de aanroep én het oordeel."""
    vang(vangnet_pad, "review", stap.get("id"),
         {"rol": rol, "stap": stap, "instructie": uitvoer},
         {"antwoord": antwoord}, oordeel=antwoord if antwoord else None)


def vang_stap(vangnet_pad: Path, stap_id: str, status: str, bewijstekst: str) -> None:
    """Opvangpunt voor stap-uitkomsten: gratis signaal (test_uitkomst)."""
    vang(vangnet_pad, "stap", stap_id, None, {"bewijs": bewijstekst}, oordeel=status)


def tel(vangnet_pad: Path, bron: str | None = None) -> int:
    """Aantal vangsten; used by tests en later het dashboard."""
    try:
        con = sqlite3.connect(Path(vangnet_pad) / "vangnet.db", timeout=5)
        try:
            rij = con.execute(
                "SELECT COUNT(*) FROM vangsten" + (" WHERE bron=?" if bron else ""),
                (bron,) if bron else ()).fetchone()
            return rij[0]
        finally:
            con.close()
    except Exception:
        return 0
