import json
import threading
import unittest
from urllib.request import Request, urlopen

from tariffwire.server import TariffWireHandler
from http.server import ThreadingHTTPServer


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), TariffWireHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(timeout=5)

    def request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode())

    def test_pages_and_research_packet(self):
        meta = self.request("/api/meta")
        self.assertFalse(meta["live_tariff_integration"])
        self.assertEqual(meta["chapter_count"], 99)
        home = urlopen(f"http://127.0.0.1:{self.port}/", timeout=10)
        html = home.read().decode()
        self.assertIn("not a customs determination", html)
        packet = self.request("/api/classify", {"description": "ceramic mug"})
        self.assertIsNone(packet["duty_rate"])
        self.assertIsNone(packet["tariff_classification"])
        self.assertTrue(any(item["chapter"] == 69 for item in packet["candidate_chapters"]))


if __name__ == "__main__":
    unittest.main()
