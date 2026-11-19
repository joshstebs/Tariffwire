import json
import unittest
from datetime import datetime, timezone
from io import BytesIO

from tariffwire.monitor import _markers, run_check

class FakeResponse(BytesIO):
    def __init__(self, body: bytes, status: int = 200):
        super().__init__(body)
        self.status = status
        self.headers = {"Content-Type": "text/html"}

    def getcode(self):
        return self.status

    def geturl(self):
        return "https://example.test/final"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class MonitorTests(unittest.TestCase):
    def test_hash_change_is_not_described_as_a_rate_change(self):
        phase = {"later": False}

        def opener(request, timeout):
            edition = b"T2026-3 Effective date: 2026-11-01" if phase["later"] else b"T2026-2 Effective date: 2026-09-01"
            return FakeResponse(b"<html>" + edition + b" " + request.full_url.encode() + b"</html>")

        first = run_check(
            opener=opener,
            write=False,
            now=datetime(2026, 11, 13, tzinfo=timezone.utc),
        )
        self.assertTrue(all(item["ok"] for item in first["observations"]))
        self.assertEqual(first["live_tariff_integration"], False)
        self.assertIn("does not identify a duty-rate amendment", first["observations"][0]["interpretation"])
        self.assertIn("T2026-2", first["observations"][0]["markers"]["edition_token"])

        phase["later"] = True
        second = run_check(
            opener=opener,
            write=False,
            now=datetime(2026, 11, 14, tzinfo=timezone.utc),
        )
        # Without a saved baseline, both runs report no_baseline. Compare hashes directly.
        self.assertNotEqual(first["observations"][0]["sha256"], second["observations"][0]["sha256"])
        self.assertNotIn("duty rate changed", json.dumps(second).lower())

    def test_markers_still_match_when_html_splits_the_phrase(self):
        found = _markers("<p>Act current to 2026-10-19 and last amended on <span>2026-09-01</span></p>")
        self.assertEqual(found["act_current_to"], ["Act current to 2026-10-19"])
        self.assertEqual(found["last_amended"], ["last amended on 2026-09-01"])


if __name__ == "__main__":
    unittest.main()
