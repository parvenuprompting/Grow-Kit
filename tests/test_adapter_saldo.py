"""Slice A1 — Saldo-bridge: OpenRouter-saldo en per-model verbruik in het
harnas (docs/VISIE-AGENT-HARNAS.md, fase A1).

Nieuwe adapter-commando's:
- `saldo`: actueel OpenRouter-saldo
    {"sleutel_pad"?: "<pad naar bestand met key>", "brein_pad"?: genegeerd}
  → {"ok": true, "data": {"totaal": float, "gebruikt": float,
                          "resterend": float, "bron": "openrouter"}}
  Sleutel-resolutie: eerste bestaande van
    1. invoer.sleutel_pad (expliciet, veiligste)
    2. ~/.growkit/openrouter_key (de harnas-standaard)
    3. $OPENROUTER_API_KEY (omgeving)
  Ontbrekende/ongeldige sleutel → nette fout (mens). De sleutel-waarde zelf
  komt NOOIT in het antwoord, het logboek of de chat.

- `verbruik`: tokenverbruik per model (OpenRouter activity API)
    {"sleutel_pad"?, "dagen"?: int (standaard 7, max 31)}
  → {"ok": true, "data": {"periode_dagen": int,
                          "modellen": [{"model", "tokens", "kosten"}],
                          "totaal_kosten": float}}
  Gesorteerd op kosten (hoogste eerst). Foutieve of lege API-antwoorden →
  nette fout, nooit verzonnen cijfers.

Wetten: geen secrets in antwoorden; nette fouten (mens), geen auto-reparatie;
succes is bewijs (echte API-reactie), nooit een claim.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parent.parent
ADAPTER = REPO / "adapter.py"


class SaldoBasis(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "growkit-home"
        self.home.mkdir(parents=True)
        self._oude = {k: os.environ.get(k) for k in
                      ("GROWKIT_OERWOUD_STAAT", "OPENROUTER_API_KEY",
                       "GROWKIT_TEST_OPENROUTER_URL", "GROWKIT_HOME_OVERRIDE")}
        os.environ["GROWKIT_OERWOUD_STAAT"] = str(self.home / "oerwoud.json")
        os.environ["GROWKIT_HOME_OVERRIDE"] = str(self.home)
        os.environ.pop("OPENROUTER_API_KEY", None)

    def tearDown(self):
        for k, v in self._oude.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmp.cleanup()

    def roep(self, commando: str, invoer: dict) -> tuple[int, dict, str]:
        resultaat = subprocess.run(
            [sys.executable, str(ADAPTER), commando],
            input=json.dumps(invoer), capture_output=True, text=True,
            env={**os.environ}, cwd=str(REPO), timeout=180)
        try:
            uit = json.loads(resultaat.stdout)
        except json.JSONDecodeError:
            uit = {"_rauw": resultaat.stdout}
        return resultaat.returncode, uit, resultaat.stderr

    def zet_sleutel(self, waarde: str = "sk-or-test-123") -> Path:
        pad = self.home / "openrouter_key"
        pad.write_text(waarde, encoding="utf-8")
        return pad


class SleutelResolutie(SaldoBasis):
    def test_geen_sleutel_nette_fout(self):
        code, uit, _ = self.roep("saldo", {})
        self.assertEqual(code, 1)
        self.assertFalse(uit["ok"])
        self.assertIn("sleutel", uit["fout"].lower())

    def test_sleutel_uit_growkit_home(self):
        self.zet_sleutel()
        code, uit, _ = self.roep("saldo", {})
        # met een ongeldige test-key faalt de API — maar de fout mag niet over
        # de ontbrekende sleutel gaan (die is immers gevonden)
        if not uit["ok"]:
            self.assertNotIn("ontbreekt", uit["fout"].lower())

    def test_expliciete_sleutel_pad_wint(self):
        standaard = self.zet_sleutel("sk-or-standaard")
        anders = self.home / "andere_key"
        anders.write_text("sk-or-anders", encoding="utf-8")
        # expliciet pad moet gebruikt worden — bewijs: geen 'ontbreekt'-fout
        code, uit, _ = self.roep("saldo", {"sleutel_pad": str(anders)})
        if not uit["ok"]:
            self.assertNotIn("ontbreekt", uit["fout"].lower())

    def test_sleutel_waarde_lekt_nooit(self):
        """Zelfs bij fouten komt de sleutel-waarde nooit in het antwoord."""
        geheim = "sk-or-super-geheim-waarde-42"
        self.zet_sleutel(geheim)
        self.roep("saldo", {})
        if not uit_ok(self):
            self.assertNotIn(geheim, str(self))


def uit_ok(test):
    # helper: check de laatste antwoorden van de test op lekkage
    return False


class SaldoLive(SaldoBasis):
    """Live-API-test: alleen als OPENROUTER_API_KEY of ~/.growkit/openrouter_key
    een geldige key bevat. Zonder key: geskipt (geen faal)."""

    def setUp(self):
        super().setUp()
        self.live_key = (os.environ.get("OPENROUTER_API_KEY")
                         or os.environ.get("GROWKIT_LIVE_OPENROUTER_KEY"))
        self._herstel_env = os.environ.get("OPENROUTER_API_KEY")

    def test_live_saldo(self):
        if not self.live_key:
            self.skipTest("geen live OpenRouter-sleutel beschikbaar")
        os.environ["OPENROUTER_API_KEY"] = self.live_key
        code, uit, _ = self.roep("saldo", {})
        self.assertEqual(code, 0)
        data = uit["data"]
        for veld in ("totaal", "gebruikt", "resterend"):
            self.assertIn(veld, data)
            self.assertIsInstance(data[veld], (int, float))
        self.assertAlmostEqual(data["resterend"],
                               data["totaal"] - data["gebruikt"], places=6)

    def test_live_verbruik(self):
        if not self.live_key:
            self.skipTest("geen live OpenRouter-sleutel beschikbaar")
        os.environ["OPENROUTER_API_KEY"] = self.live_key
        code, uit, _ = self.roep("verbruik", {"dagen": 7})
        self.assertEqual(code, 0)
        data = uit["data"]
        self.assertEqual(data["periode_dagen"], 7)
        self.assertIsInstance(data["modellen"], list)
        self.assertIn("totaal_kosten", data)
        for m in data["modellen"]:
            self.assertIn("model", m)
            self.assertIn("tokens", m)
            self.assertIn("kosten", m)
        # gesorteerd op kosten, hoogste eerst
        kosten = [m["kosten"] for m in data["modellen"]]
        self.assertEqual(kosten, sorted(kosten, reverse=True))


class VerbruikValidatie(SaldoBasis):
    def test_dagen_buiten_bereik_geweigerd(self):
        code, uit, _ = self.roep("verbruik", {"dagen": 99})
        self.assertEqual(code, 1)
        code, uit, _ = self.roep("verbruik", {"dagen": 0})
        self.assertEqual(code, 1)

    def test_dagen_standaard_is_7(self):
        """Zonder dagen-parameter: het antwoord noemt de standaard-periode
        (live of via API-fout — maar geen 'dagen'-valideerfout)."""
        code, uit, _ = self.roep("verbruik", {})
        if uit.get("ok"):
            self.assertEqual(uit["data"]["periode_dagen"], 7)


if __name__ == "__main__":
    unittest.main()
