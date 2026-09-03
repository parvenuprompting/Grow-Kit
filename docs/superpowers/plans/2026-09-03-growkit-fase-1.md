# GrowKit Fase 1 — Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fase 1 van GrowKit bouwen: een werkend tweede-brein-stappenplan (generiek, met sjablonen en machine-bewijs) dat via een bestaande agent kan worden uitgevoerd, plus SEED.md, het kiemkeuze-mechanisme en de groeilaag.

**Architecture:** GrowKit is een repo met een geboortebrief (SEED.md) die de agent als eerste leest, een opstartscript (seed.py) dat de kiemkeuze afhandelt en per fase content injecteert, profielen als JSON-stappenplannen met gecodeerde bewijsvoorwaarden, sjabloonbestanden (geen heredocs) voor alle te schrijven bestanden, en een groeilaag (groei/) die na de installatie blijft bestaan. Machine-bewijs: seed.py voert alle checks zelf uit; de agent claimt nooit zelf succes. De mens wordt alleen geroepen bij echte mens-momenten.

**Tech Stack:** Python 3.11+ (stdlib only — geen pip-dependencies in fase 1), JSON, Markdown, unittest (stdlib), git.

**Spec:** `docs/superpowers/specs/2026-09-03-growkit-design.md` (v10) — het plan redeneert vanuit deze spec; executors lezen beide.

## Global Constraints

- **Taal:** alle inhoud (SEED.md, profielen, sjablonen, logboek, output) in het Nederlands.
- **Spelling:** productnaam GrowKit; repo-/mapnamen lowercase `growkit/`.
- **Geen dependencies:** uitsluitend Python-stdlib; geen pip-install nodig om te draaien.
- **Bewijs is gecodeerd:** geen vrije-tekstvoorwaarden; de vijf types uit spec §3 (shell_check, http_check, file_exists, json_valid, file_equals) met vaste velden.
- **Sjablonen, geen heredocs:** alle te schrijven bestanden komen uit `profielen/<profiel>/sjablonen/`.
- **Grenzen:** nooit wegschrijven naar Tiëndo's eigen Agent-Brain/VPS/setup; GrowKit staat daar volledig los van. Harnas-onderdelen bouwen we hier NIET (fase 4, na bewijs).
- **Faalcontract:** per stap maximaal één alternatief commando; faalt dat ook, dan `roep_mens`. Geen verdere retries.
- **Idempotentie:** elke stap zet `idempotent` expliciet (true/false); geen impliciete aanname.
- **Commits:** na elke afgeronde taak committen met duidelijke Nederlandse boodschap.
- **De agent voert nooit stappen uit zonder geldig bewijs** — dat is het hele punt van het product.

---

## File Structure (wat we gaan bouwen)

```
growkit/
├── SEED.md                                  ← geboortebrief (task 1)
├── seed.py                                  ← opstartscript: kiemkeuze, stappen-motor, bewijscontroles (tasks 2-5)
├── profielen/
│   ├── INDEX.md                             ← kiemkeuze-catalogus (task 6)
│   ├── tweede-brein/
│   │   ├── profiel.json                    ← stappenplan + mappen-definitie (task 7)
│   │   └── sjablonen/
│   │       ├── INDEX.md                     ← brein-index (task 7)
│   │       ├── AGENT-ROL.md                 ← rol van de agent in het brein (task 7)
│   │       ├── REGELS.md                    ← inbox-curatiewerk (task 7)
│   │       └── geboortebewijs.json.template ← per-boom identiteit (task 7)
│   ├── autonome-fabriek/                    ← placeholder profiel.json met status "in-ontwikkeling" (task 8)
│   └── dev-werkplaats/                      ← placeholder profiel.json met status "in-ontwikkeling" (task 8)
├── groei/                                    ← groeilaag: NIET in git (per-installatie)
│   ├── SETUP.md                             ← instructie groeilaag-initialisatie (task 9)
│   ├── logboek.json                         ← append-only, per installatie aangemaakt door seed.py
│   └── takenlijst.md                        ← door de agent onderhouden, per installatie
└── tests/
    ├── test_bewijs.py                       ← unit-tests voor de vijf bewijs-controles (task 3)
    ├── test_motor.py                        ← unit-tests voor de stappen-motor (task 4)
    └── test_profiel.py                      ← unit-tests voor profiel-validering (task 7)
```

**Let op:** `groei/` bestaat in de repo alleen als instructie (`SETUP.md`); de daadwerkelijke groeilaag wordt per installatie door seed.py aangemaakt in de doelmap. Daarom komt `.gitignore` erbij (task 2) met daarin `groei/logboek.json` en `groei/takenlijst.md` — instructiebestanden blijven wel gevolgd.

---

### Task 1: SEED.md — de geboortebrief

**Files:**
- Create: `SEED.md`

**Interfaces:**
- Produces: het eerste document dat elke agent leest; verwijst naar `profielen/INDEX.md` (fase 1) en `groei/SETUP.md` (fase 3). seed.py (task 2) leest SEED.md niet zelf, maar de agent wel — SEED.md is het ingangspunt voor de geleende agent.

- [ ] **Step 1: Schrijf SEED.md exact zoals hieronder** (spec §6 skeleton, uitgebreid met de faal- en leesregels die we in de spec hebben vastgelegd)

```markdown
# Geboortebrief

Jij bent vanaf nu de tuinier van dit zaadje. Je rol: dit stappenplan uitvoeren,
bewijs verzamelen, en nooit claimen dat iets gelukt is zonder dat bewijs.

## Regels

1. Lees alleen het bestand dat de leesroute op dit moment aanwijst.
2. Voer een stap pas uit nadat seed.py de profiel-JSON heeft vrijgegeven.
3. Bij falen van een stap: probeer precies één keer het alternatief_commando.
   Faalt dat ook, roep dan de mens. Geen verdere pogingen.
4. Log elke stap in groei/logboek.json vóór je verdergaat — seed.py doet dit
   automatisch; controleer na elke stap dat de entry er staat.
5. Bewijs komt van seed.py (machine-controle), nooit van jouw eigen
   interpretatie van terminal-output.
6. Secrets horen nooit in de chat; auth en API-sleutels worden op de
   doelmachine zelf ingevoerd.

## Leesroute

- Fase 0 (nu): dit bestand
- Fase 1: profielen/INDEX.md (kiemkeuze — welke boom?)
- Fase 2: seed.py geeft per stap de juiste profiel-JSON vrij
- Fase 3: groei/SETUP.md (initialiseren van de groeilaag)

Lees niets buiten deze route tenzij een stap dat expliciet vraagt.
```

