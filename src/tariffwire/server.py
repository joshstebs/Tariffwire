"""Small local web server for the reading room.

The server reads bundled JSON and can fingerprint the fixed watchlist.
It has no path that accepts an arbitrary URL, and no path that returns a duty rate.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from tariffwire import __version__
from tariffwire.catalog import (
    chapter_by_number,
    chapters_catalog,
    document_by_id,
    documents_catalog,
    search,
    sources_catalog,
)
from tariffwire.classify import EXPANSIONS, research_packet
from tariffwire.monitor import latest_report, run_check
from tariffwire.paths import WEB_DIR

_STATIC = {
    "/": "index.html",
    "/index.html": "index.html",
    "/styles.css": "styles.css",
    "/app.js": "app.js",
}


class TariffWireHandler(BaseHTTPRequestHandler):
    server_version = "TariffWire/0.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path in _STATIC:
            self._static(_STATIC[path])
            return
        if path == "/api/meta":
            catalog = chapters_catalog()
            self._json(
                {
                    "name": "TariffWire",
                    "version": __version__,
                    "live_tariff_integration": False,
                    "jurisdiction": "Canada",
                    "edition": catalog.get("edition"),
                    "index_retrieved_at": catalog.get("retrieved_at"),
                    "chapter_count": len(catalog.get("chapters", [])),
                    "document_count": len(documents_catalog().get("documents", [])),
                    "search_expansions": EXPANSIONS,
                    "disclaimer": (
                        "Unofficial informational aid. Not a CBSA system and not a customs determination."
                    ),
                }
            )
            return
        if path == "/api/search":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            self._json(search(query))
            return
        if path == "/api/chapters":
            self._json(chapters_catalog())
            return
        if path.startswith("/api/chapters/"):
            raw = path.removeprefix("/api/chapters/")
            if not raw.isdigit():
                self._error(400, "Chapter number must be an integer")
                return
            chapter = chapter_by_number(int(raw))
            if not chapter:
                self._error(404, "No stored chapter with that number")
                return
            catalog = chapters_catalog()
            self._json(
                {
                    **chapter,
                    "edition": catalog["edition"],
                    "index_url": catalog["index_url"],
                    "retrieved_at": catalog["retrieved_at"],
                    "publisher": catalog["publisher"],
                    "jurisdiction": catalog["jurisdiction"],
                    "caveat": catalog["caveat"],
                    "duty_rate": None,
                    "tariff_classification": None,
                }
            )
            return
        if path == "/api/documents":
            self._json(documents_catalog())
            return
        if path.startswith("/api/documents/"):
            document = document_by_id(path.removeprefix("/api/documents/"))
            if not document:
                self._error(404, "No stored document with that id")
                return
            self._json(document)
            return
        if path == "/api/sources":
            self._json(sources_catalog())
            return
        if path == "/api/monitor":
            report = latest_report()
            if report is None:
                self._json(
                    {
                        "checked_at": None,
                        "live_tariff_integration": False,
                        "meaning": "No page-fingerprint report has been saved yet.",
                        "observations": [],
                    }
                )
                return
            self._json(report)
            return
        self._error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 100_000:
            self._error(413, "Request body is too large")
            return
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._error(400, "Body must be JSON")
            return
        if not isinstance(payload, dict):
            self._error(400, "Body must be a JSON object")
            return
        if parsed.path == "/api/classify":
            self._json(
                research_packet(
                    str(payload.get("description") or ""),
                    materials=str(payload.get("materials") or ""),
                    function=str(payload.get("function") or ""),
                    condition=str(payload.get("condition") or ""),
                    origin=str(payload.get("origin") or ""),
                    importation=str(payload.get("importation") or ""),
                )
            )
            return
        if parsed.path == "/api/monitor/run":
            # The client cannot supply URLs. The watchlist is the only fetch set.
            self._json(run_check(write=True))
            return
        self._error(404, "Not found")

    def log_message(self, fmt: str, *args) -> None:
        return

    def _static(self, name: str) -> None:
        path = (WEB_DIR / name).resolve()
        if WEB_DIR.resolve() not in path.parents and path != WEB_DIR.resolve():
            self._error(404, "Not found")
            return
        if not path.is_file():
            self._error(404, "Not found")
            return
        content_type = "text/plain; charset=utf-8"
        if name.endswith(".html"):
            content_type = "text/html; charset=utf-8"
        elif name.endswith(".css"):
            content_type = "text/css; charset=utf-8"
        elif name.endswith(".js"):
            content_type = "application/javascript; charset=utf-8"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _error(self, status: int, message: str) -> None:
        data = json.dumps({"error": message}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    httpd = ThreadingHTTPServer((host, port), TariffWireHandler)
    print(f"TariffWire reading room at http://{host}:{port}")
    httpd.serve_forever()
