"""Fingerprint public pages. A hash change is not a parsed tariff amendment.

The monitor fetches only URLs on the local watchlist. It records status,
byte length, a SHA-256 of the body, and a few literal markers. It does not
log in, does not call CARM, and does not decide that a duty rate changed.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tariffwire.paths import MONITOR_BASELINE_PATH, MONITOR_LATEST_PATH, WATCHLIST_PATH

USER_AGENT = "TariffWirePageCheck/0.1 (public regulatory reading room; +https://github.com/joshstebs/tariffwire_trade_assistant)"
MARKER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("edition_token", re.compile(r"T20\d{2}(?:-\d+)?")),
    ("effective_date", re.compile(r"Effective date:?\s*\d{4}-\d{2}-\d{2}", re.I)),
    ("act_current_to", re.compile(r"Act current to \d{4}-\d{2}-\d{2}", re.I)),
    ("last_amended", re.compile(r"last amended on \d{4}-\d{2}-\d{2}", re.I)),
    ("regulations_current_to", re.compile(r"Regulations are current to \d{4}-\d{2}-\d{2}", re.I)),
    ("sor_number", re.compile(r"SOR/\d{4}-\d+")),
    ("cpukt", re.compile(r"CPUKT")),
]


def load_watchlist() -> list[dict[str, Any]]:
    with WATCHLIST_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    entries = payload["entries"]
    urls = [entry["url"] for entry in entries]
    if len(urls) != len(set(urls)):
        raise ValueError("Watchlist URLs must be unique")
    for entry in entries:
        if not entry["url"].startswith("https://"):
            raise ValueError(f"Watchlist URL must be https: {entry['url']}")
    return entries


def _markers(body: str) -> dict[str, list[str]]:
    """Read a few literal phrases. Tags are removed so split headings still match."""
    text = re.sub(r"<[^>]+>", " ", body)
    text = re.sub(r"\s+", " ", text)
    found: dict[str, list[str]] = {}
    for name, pattern in MARKER_PATTERNS:
        values = list(dict.fromkeys(pattern.findall(text)))
        if values:
            found[name] = values[:12]
    return found


def fetch_entry(
    entry: dict[str, Any],
    *,
    opener: Callable[..., Any] | None = None,
    timeout: float = 30,
) -> dict[str, Any]:
    """Fetch one watchlist entry. `opener` is injectable for tests."""
    request = Request(entry["url"], headers={"User-Agent": USER_AGENT})
    open_fn = opener or urlopen
    try:
        with open_fn(request, timeout=timeout) as response:
            raw = response.read()
            status = getattr(response, "status", None) or response.getcode()
            final_url = response.geturl() if hasattr(response, "geturl") else entry["url"]
            content_type = ""
            headers = getattr(response, "headers", None)
            if headers is not None:
                content_type = headers.get("Content-Type", "")
    except HTTPError as exc:
        return {
            "id": entry["id"],
            "url": entry["url"],
            "ok": False,
            "http_status": exc.code,
            "error": f"HTTP {exc.code}",
            "sha256": None,
            "bytes": None,
            "markers": {},
        }
    except URLError as exc:
        return {
            "id": entry["id"],
            "url": entry["url"],
            "ok": False,
            "http_status": None,
            "error": str(exc.reason),
            "sha256": None,
            "bytes": None,
            "markers": {},
        }

    text = raw.decode("utf-8", "replace")
    return {
        "id": entry["id"],
        "title": entry.get("title"),
        "url": entry["url"],
        "final_url": final_url,
        "ok": 200 <= int(status) < 400,
        "http_status": int(status),
        "content_type": content_type,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "markers": _markers(text),
        "error": None,
        "interpretation": (
            "SHA-256 covers the HTTP body. A change means those bytes changed. "
            "It does not identify a duty-rate amendment."
        ),
    }


def _read_json(path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def run_check(
    *,
    opener: Callable[..., Any] | None = None,
    write: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    moment = now or datetime.now(timezone.utc)
    observations = [fetch_entry(entry, opener=opener) for entry in load_watchlist()]
    baseline = _read_json(MONITOR_BASELINE_PATH)
    previous = {
        item["id"]: item
        for item in (baseline or {}).get("observations", [])
    }
    for observation in observations:
        prior = previous.get(observation["id"])
        if not observation["ok"]:
            observation["change"] = "check_failed"
        elif prior is None or not prior.get("sha256"):
            observation["change"] = "no_baseline"
        elif prior.get("sha256") == observation.get("sha256"):
            observation["change"] = "unchanged_since_baseline"
        else:
            observation["change"] = "page_bytes_changed"
            observation["baseline_sha256"] = prior.get("sha256")

    report = {
        "checked_at": moment.isoformat(),
        "live_tariff_integration": False,
        "meaning": (
            "On-demand fingerprint of public web pages. This is not a feed of "
            "tariff amendments and it is not a connection to CBSA accounting systems."
        ),
        "baseline_checked_at": (baseline or {}).get("checked_at"),
        "observation_count": len(observations),
        "failure_count": sum(1 for item in observations if not item["ok"]),
        "changed_count": sum(1 for item in observations if item["change"] == "page_bytes_changed"),
        "observations": observations,
    }
    if write:
        MONITOR_LATEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MONITOR_LATEST_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if baseline is None:
            MONITOR_BASELINE_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            for observation in report["observations"]:
                if observation["change"] == "no_baseline" and observation["ok"]:
                    observation["change"] = "baseline_created"
            MONITOR_LATEST_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            MONITOR_BASELINE_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def latest_report() -> dict[str, Any] | None:
    return _read_json(MONITOR_LATEST_PATH)