- [ ] **Step 2: Controleer dat het bestand bestaat en niet leeg is**

Run: `test -s SEED.md && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add SEED.md
git commit -m "feat: geboortebrief SEED.md — regels en leesroute"
```

---

### Task 2: seed.py skelet — kiemkeuze en CLI

**Files:**
- Create: `seed.py`
- Create: `.gitignore`

**Interfaces:**
- Produces:
  - `main(argv) -> int` — CLI-ingang; `--profiel <naam>` kiest zonder dialoog, `--doel <pad>` zet de doelmap, `--slijp` opent de interactieve slijper (nog niet in fase 1: alleen stub die netjes afsluit met een duidelijke melding), default start de interactieve kiemkeuze.
  - `kiemkeuze() -> dict | None` — retourneert `{"profiel": str, "doel": str}` of None bij afbreken.
  - Werkt op Python 3.11+, stdlib only.

- [ ] **Step 1: Schrijf seed.py** — het volledige skelet met: argument-parsing, welkomsttekst (Nederlands), en een kiemkeuze-dialoog die de beschikbare profielen leest uit `profielen/*/profiel.json` (status "in-ontwikkeling" wordt getoond maar geweigerd met duidelijke melding). De Prompt-slijper zit er als nette stub in: `--slijp` meldt dat de slijper in fase 3 komt en sluit af met exit-code 0 — geen stub-beloftes, geen TODO's in code.

```python
#!/usr/bin/env python3
"""GrowKit seed.py — het plant-mechanisme.

Gebruik:
    python3 seed.py                          # interactieve kiemkeuze
    python3 seed.py --profiel tweede-brein --doel ~/mijn-brein
    python3 seed.py --slijp                  # Prompt-slijper (fase 3)
"""
import argparse
import json
import sys
from pathlib import Path

PROFILES_DIR = Path(__file__).parent / "profielen"
VERSIE = "0.1.0"


def laad_profielen() -> list[dict]:
    """Lees alle profiel.json-bestanden uit profielen/."""
    profielen = []
    if not PROFILES_DIR.exists():
        return profielen
    for pad in sorted(PROFILES_DIR.glob("*/profiel.json")):
        try:
            with open(pad, encoding="utf-8") as f:
                profielen.append(json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ! Ongeldig profielbestand {pad}: {e}")
    return profielen


def kiemkeuze() -> dict | None:
    """Interactieve kiemkeuze: welke boom, welke plek."""
    print()
    print("  Wat wil je laten groeien?")
    print()
    profielen = laad_profielen()
    if not profielen:
        print("  Geen profielen gevonden in profielen/. Roep de mens.")
        return None
    for i, p in enumerate(profielen, start=1):
        status = p.get("status", "?")
        print(f"  {i}. {p['profiel']} — {p.get('beschrijving', '')}"
              + ("  (in ontwikkeling)" if status == "in-ontwikkeling" else ""))
    print()
    keuze = input("  Kies een nummer (of 'q' om te stoppen): ").strip()
    if keuze.lower() == "q":
        return None
    try:
        gekozen = profielen[int(keuze) - 1]
    except (ValueError, IndexError):
        print("  Ongeldige keuze. Dit is nog geen opdracht — dit is ruis.")
        return None
    if gekozen.get("status") == "in-ontwikkeling":
        print(f"  Profiel '{gekozen['profiel']}' is nog in ontwikkeling; "
              "de agent stelt onderweg vragen. Voor nu: kies een bewezen profiel.")
        return None
    doel = input("  Waar moet het groeien? (map, bijv. ~/mijn-brein): ").strip()
    if not doel:
        print("  Geen doel = geen opdracht. Noem een map, dan plant ik.")
        return None
    return {"profiel": gekozen["profiel"], "doel": doel}


def slijper_stub() -> int:
    """Prompt-slijper komt in fase 3; nu een nette stub."""
    print("  De Prompt-slijper komt in fase 3. Voor nu: kies rechtstreeks een profiel.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seed.py", description="GrowKit — plant een boom.")
    parser.add_argument("--profiel", help="profielnaam, bijv. tweede-brein")
    parser.add_argument("--doel", help="doelmap voor de plant")
    parser.add_argument("--slijp", action="store_true", help="open de Prompt-slijper (fase 3)")
    args = parser.parse_args(argv)

    print()
    print("  ────────────────────────────────────────")
    print("   GrowKit — het zaadje dat vanzelf groeit")
    print(f"   versie {VERSIE}")
    print("  ────────────────────────────────────────")

    if args.slijp:
        return slijper_stub()

    if args.profiel and args.doel:
        keuze = {"profiel": args.profiel, "doel": args.doel}
    else:
        keuze = kiemkeuze()
        if keuze is None:
            print("  Geen opdracht — geen actie. Tot ziens.")
            return 1

    # Fase 2-motor en groeilaag komen in de volgende taken.
    print(f"  Gepland: profiel '{keuze['profiel']}' in '{keuze['doel']}'.")
    print("  (De stappen-motor wordt in de volgende taak aangesloten.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Schrijf .gitignore**

```gitignore
# Groeilaag is per-installatie, niet per-repo
groei/logboek.json
groei/takenlijst.md
__pycache__/
*.pyc
```

- [ ] **Step 3: Run seed.py --help en de interactieve modus (q om af te breken)**

Run: `python3 seed.py --help && echo q | python3 seed.py`
Expected: help-tekst; daarna welkomstscherm, kiemkeuze; q breekt af met "Geen opdracht — geen actie" en exit-code 1.

- [ ] **Step 4: Commit**

```bash
git add seed.py .gitignore
git commit -m "feat: seed.py skelet — kiemkeuze, CLI, slijper-stub"
```

---

### Task 3: De vijf bewijs-controles

**Files:**
- Create: `growkit_bewijs.py` (naast seed.py — bewijslogic gescheiden, één verantwoordelijkheid per bestand)
- Test: `tests/test_bewijs.py`

**Interfaces:**
- Produces: `controleer(bewijs: dict, doel: Path) -> tuple[bool, str]` — voert één bewijsdict uit, retourneert (geslaagd, bewijstekst). Het dict heeft altijd `"type"` plus type-specifieke gecodeerde velden (spec §3):
  - `shell_check`: `commando` (str, verplicht), `verwacht_substr` (str, verplicht)
  - `http_check`: `url` (str, verplicht), `verwacht_status` (int, verplicht)
  - `file_exists`: `pad` (str, verplicht), `bevat` (str, optioneel)
  - `json_valid`: `pad` (str, verplicht), `top_level` ("array"|"object", optioneel), `exacte_lengte` (int, optioneel), `verplicht_veld` (str, optioneel)
  - `file_equals`: `sjabloon` (str — pad binnen profiel-sjablonenmap), `pad` (str — doelbestand)
- Consumes: niets buiten stdlib (urllib.request voor http_check).

- [ ] **Step 1: Schrijf de falende tests** (unittest, stdlib)

```python
import json
import tempfile
import unittest
from pathlib import Path

