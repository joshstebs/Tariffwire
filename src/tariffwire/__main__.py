"""Command line entry points for the reading room."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from urllib.request import Request, urlopen

from tariffwire.catalog import clear_caches, search
from tariffwire.classify import research_packet
from tariffwire.index_parser import INDEX_URL, parse_chapter_index, require_complete_chapter_span
from tariffwire.monitor import USER_AGENT, run_check
from tariffwire.paths import CHAPTERS_PATH
from tariffwire.server import serve


def _refresh_index() -> int:
    request = Request(INDEX_URL, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=45) as response:
        if response.status != 200:
            print(f"Index request failed with HTTP {response.status}", file=sys.stderr)
            return 1
        page = response.read().decode("utf-8", "replace")
        final_url = response.geturl()
    catalog = parse_chapter_index(page, index_url=final_url, retrieved_on=date.today().isoformat())
    require_complete_chapter_span(catalog)
    CHAPTERS_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    clear_caches()
    print(
        f"Wrote {len(catalog['chapters'])} chapters for {catalog['edition']} "
        f"retrieved {catalog['retrieved_at']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tariffwire", description="TariffWire informational reading room")
    sub = parser.add_subparsers(dest="command", required=True)

    serve_parser = sub.add_parser("serve", help="Run the local reading room")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=int(os.environ.get("TARIFFWIRE_PORT", "8765")))

    sub.add_parser("refresh-index", help="Re-read the public CBSA chapter index")
    sub.add_parser("monitor", help="Fingerprint the public watchlist")

    search_parser = sub.add_parser("search", help="Search stored titles and documents")
    search_parser.add_argument("query")

    classify_parser = sub.add_parser("classify", help="Build a research packet that does not classify")
    classify_parser.add_argument("description")
    classify_parser.add_argument("--origin", default="")
    classify_parser.add_argument("--materials", default="")

    args = parser.parse_args(argv)
    if args.command == "serve":
        serve(args.host, args.port)
        return 0
    if args.command == "refresh-index":
        return _refresh_index()
    if args.command == "monitor":
        report = run_check(write=True)
        print(
            f"Checked {report['observation_count']} pages at {report['checked_at']}; "
            f"failures={report['failure_count']} byte_changes={report['changed_count']}"
        )
        return 0 if report["failure_count"] == 0 else 1
    if args.command == "search":
        print(json.dumps(search(args.query), indent=2, ensure_ascii=False))
        return 0
    if args.command == "classify":
        print(
            json.dumps(
                research_packet(args.description, origin=args.origin, materials=args.materials),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
