import json
import tempfile
import unittest
from pathlib import Path

from kern.growkit_bewijs import controleer


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