from growkit_bewijs import controleer


class TestShellCheck(unittest.TestCase):
    def test_geslaagd(self):
        ok, tekst = controleer({"type": "shell_check", "commando": "echo hallo", "verwacht_substr": "hallo"}, Path("."))
        self.assertTrue(ok)

    def test_gefaald(self):
        ok, _ = controleer({"type": "shell_check", "commando": "echo hallo", "verwacht_substr": "tot ziens"}, Path("."))
        self.assertFalse(ok)


class TestFileExists(unittest.TestCase):
    def test_bestaat(self):
        with tempfile.TemporaryDirectory() as d:
            doel = Path(d) / "a.txt"
            doel.write_text("inhoud met VOORSTEL erin")
            ok, _ = controleer({"type": "file_exists", "pad": "a.txt", "bevat": "VOORSTEL"}, Path(d))
            self.assertTrue(ok)

    def test_bestaat_niet(self):
        with tempfile.TemporaryDirectory() as d:
            ok, _ = controleer({"type": "file_exists", "pad": "a.txt"}, Path(d))
            self.assertFalse(ok)


class TestJsonValid(unittest.TestCase):
    def test_lege_array(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "log.json").write_text("[]", encoding="utf-8")
            ok, _ = controleer({"type": "json_valid", "pad": "log.json", "top_level": "array", "exacte_lengte": 0}, Path(d))
            self.assertTrue(ok)

    def test_verplicht_veld(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "log.json").write_text('[{"actie": "geplant"}]', encoding="utf-8")
            ok, _ = controleer({"type": "json_valid", "pad": "log.json", "top_level": "array", "verplicht_veld": "actie"}, Path(d))
            self.assertTrue(ok)

    def test_onvalid(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "log.json").write_text("geen json", encoding="utf-8")
            ok, _ = controleer({"type": "json_valid", "pad": "log.json"}, Path(d))
            self.assertFalse(ok)


class TestFileEquals(unittest.TestCase):
    def test_identiek(self):
        with tempfile.TemporaryDirectory() as d:
            sjablonen = Path(d) / "sjablonen"
            sjablonen.mkdir()
            (sjablonen / "x.md").write_text("# Index\n", encoding="utf-8")
            (Path(d) / "x.md").write_text("# Index\n", encoding="utf-8")
            ok, _ = controleer({"type": "file_equals", "sjabloon": "x.md", "pad": "x.md"}, Path(d), sjablonen_map=sjablonen)
            self.assertTrue(ok)

    def test_afwijkend(self):
        with tempfile.TemporaryDirectory() as d:
            sjablonen = Path(d) / "sjablonen"
            sjablonen.mkdir()
            (sjablonen / "x.md").write_text("# Index\n", encoding="utf-8")
            (Path(d) / "x.md").write_text("# Iets anders\n", encoding="utf-8")
            ok, _ = controleer({"type": "file_equals", "sjabloon": "x.md", "pad": "x.md"}, Path(d), sjablonen_map=sjablonen)
            self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run de tests — ze moeten falen** (module bestaat nog niet)

Run: `python3 -m unittest tests.test_bewijs -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'growkit_bewijs'`

- [ ] **Step 3: Schrijf growkit_bewijs.py**

