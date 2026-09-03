import unittest

from kern.growkit_review import roep_reviewer

STAP = {"id": "stap-x", "verwacht": "de structuur klopt"}
UITVOER = "drie bestanden getoond"
CONFIG = {
    "rollen": {
        "reviewer_cli": {"type": "cli", "commando": "echo geslaagd"},
    }
}


class TestCliReviewer(unittest.TestCase):
    def test_geslaagd(self):
        oordeel = roep_reviewer("reviewer_cli", STAP, UITVOER, CONFIG)
        self.assertEqual(oordeel, "geslaagd")

    def test_onzinnig_antwoord_is_onduidelijk(self):
        config = {"rollen": {"r": {"type": "cli", "commando": "echo misschien-wel-misschien-niet"}}}
        self.assertEqual(roep_reviewer("r", STAP, UITVOER, config), "onduidelijk")

    def test_crash_is_onduidelijk(self):
        config = {"rollen": {"r": {"type": "cli", "commando": "bestaat-niet-commando-xyz"}}}
        self.assertEqual(roep_reviewer("r", STAP, UITVOER, config), "onduidelijk")


class TestHttpReviewer(unittest.TestCase):
    def test_post_brengt_payload_over_en_leest_oordeel(self):
        # miniem lokale http-server die het verzoek beantwoordt met een oordeel-JSON
        import json
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        ontvangen = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                lengte = int(self.headers.get("Content-Length", 0))
                ontvangen["payload"] = self.rfile.read(lengte).decode("utf-8")
                body = json.dumps({"oordeel": "geslaagd"}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            poort = server.server_address[1]
            config = {"rollen": {"r": {"type": "http", "url": "http://127.0.0.1:%d/review" % poort, "verwacht_status": 200}}}
            oordeel = roep_reviewer("r", STAP, UITVOER, config)
            self.assertEqual(oordeel, "geslaagd")
            # de payload bevat de stap én de uitvoer
            self.assertIn("stap-x", ontvangen["payload"])
            self.assertIn(UITVOER, ontvangen["payload"])
        finally:
            server.shutdown()

    def test_http_fout_is_onduidelijk(self):
        # poort zonder server → verbindingsfout → onduidelijk
        config = {"rollen": {"r": {"type": "http", "url": "http://127.0.0.1:59999/review", "verwacht_status": 200}}}
        self.assertEqual(roep_reviewer("r", STAP, UITVOER, config), "onduidelijk")


class TestGrenzen(unittest.TestCase):
    def test_onbekende_rol_is_onduidelijk(self):
        self.assertEqual(roep_reviewer("bestaat-niet", STAP, UITVOER, CONFIG), "onduidelijk")

    def test_shell_injectie_via_uitvoer_is_onmogelijk(self):
        # kwaadaardige uitvoer-inhoud mag nooit als commando worden uitgevoerd;
        # stdin-only transport betekent: het antwoord blijft "geslaagd" en er is geen effect
        kwaadaardig = '"; rm -rf ~; echo "'
        config = {"rollen": {"r": {"type": "cli", "commando": "echo geslaagd"}}}
        self.assertEqual(roep_reviewer("r", STAP, kwaadaardig, config), "geslaagd")


if __name__ == "__main__":
    unittest.main()
