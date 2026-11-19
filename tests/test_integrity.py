"""Regression tests for source-integrity hardening (2026-11-14 review)."""

import copy
import json
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tariffwire import monitor
from tariffwire.classify import DETERMINATION_FIELDS, _guard, research_packet
from tariffwire.server import TariffWireHandler


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


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.packet = research_packet("ceramic mug from the United States", origin="United States")

    def test_every_determination_field_fails_closed(self):
        for field in DETERMINATION_FIELDS:
            with self.subTest(field=field):
                tampered = copy.deepcopy(self.packet)
                tampered[field] = "filled in"
                with self.assertRaises(RuntimeError):
                    _guard(tampered)

    def test_missing_determination_field_fails_closed(self):
        tampered = copy.deepcopy(self.packet)
        del tampered["surtax_determination"]
        with self.assertRaises(RuntimeError):
            _guard(tampered)

    def test_candidate_cannot_carry_a_tariff_item_or_change_basis(self):
        self.assertTrue(self.packet["candidate_chapters"])
        for key, value in (("tariff_item", "6912.00.00"), ("duty_rate", "Free"), ("basis", "general_rules")):
            with self.subTest(key=key):
                tampered = copy.deepcopy(self.packet)
                tampered["candidate_chapters"][0][key] = value
                with self.assertRaises(RuntimeError):
                    _guard(tampered)

    def test_user_supplied_code_cannot_be_marked_verified(self):
        packet = research_packet("mug 6912.00.00")
        self.assertTrue(packet["user_supplied_code"]["unverified"])
        tampered = copy.deepcopy(packet)
        tampered["user_supplied_code"]["exists_in_stored_schedule"] = True
        with self.assertRaises(RuntimeError):
            _guard(tampered)

    def test_named_chapter_is_not_duplicated(self):
        packet = research_packet("chapter 9 coffee chapter 9")
        ch9 = [item for item in packet["candidate_chapters"] if item["chapter"] == 9]
        self.assertEqual(len(ch9), 1)
        self.assertEqual(ch9[0]["matched_terms"].count("named chapter number"), 1)


class MonitorIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.baseline = root / "baseline.json"
        self.latest = root / "latest.json"
        self.patches = [
            mock.patch.object(monitor, "MONITOR_BASELINE_PATH", self.baseline),
            mock.patch.object(monitor, "MONITOR_LATEST_PATH", self.latest),
            mock.patch.object(
                monitor,
                "load_watchlist",
                return_value=[
                    {"id": "page-a", "url": "https://example.test/a", "title": "A"},
                    {"id": "page-b", "url": "https://example.test/b", "title": "B"},
                ],
            ),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        self.tmp.cleanup()

    def test_per_request_script_nonce_is_not_reported_as_a_change(self):
        counter = {"n": 0}

        def opener(request, timeout):
            counter["n"] += 1
            nonce = f"nonce-{counter['n']}".encode()
            return FakeResponse(b"<html><script>var t='" + nonce + b"';</script><p>T2026-2 list</p></html>")

        first = monitor.run_check(opener=opener, write=True, now=datetime(2026, 11, 14, tzinfo=timezone.utc))
        self.assertEqual({o["change"] for o in first["observations"]}, {"baseline_created"})
        second = monitor.run_check(opener=opener, write=False)
        for observation in second["observations"]:
            self.assertEqual(observation["change"], "unchanged_since_baseline")
            self.assertTrue(observation["raw_bytes_differ_in_scripts_or_markup_only"])
        self.assertEqual(second["changed_count"], 0)

    def test_server_marker_comment_variants_hash_the_same(self):
        # Observed live on laws-lois.justice.gc.ca, 2026-11-14: two edge variants differ only here.
        a = "<p>Act current to 2026-10-19</p>\n<!-- CURATE --> \t\n</body>"
        b = "<p>Act current to 2026-10-19</p>\n<!-- ELAPSE --> \n</body>"
        self.assertEqual(monitor.content_digest(a), monitor.content_digest(b))
        self.assertNotEqual(monitor.content_digest(a), monitor.content_digest(a.replace("10-19", "11-02")))

    def test_visible_text_change_is_reported(self):
        phase = {"later": False}

        def opener(request, timeout):
            text = b"T2026-3" if phase["later"] else b"T2026-2"
            return FakeResponse(b"<html><p>" + text + b"</p></html>")

        monitor.run_check(opener=opener, write=True)
        phase["later"] = True
        report = monitor.run_check(opener=opener, write=False)
        self.assertEqual({o["change"] for o in report["observations"]}, {"page_content_changed"})
        self.assertEqual(report["changed_count"], 2)
        self.assertNotIn("duty rate changed", json.dumps(report).lower())

    def test_legacy_baseline_without_content_hash_falls_back_to_raw_bytes(self):
        self.baseline.write_text(json.dumps({"checked_at": "2026-11-13", "observations": [
            {"id": "page-a", "sha256": "0" * 64},
            {"id": "page-b", "sha256": "0" * 64},
        ]}))
        report = monitor.run_check(opener=lambda r, timeout: FakeResponse(b"<p>x</p>"), write=False)
        for observation in report["observations"]:
            self.assertEqual(observation["change"], "page_bytes_changed")
            self.assertTrue(observation["baseline_has_no_content_hash"])

    def test_timeout_or_dropped_connection_does_not_abort_the_run(self):
        def opener(request, timeout):
            if request.full_url.endswith("/a"):
                raise TimeoutError("timed out")
            raise ConnectionResetError("Remote end closed connection without response")

        report = monitor.run_check(opener=opener, write=False)
        self.assertEqual(report["failure_count"], 2)
        self.assertEqual({o["change"] for o in report["observations"]}, {"check_failed"})
        self.assertIn("TimeoutError", report["observations"][0]["error"])


class PostContentTypeTests(unittest.TestCase):
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

    def test_simple_cross_site_post_is_rejected(self):
        for path in ("/api/monitor/run", "/api/classify"):
            with self.subTest(path=path):
                request = Request(
                    f"http://127.0.0.1:{self.port}{path}",
                    data=b"{}",
                    headers={"Content-Type": "text/plain"},
                )
                with self.assertRaises(HTTPError) as caught:
                    urlopen(request, timeout=10)
                self.assertEqual(caught.exception.code, 415)


if __name__ == "__main__":
    unittest.main()