```python
"""GrowKit bewijs-controles — machine-toetsbaar, nooit zelf-gerapporteerd.

Elke functie voert precies één gecodeerde check uit. Geen enkele check
vertrouwt op interpretatie van agent-output.
"""
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

BEWIJS_TYPES = {"shell_check", "http_check", "file_exists", "json_valid", "file_equals"}


def _shell_check(bewijs: dict, doel: Path, **_) -> tuple[bool, str]:
    resultaat = subprocess.run(bewijs["commando"], shell=True, cwd=doel,
                               capture_output=True, text=True, timeout=60)
    tekst = resultaat.stdout + resultaat.stderr
    geslaagd = bewijs["verwacht_substr"] in tekst
    return geslaagd, f"shell_check: zocht '{bewijs['verwacht_substr']}', kreeg: {tekst.strip()[:200]!r}"


def _http_check(bewijs: dict, doel: Path, **_) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(bewijs["url"], timeout=10) as r:
            status = r.status
    except Exception as e:  # ook HTTP-fouten (404 e.d.) vallen hieronder
        return False, f"http_check: {bewijs['url']} faalde: {e}"
    return status == bewijs["verwacht_status"], f"http_check: {bewijs['url']} -> {status}"


def _file_exists(bewijs: dict, doel: Path, **_) -> tuple[bool, str]:
    bestand = doel / bewijs["pad"]
    if not bestand.exists():
        return False, f"file_exists: {bewijs['pad']} bestaat niet"
    if "bevat" in bewijs and bewijs["bevat"] not in bestand.read_text(encoding="utf-8"):
        return False, f"file_exists: {bewijs['pad']} bevat niet {bewijs['bevat']!r}"
    return True, f"file_exists: {bewijs['pad']} OK"


def _json_valid(bewijs: dict, doel: Path, **_) -> tuple[bool, str]:
    try:
        with open(doel / bewijs["pad"], encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return False, f"json_valid: {bewijs['pad']} is geen valide JSON: {e}"
    if "top_level" in bewijs:
        verwacht = list if bewijs["top_level"] == "array" else dict
        if not isinstance(data, verwacht):
            return False, f"json_valid: top-level is geen {bewijs['top_level']}"
    if "exacte_lengte" in bewijs and len(data) != bewijs["exacte_lengte"]:
        return False, f"json_valid: lengte {len(data)} != {bewijs['exacte_lengte']}"
    if "verplicht_veld" in bewijs:
        items = data if isinstance(data, list) else [data]
        if not all(bewijs["verplicht_veld"] in item for item in items):
            return False, f"json_valid: veld {bewijs['verplicht_veld']!r} ontbreekt"
    return True, f"json_valid: {bewijs['pad']} OK"


def _file_equals(bewijs: dict, doel: Path, sjablonen_map: Path | None = None, **_) -> tuple[bool, str]:
    if sjablonen_map is None:
        return False, "file_equals: geen sjablonenmap meegegeven"
    sjabloon = sjablonen_map / bewijs["sjabloon"]
    bestand = doel / bewijs["pad"]
    if not sjabloon.exists() or not bestand.exists():
        return False, f"file_equals: {bewijs['sjabloon']} of {bewijs['pad']} bestaat niet"
    h1 = hashlib.sha256(sjabloon.read_bytes()).hexdigest()
    h2 = hashlib.sha256(bestand.read_bytes()).hexdigest()
    return h1 == h2, f"file_equals: {bewijs['pad']} {'=' if h1 == h2 else '!='} sjabloon"


_CONTROLES = {
    "shell_check": _shell_check,
    "http_check": _http_check,
    "file_exists": _file_exists,
    "json_valid": _json_valid,
    "file_equals": _file_equals,
}


def controleer(bewijs: dict, doel: Path, sjablonen_map: Path | None = None) -> tuple[bool, str]:
    """Voer één gecodeerde bewijscheck uit. Retourneert (geslaagd, bewijstekst)."""
    soort = bewijs.get("type")
    if soort not in BEWIJS_TYPES:
        return False, f"onbekend bewijstype: {soort!r} (geldige types: {sorted(BEWIJS_TYPES)})"
    return _CONTROLES[soort](bewijs, doel, sjablonen_map=sjablonen_map)
```

- [ ] **Step 4: Run de tests — ze moeten slagen**

Run: `python3 -m unittest tests.test_bewijs -v`
Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add growkit_bewijs.py tests/test_bewijs.py
git commit -m "feat: vijf machine-bewijscontroles met gecodeerde voorwaarden"
```

---

### Task 4: De stappen-motor

**Files:**
- Create: `growkit_motor.py`
- Test: `tests/test_motor.py`
- Modify: `seed.py` (main() koppelt de motor aan na de kiemkeuze)

**Interfaces:**
- Consumes: `controleer()` uit growkit_bewijs (task 3); profiel-JSON-structuur uit task 7.
- Produces:
  - `voer_uit(profiel: dict, doel: Path, logboek: Path, sjablonen_map: Path) -> bool` — draait het hele stappenplan; retourneert True alleen als élke stap bewezen is.
  - `voer_stap_uit(stap: dict, doel: Path, sjablonen_map: Path) -> tuple[bool, str]` — één stap: commando uitvoeren → bewijs controleren → bij falen precies één alternatief → anders False met reden "roep_mens".
  - Logboekformaat (append-only, per entry):

```json
{"stap": "stap-001", "status": "geslaagd|gefaald|wacht_op_mens", "bewijs": "<bewijstekst>", "tijdstip": "2026-09-03T16:00:00"}
```

- [ ] **Step 1: Schrijf de falende tests**

```python
import json
import tempfile
import unittest
from pathlib import Path

from growkit_motor import voer_stap_uit, voer_uit


def maak_profiel():
    return {
        "profiel": "test",
        "stappen": [
            {
                "id": "stap-001",
                "commando": "echo OK",
                "verwacht": "OK verschijnt",
                "bewijs": {"type": "shell_check", "commando": "echo OK", "verwacht_substr": "OK"},
                "bij_falen": {"alternatief_commando": None, "anders": "roep_mens"},
                "idempotent": True,
            },
            {
                "id": "stap-002",
                "commando": "false",
                "verwacht": "onmogelijk",
                "bewijs": {"type": "shell_check", "commando": "false", "verwacht_substr": "nooit"},
                "bij_falen": {"alternatief_commando": "echo ook-niet", "anders": "roep_mens"},
                "idempotent": False,
            },
        ],
    }


class TestStap(unittest.TestCase):
    def test_geslaagde_stap(self):
        with tempfile.TemporaryDirectory() as d:
            ok, _ = voer_stap_uit(maak_profiel()["stappen"][0], Path(d), None)
            self.assertTrue(ok)

    def test_gefaalde_stap_met_alternatief_ook_faalt(self):
        with tempfile.TemporaryDirectory() as d:
            ok, _ = voer_stap_uit(maak_profiel()["stappen"][1], Path(d), None)
            self.assertFalse(ok)


class TestVolledigeRun(unittest.TestCase):
    def test_run_stopt_bij_falen_en_logt(self):
        with tempfile.TemporaryDirectory() as d:
            doel = Path(d) / "plant"
            doel.mkdir()
            logboek = Path(d) / "logboek.json"
            logboek.write_text("[]", encoding="utf-8")
            ok = voer_uit(maak_profiel(), doel, logboek, None)
            self.assertFalse(ok)  # stap-002 faalt per opzet
            entries = json.loads(logboek.read_text(encoding="utf-8"))
            self.assertEqual(entries[0]["stap"], "stap-001")
            self.assertEqual(entries[0]["status"], "geslaagd")
            self.assertEqual(entries[1]["status"], "gefaald")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run de tests — ze moeten falen**

Run: `python3 -m unittest tests.test_motor -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'growkit_motor'`

