"""Gegevensroute en cloudtoestemming (advies 6).

Wat hier wordt vastgehouden:
- de route wordt afgeleid uit de commando's (lokaal / eigen VPS / cloud);
- verklaart een profiel minder dan zijn commando's doen, dan wint het zwaarste
  én komt er een waarschuwing — geen stille keuze;
- een cloud-opdracht start nooit zonder jouw expliciete toestemming, en die
  toestemming staat in de geschiedenis (ook als je hem intrekt).
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import adapter
from kern import growkit_opdrachten as op
from kern import growkit_route as route
from seed import laad_profielen


def profiel_van(naam: str) -> dict:
    return next(p for p in laad_profielen() if p["profiel"] == naam)


def een_stap(commando: str) -> dict:
    return {"stappen": [{"id": "s1", "commando": commando,
                         "bewijs": {"type": "file_exists", "pad": "x"}}]}


class RouteAfleiding(unittest.TestCase):
    def test_zonder_extern_commando_is_de_route_lokaal(self):
        zelf = route.route(een_stap("mkdir -p x"))
        self.assertEqual(zelf["soort"], "lokaal")
        self.assertEqual(zelf["verzendt"], [])

    def test_ssh_naar_eigen_server_is_eigen_vps(self):
        uit = route.route(een_stap("ssh gast@mijn-server 'ls'"))
        self.assertEqual(uit["soort"], "eigen_vps")
        self.assertTrue(uit["verzendt"])

    def test_http_is_cloud(self):
        self.assertEqual(route.route(een_stap("curl https://api.voorbeeld.nl/v1"))["soort"], "cloud")

    def test_cloud_wint_van_eigen_vps(self):
        profiel = {"stappen": [{"id": "a", "commando": "ssh gast@vps 'x'"},
                               {"id": "b", "commando": "wget https://x.nl"}]}
        self.assertEqual(route.route(profiel)["soort"], "cloud")

    def test_lichter_verklaard_dan_gedaan_wordt_gemeld(self):
        profiel = een_stap("curl https://api.voorbeeld.nl/v1")
        profiel["gegevensroute"] = {"soort": "lokaal", "uitleg": "zegt lokaal"}
        uit = route.route(profiel)
        self.assertEqual(uit["soort"], "cloud")                        # zwaarste wint
        self.assertIn("maar een commando gaat verder", uit["waarschuwing"])

    def test_zwaarder_verklaren_mag_zonder_waarschuwing(self):
        profiel = een_stap("mkdir -p x")
        profiel["gegevensroute"] = {"soort": "cloud", "uitleg": "voorzichtig"}
        uit = route.route(profiel)
        self.assertEqual(uit["soort"], "cloud")
        self.assertIsNone(uit["waarschuwing"])

    def test_alle_bestaande_profielen_zijn_lokaal_en_verzenden_niets(self):
        for naam in ("projectcontrole", "documentenoverzicht", "terugkerend-rapport",
                     "tweede-brein"):
            uit = route.route(profiel_van(naam))
            self.assertEqual(uit["soort"], "lokaal", naam)
            self.assertEqual(uit["verzendt"], [], naam)
            self.assertEqual(uit["bron"], "verklaard", naam)

    def test_uitgebreide_netwerksignalen_zijn_nooit_lokaal(self):
        """Elk bekend netwerkcommando moet als extern worden herkend."""
        for commando in ("git push origin main", "git clone https://x.nl/r.git",
                         "git fetch --all", "pip install requests",
                         "npm install left-pad", "nc -l 1234", "ftp server",
                         "python -c 'import urllib.request'",
                         "python -c 'import requests'",
                         "ssh gast@server 'ls'", "scp bestand gast@server:/tmp",
                         "rsync -a . gast@server:/tmp"):
            self.assertNotEqual(route.route(een_stap(commando))["soort"], "lokaal", commando)

    def test_hoofdletters_maken_niets_uit(self):
        self.assertEqual(route.route(een_stap("SSH gast@server 'ls'"))["soort"], "eigen_vps")
        self.assertEqual(route.route(een_stap("GIT PUSH origin main"))["soort"], "cloud")

    def test_woordgrens_voorkomt_valse_alarmen(self):
        """'sync' is geen rsync en 'ncat' is geen nc."""
        for commando in ("cat sync.json", "python3 -m json.tool ncat.log",
                         "echo curling is een sport"):
            self.assertEqual(route.route(een_stap(commando))["soort"], "lokaal", commando)


class CloudPoort(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch.object(op, "_root", return_value=Path(self.tmp.name)).start()
        self.addCleanup(patch.stopall)
        self.profiel = {
            "profiel": "cloud-demo",
            "gegevensroute": {"soort": "cloud", "uitleg": "stuurt inhoud naar een clouddienst"},
            "stappen": [{"id": "s1", "commando": "touch bewijs.txt",
                         "bewijs": {"type": "file_exists", "pad": "bewijs.txt"}}],
        }

    def _nieuw(self) -> dict:
        return op.nieuw("Cloudproef", ["Het bewijs bestaat"], self.profiel)

    def test_zonder_toestemming_start_er_niets(self):
        dossier = self._nieuw()
        self.assertEqual(dossier["gegevensroute"]["soort"], "cloud")
        self.assertFalse(dossier["cloud_toestemming"])
        with self.assertRaises(ValueError) as ctx:
            op.uitvoeren(dossier["id"], dossier["plan_hash"], True)
        self.assertIn("toestemming", str(ctx.exception))
        self.assertFalse((Path(dossier["doel"]) / "bewijs.txt").exists())

    def test_met_toestemming_draait_het_en_staat_het_in_de_geschiedenis(self):
        dossier = self._nieuw()
        dossier = op.toestemming(dossier["id"], True, "Bewust via de cloud, deze opdracht")
        self.assertTrue(dossier["cloud_toestemming"])
        dossier = op.uitvoeren(dossier["id"], dossier["plan_hash"], True)
        self.assertEqual(dossier["status"], "resultaat")
        self.assertIn("cloudtoestemming", [e["actie"] for e in dossier["geschiedenis"]])

    def test_intrekken_werkt_en_blokkeert_weer(self):
        dossier = self._nieuw()
        dossier = op.toestemming(dossier["id"], True, "Eerste keer akkoord")
        dossier = op.toestemming(dossier["id"], False, "Ik trek het in")
        self.assertFalse(dossier["cloud_toestemming"])
        with self.assertRaises(ValueError):
            op.uitvoeren(dossier["id"], dossier["plan_hash"], True)

    def test_toestemming_zonder_reden_is_geen_toestemming(self):
        dossier = self._nieuw()
        with self.assertRaises(ValueError):
            op.toestemming(dossier["id"], True, "   ")

    def test_adapteractie_toestemming_werkt(self):
        dossier = self._nieuw()
        uit = adapter.cmd_opdrachten({"actie": "toestemming", "id": dossier["id"],
                                      "akkoord": True, "toelichting": "Bewust akkoord"})
        self.assertTrue(uit["ok"])
        self.assertTrue(uit["data"]["cloud_toestemming"])