- [ ] **Step 3: Schrijf growkit_motor.py**

```python
"""GrowKit stappen-motor — voert uit, seed.py-gedrag: bewijs of mens.

Faalcontract: één commando, bij falen precies één alternatief, dan de mens.
Elke stap wordt append-only gelogd vóórdat de volgende begint.
"""
import datetime
import json
import subprocess
from pathlib import Path

from growkit_bewijs import controleer


def _nu() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def voer_stap_uit(stap: dict, doel: Path, sjablonen_map: Path | None) -> tuple[bool, str]:
    """Eén stap: commando → bewijs → (alternatief) → mens."""
    resultaat = subprocess.run(stap["commando"], shell=True, cwd=doel,
                               capture_output=True, text=True, timeout=300)
    ok, bewijstekst = controleer(stap["bewijs"], doel, sjablonen_map=sjablonen_map)
    if not ok and stap.get("bij_falen", {}).get("alternatief_commando"):
        subprocess.run(stap["bij_falen"]["alternatief_commando"], shell=True, cwd=doel,
                        capture_output=True, text=True, timeout=300)
        ok, bewijstekst = controleer(stap["bewijs"], doel, sjablonen_map=sjablonen_map)
        if not ok:
            bewijstekst += " — ook na alternatief_commando"
    return ok, bewijstekst


def _log(logboek: Path, stap_id: str, status: str, bewijstekst: str) -> None:
    entries = json.loads(logboek.read_text(encoding="utf-8")) if logboek.exists() else []
    entries.append({"stap": stap_id, "status": status, "bewijs": bewijstekst, "tijdstip": _nu()})
    logboek.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def voer_uit(profiel: dict, doel: Path, logboek: Path, sjablonen_map: Path | None) -> bool:
    """Volledige run. Mens-stappen pauzeren (wacht_op_mens), bewijs-stappen bewijzen."""
    alles_geslaagd = True
    for stap in profiel["stappen"]:
        if stap.get("mens_nodig"):
            _log(logboek, stap["id"], "wacht_op_mens", stap["mens_nodig"].get("instructie", ""))
            print(f"  [mens-moment] {stap['id']}: {stap['mens_nodig'].get('instructie', '')}")
            continue  # fase 1: mens-momenten tonen we, auto-hervatten komt later
        ok, bewijstekst = voer_stap_uit(stap, doel, sjablonen_map)
        _log(logboek, stap["id"], "geslaagd" if ok else "gefaald", bewijstekst)
        print(f"  [{'OK' if ok else 'X'}] {stap['id']} — {bewijstekst}")
        if not ok:
            print(f"  Stap {stap['id']} faalde na alternatief. Roep de mens.")
            return False
    return alles_geslaagd
```

- [ ] **Step 4: Koppel de motor aan seed.py** — vervang in `main()` de regel `# Fase 2-motor en groeilaag komen in de volgende taken.` + print-regels door:

```python
    import growkit_motor
    doel = Path(keuze["doel"]).expanduser().resolve()
    doel.mkdir(parents=True, exist_ok=True)
    logboek = doel / "logboek.json"
    if not logboek.exists():
        logboek.write_text("[]", encoding="utf-8")
    profiel_pad = PROFILES_DIR / keuze["profiel"] / "profiel.json"
    with open(profiel_pad, encoding="utf-8") as f:
        profiel = json.load(f)
    sjablonen = PROFILES_DIR / keuze["profiel"] / "sjablonen"
    geslaagd = growkit_motor.voer_uit(profiel, doel, logboek, sjablonen)
    return 0 if geslaagd else 2
```

- [ ] **Step 5: Run de motor-tests — ze moeten slagen**

Run: `python3 -m unittest tests.test_motor -v`
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add growkit_motor.py tests/test_motor.py seed.py
git commit -m "feat: stappen-motor — bewijs of mens, append-only logboek, faalcontract"
```

---

### Task 5: E2E-rooktest — plant een miniem testprofiel

**Files:**
- Create: `tests/e2e_plant.sh`
- Test profiel: hergebruikt geen productprofiel — een miniem `profielen/test-mini/profiel.json` aanmaken voor de test, en na de test weer verwijderen is valkuil; beter: de test draait seed.py met `--profiel tweede-brein` zodra task 7 klaar is. Deze taak maakt de runner die dat bewijst, met als minimale versie een handmatige rooktest.

**Interfaces:**
- Produces: `tests/e2e_plant.sh` — roept `python3 seed.py --profiel tweede-brein --doel <tmp>` aan, controleert dat de vijf kernmappen bestaan, INDEX.md bestaat, logboek.json valide is en alle entries "geslaagd" zijn, exit 0 anders exit 1.

- [ ] **Step 1: Schrijf tests/e2e_plant.sh**

```bash
#!/usr/bin/env bash
# E2E: plant het tweede-brein-profiel in een schone tmp-map en bewijs het resultaat.
set -euo pipefail
cd "$(dirname "$0")/.."

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 seed.py --profiel tweede-brein --doel "$TMP/plant"

# Bewijs 1: vijf kernmappen
for map in identiteit kennis projecten inbox logboek; do
  test -d "$TMP/plant/$map" || { echo "FAIL: map $map ontbreekt"; exit 1; }
done

# Bewijs 2: INDEX.md in de root van de plant
test -s "$TMP/plant/INDEX.md" || { echo "FAIL: INDEX.md ontbreekt"; exit 1; }

# Bewijs 3: logboek is valide JSON en alles is geslaagd of wacht_op_mens
python3 - "$TMP/plant/logboek.json" <<'PY'
import json, sys
entries = json.load(open(sys.argv[1], encoding="utf-8"))
assert entries, "logboek is leeg"
assert all(e["status"] in ("geslaagd", "wacht_op_mens") for e in entries), \
    f"logboek bevat niet-geslaagde stappen: {[e for e in entries if e['status'] not in ('geslaagd', 'wacht_op_mens')]}"
print("E2E OK: alle stappen geslaagd of wacht_op_mens")
PY
```

- [ ] **Step 2: Maak uitvoerbaar en run (na task 7)** — draait pas zodra het echte profiel bestaat; tot die tijd faalt hij netjes met "profiel niet gevonden".

Run: `chmod +x tests/e2e_plant.sh && ./tests/e2e_plant.sh`
Expected (na task 7): `E2E OK: alle stappen geslaagd of wacht_op_mens`

- [ ] **Step 3: Commit**

```bash
git add tests/e2e_plant.sh
git commit -m "test: E2E-rooktest — plant tweede-brein in schone map en bewijst alles"
```

---

### Task 6: profielen/INDEX.md — de kiemkeuze-catalogus

**Files:**
- Create: `profielen/INDEX.md`

**Interfaces:**
- Consumes: SEED.md leesroute (fase 1) verwijst hierheen.
- Produces: de catalogus die de mens én de agent lezen bij de kiemkeuze; per profiel: naam, een-zins-beschrijving, status.

- [ ] **Step 1: Schrijf profielen/INDEX.md**

```markdown
# Kiemkeuze — welke boom wil je laten groeien?

Elke boom hieronder is een stappenplan: een vast pad van commando's met
machine-bewijs per stap. Jij kiest en bevestigt; de agent plant en bewijst.

| Boom | Wat het is | Status |
|---|---|---|
| **tweede-brein** | Een gecontroleerd geheugen naast je AI-agent: de agent leest en stelt voor, jij keurt goed. Vijf kernmappen, append-only logboek, inbox met VOORSTEL-status. | bewezen-vorm |
| **autonome-fabriek** | Een VPS-dienst die 's nachts zelfstandig bouwt en rapporteert. | in-ontwikkeling |
| **dev-werkplaats** | Een codeeromgeving met je tools, regels en configuraties. | in-ontwikkeling |

## Vrij beschrijven

Wil je een andere boom? Beschrijf dan in eigen woorden: (1) wat het einddoel is,
(2) waar het moet groeien (deze machine of een VPS), en (3) wanneer het geslaagd
is. De Prompt-slijper schuurt je beschrijving tot een concept-profiel — maar
let op: een vrij beschreven boom is nog niet bewezen; de agent stelt onderweg
vragen. (Prompt-slijper: fase 3.)
```

- [ ] **Step 2: Commit**

```bash
git add profielen/INDEX.md
git commit -m "feat: kiemkeuze-catalogus INDEX.md"
```

---

### Task 7: Het echte tweede-brein-profiel + sjablonen

**Files:**
- Create: `profielen/tweede-brein/profiel.json`
- Create: `profielen/tweede-brein/sjablonen/INDEX.md`
- Create: `profielen/tweede-brein/sjablonen/AGENT-ROL.md`
- Create: `profielen/tweede-brein/sjablonen/REGELS.md`
- Create: `profielen/tweede-brein/sjablonen/geboortebewijs.json.template`
- Test: `tests/test_profiel.py`

**Interfaces:**
- Consumes: `controleer()` (task 3), `voer_uit()` (task 4), profiel-structuur zoals seed.py die laadt.
- Produces: het eerste échte, bewezen profiel — géén voorbeelden meer. Sjablonen-map wordt door seed.py als `sjablonen_map` meegegeven aan de motor.

- [ ] **Step 1: Schrijf de falende profield-test**

```python
import json
import unittest
from pathlib import Path

PROFIEL = Path(__file__).parent.parent / "profielen" / "tweede-brein" / "profiel.json"
SJABLONEN = PROFIEL.parent / "sjablonen"


class TestTweedeBreinProfiel(unittest.TestCase):
    def setUp(self):
        with open(PROFIEL, encoding="utf-8") as f:
            self.profiel = json.load(f)

    def test_basale_structuur(self):
        self.assertEqual(self.profiel["profiel"], "tweede-brein")
        self.assertEqual(self.profiel["status"], "bewezen-vorm")
        self.assertIn("stappen", self.profiel)

    def test_elke_stap_heeft_verplichte_velden(self):
        for stap in self.profiel["stappen"]:
            for veld in ("id", "commando", "bewijs", "bij_falen", "idempotent"):
                self.assertIn(veld, stap, f"{stap.get('id', '?')} mist veld {veld}")
            self.assertIn(stap["bewijs"]["type"],
                          {"shell_check", "http_check", "file_exists", "json_valid", "file_equals", "mens_verificatie"})

    def test_sjablonen_bestaan(self):
        for bestand in ("INDEX.md", "AGENT-ROL.md", "REGELS.md", "geboortebewijs.json.template"):
            self.assertTrue((SJABLONEN / bestand).exists(), f"sjabloon {bestand} ontbreekt")

    def test_kernmappen_staan_in_profiel(self):
        for map_ in ("identiteit", "kennis", "projecten", "inbox", "logboek"):
            self.assertIn(map_, self.profiel["mappen"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run de test — moet falen** (profiel bestaat nog niet)

Run: `python3 -m unittest tests.test_profiel -v`
Expected: FAIL — FileNotFoundError

- [ ] **Step 3: Schrijf de vier sjablonen**

`profielen/tweede-brein/sjablonen/INDEX.md`:

```markdown
# INDEX — tweede brein

> Ingang van het brein. Lees dit bestand eerst.

## Kaart

| Map | Wat | Wie schrijft |
|---|---|---|
| `identiteit/` | wie dit brein is + de rol van de agent | mens |
| `kennis/` | vastgelegde, geverifieerde kennis | mens |
| `projecten/` | actieve en afgeronde projecten | mens |
| `inbox/` | agent-voorstellen (status VOORSTEL) | agent |
| `logboek/` | append-only log van alle gebeurtenissen | machine |

## Regel

De agent leest en stelt voor. Alleen de mens promoveert, overschrijft of
verwijdert. Niets wordt ooit stilletjes veranderd.
```

`profielen/tweede-brein/sjablonen/AGENT-ROL.md`:

```markdown
# Rol van de agent in dit brein

- Leest uit alle mappen om context op te bouwen.
- Schrijft voorstellen naar `inbox/`, altijd met status VOORSTEL.
- Past nooit rechtstreeks kennis, projecten of identiteit aan.
- Promotie van een voorstel gebeurt uitsluitend door de mens.
- Beweert nooit dat iets gelukt is zonder machine-bewijs.
```

`profielen/tweede-brein/sjablonen/REGELS.md`:

```markdown
# Regels voor de inbox

1. Elk agent-voorstel krijgt de status VOORSTEL bij aanmaak.
2. De mens beoordeelt: goedkeuren (promotie naar kennis/ of projecten/)
   of afwijzen.
3. Een afgewezen voorstel wordt gemarkeerd [AFGEWEZEN], nooit verwijderd.
4. De agent overschrijft nooit een bestaand voorstel; nieuwe inzichten
   zijn nieuwe bestanden.
```

`profielen/tweede-brein/sjablonen/geboortebewijs.json.template`:

```json
{
  "boom_id": "{{BOOM_ID}}",
  "profiel": "tweede-brein",
  "machine": "{{MACHINE}}",
  "locatie": "{{LOCATIE}}",
  "geplant_op": "{{TIJDSTIP}}"
}
```

- [ ] **Step 4: Schrijf profiel.json** — het échte stappenplan (deterministisch, alles via sjablonen):

```json
{
  "profiel": "tweede-brein",
  "status": "bewezen-vorm",
  "beschrijving": "Generiek tweede brein: een gecontroleerd geheugen naast een AI-agent. De agent leest en stelt voor, de mens keurt goed. Nooit overschrijven, alleen toevoegen.",
  "mappen": ["identiteit", "kennis", "projecten", "inbox", "logboek"],
  "stappen": [
    {
      "id": "stap-001",
      "commando": "mkdir -p identiteit kennis projecten inbox logboek",
      "verwacht": "de vijf kernmappen bestaan in de doelmap",
      "bewijs": {
        "type": "shell_check",
        "commando": "test -d identiteit && test -d kennis && test -d projecten && test -d inbox && test -d logboek && echo MAPPEN-OK",
        "verwacht_substr": "MAPPEN-OK"
      },
      "bij_falen": {"alternatief_commando": "mkdir -p ./identiteit ./kennis ./projecten ./inbox ./logboek", "anders": "roep_mens"},
      "idempotent": true
    },
    {
      "id": "stap-002",
      "commando": "cp profielen/tweede-brein/sjablonen/INDEX.md ./INDEX.md",
      "verwacht": "INDEX.md staat in de root van de plant en is identiek aan het sjabloon",
      "bewijs": {"type": "file_equals", "sjabloon": "INDEX.md", "pad": "INDEX.md"},
      "bij_falen": {"alternatief_commando": "cp profielen/tweede-brein/sjablonen/INDEX.md ./", "anders": "roep_mens"},
      "idempotent": true
    },
    {
      "id": "stap-003",
      "commando": "cp profielen/tweede-brein/sjablonen/AGENT-ROL.md ./identiteit/AGENT-ROL.md",
      "verwacht": "identiteit/AGENT-ROL.md bestaat en is identiek aan het sjabloon",
      "bewijs": {"type": "file_equals", "sjabloon": "AGENT-ROL.md", "pad": "identiteit/AGENT-ROL.md"},
      "bij_falen": {"alternatief_commando": null, "anders": "roep_mens"},
      "idempotent": true
    },
    {
      "id": "stap-004",
      "commando": "cp profielen/tweede-brein/sjablonen/REGELS.md ./inbox/REGELS.md",
      "verwacht": "inbox/REGELS.md bestaat en bevat de tekst VOORSTEL",
      "bewijs": {"type": "file_equals", "sjabloon": "REGELS.md", "pad": "inbox/REGELS.md"},
      "bij_falen": {"alternatief_commando": null, "anders": "roep_mens"},
      "idempotent": true
    },
    {
      "id": "stap-005",
      "commando": "printf '[]' > logboek/logboek.json",
      "verwacht": "logboek/logboek.json is valide JSON en een lege array",
      "bewijs": {"type": "json_valid", "pad": "logboek/logboek.json", "top_level": "array", "exacte_lengte": 0},
      "bij_falen": {"alternatief_commando": null, "anders": "roep_mens"},
      "idempotent": false
    },
    {
      "id": "stap-006",
      "commando": "touch kennis/.gitkeep projecten/.gitkeep identiteit/.gitkeep",
      "verwacht": "lege mappen blijven bestaansrecht hebben in git",
      "bewijs": {
        "type": "shell_check",
        "commando": "test -f kennis/.gitkeep && test -f projecten/.gitkeep && test -f identiteit/.gitkeep && echo GITKEEP-OK",
        "verwacht_substr": "GITKEEP-OK"
      },
      "bij_falen": {"alternatief_commando": null, "anders": "roep_mens"},
      "idempotent": true
    },
    {
      "id": "stap-007",
      "commando": "cp profielen/tweede-brein/sjablonen/geboortebewijs.json.template ./geboortebewijs.json",
      "verwacht": "geboortebewijs.json staat in de root van de plant (oerwoud-voorbereiding, spec §13)",
      "bewijs": {"type": "file_equals", "sjabloon": "geboortebewijs.json.template", "pad": "geboortebewijs.json"},
      "bij_falen": {"alternatief_commando": null, "anders": "roep_mens"},
      "idempotent": true
    },
    {
      "id": "stap-008",
      "commando": "Toon INDEX.md, identiteit/AGENT-ROL.md en inbox/REGELS.md aan de mens ter bevestiging dat de structuur klopt.",
      "verwacht": "de mens bevestigt dat het skelet klopt met de bedoeling",
      "bewijs": {"type": "mens_verificatie"},
      "mens_nodig": {
        "type": "bevestiging",
        "instructie": "Lees de drie getoonde bestanden in de doelmap en bevestig of wijs af. Geen secrets of sleutels nodig in deze stap."
      },
      "bij_falen": {"alternatief_commando": null, "anders": "roep_mens"},
      "idempotent": true,
      "review": "reviewer"
    }
  ]
}
```

- [ ] **Step 5: Run alle tests — moeten slagen**

Run: `python3 -m unittest discover tests -v`
Expected: alle tests PASS (bewijs, motor, profiel)

- [ ] **Step 6: Run de E2E-rooktest**

Run: `./tests/e2e_plant.sh`
Expected: `E2E OK: alle stappen geslaagd of wacht_op_mens`

- [ ] **Step 7: Commit**

```bash
git add profielen/tweede-brein/ tests/test_profiel.py
git commit -m "feat: eerste echte profiel — tweede-brein met sjablonen en machine-bewijs"
```

---

### Task 8: Placeholder-profielen (autonome-fabriek, dev-werkplaats)

**Files:**
- Create: `profielen/autonome-fabriek/profiel.json`
- Create: `profielen/dev-werkplaats/profiel.json`

**Interfaces:**
- Consumes: profiel-structuur zoals seed.py die laadt (status "in-ontwikkeling" → geweigerd met melding).
- Produces: zichtbare, geannuleerde placeholders zodat de kiemkeuze-catalogus klopt en de structuur klaar is voor uitbreiding.

- [ ] **Step 1: Schrijf beide placeholders** — identiek van vorm:

`profielen/autonome-fabriek/profiel.json`:

```json
{
  "profiel": "autonome-fabriek",
  "status": "in-ontwikkeling",
  "beschrijving": "Een VPS-dienst die 's nachts zelfstandig bouwt en rapporteert. Stappenplan volgt in een latere fase.",
  "mappen": [],
  "stappen": []
}
```

`profielen/dev-werkplaats/profiel.json`:

```json
{
  "profiel": "dev-werkplaats",
  "status": "in-ontwikkeling",
  "beschrijving": "Een codeeromgeving met je tools, regels en configuraties. Stappenplan volgt in een latere fase.",
  "mappen": [],
  "stappen": []
}
```

- [ ] **Step 2: Controleer dat seed.py ze weigert**

Run: `echo "2" | python3 seed.py`
Expected: bij keuze van een in-ontwikkeling-profiel de melding "is nog in ontwikkeling" en afsluiten zonder actie (exit-code 1).

- [ ] **Step 3: Commit**

```bash
git add profielen/autonome-fabriek/ profielen/dev-werkplaats/
git commit -m "feat: placeholder-profielen voor autonome-fabriek en dev-werkplaats"
```

---

### Task 9: groei/SETUP.md — de groeilaag-instructie

**Files:**
- Create: `groei/SETUP.md`

**Interfaces:**
- Consumes: SEED.md leesroute fase 3 verwijst hierheen.
- Produces: instructie voor de agent (en mens) hoe de groeilaag na de installatie werkt en wordt onderhouden.

- [ ] **Step 1: Schrijf groei/SETUP.md**

```markdown
# De groeilaag — leven na de installatie

De boom is geplant. Vanaf nu blijft deze map de levensonderhoudslaag van je
boom: alles wat er daarna gebeurt, wordt hier gelogd, voorgesteld en bijgehouden.

## Onderdelen

- `logboek/logboek.json` (in de plant) — append-only log van elke stap en
  gebeurtenis, inclusief het machine-geverifieerde bewijs. Bij een crash of
  nieuwe sessie leest de agent dit om te bepalen waar hij was.
- `takenlijst.md` (in de plant) — taken die de agent zelf oppakt en afdwingt
  mét bewijs, volgens hetzelfde stappen-schema als het profiel.
- `inbox/` (in de plant) — voorstellen van de agent (status VOORSTEL); jij
  curateert. Nooit overschrijven, alleen toevoegen; promotie doe jij.

## Regels voor de agent (ook ná de installatie)

1. Bij elke taak: check eerst het logboek (waar waren we?) en de inbox
   (welke voorstellen liggen er?).
2. Nieuwe inzichten worden VOORSTELLEN in inbox/, nooit directe wijzigingen.
3. Bewijs blijft verplicht: een taak is pas klaar als de check dat zegt.
4. Grote of langdurige taken: vat op (begrepen/afgesproken/bewezen/volgende)
   en vraag bevestiging vóór iets definitief wordt (spec §11.4).

## Voor de mens

- Je curateert de inbox op je eigen tempo; niets verandert zonder jou.
- Het geboortebewijs (geboortebewijs.json in de plant) registreert deze boom
  in het toekomstige oerwoud (spec §13): meerdere bomen, één brein.
```

- [ ] **Step 2: Commit**

```bash
git add groei/SETUP.md
git commit -m "feat: groeilaag-instructie SETUP.md — leven na de installatie"
```

---

## Zelf-review checklist (voor de executor)

1. **Spec-dekking:** elke sectie uit de spec die bij fase 1 hoort (SEED.md, kiemkeuze, stappen-schema, bewijs, sjablonen, groeilaag, geboortebewijs) heeft een taak. Fase 2+ onderdelen (slijper, formulier, mijlpaal, harnas, oerwoud-sync) zijn bewust NIET in dit plan — ze hebben hun eigen fase.
2. **Placeholders:** geen TBD/TODO in dit plan; slijper is een expliciete nette stub, niet een belofte.
3. **Types consistent:** `controleer(bewijs, doel, sjablonen_map)` in task 3 == usage in task 4; `voer_stap_uit(stap, doel, sjablonen_map)` == motor-test; `voer_uit(profiel, doel, logboek, sjablonen_map)` == seed.py-koppeling.
4. **Bekende valkuil, expliciet:** profiel.json gebruikt `cp` met pad `profielen/tweede-brein/sjablonen/...` als commando — dat werkt alleen als de cwd tijdens uitvoering de GrowKit-repo is en de doelmap via de motor als `doel` wordt meegegeven. De motor draait commando's met `cwd=doel`, dus `cp`-paden naar sjablonen moeten absolute paden zíjn of seed.py moet ze vervangen. **Oplossing, verplicht:** in seed.py vóór `voer_uit` het sjabloonpad absolutiseren en in het profiel een veld `sjablonen_pad: "{GROWKIT}/profielen/tweede-brein/sjablonen"` gebruiken dat seed.py vervangt door het echte absolute pad vóór uitvoering (eenvoudige string-substitutie `{GROWKIT}` → repo-root). Pas de cp-commando's in profiel.json aan naar `cp {GROWKIT}/profielen/tweede-brein/sjablonen/INDEX.md ./INDEX.md` enzovoort, en pas de e2e-check op file_equals dienovereenkomstig aan (file_equals werkt al met sjablonen_map, dus alleen de cp-commando's zijn betroffen).
```
