"""Fingerprint public pages. A hash change is not a parsed tariff amendment.

The monitor fetches only URLs on the local watchlist. It records status,
byte length, a SHA-256 of the body, and a few literal markers. It does not
log in, does not call CARM, and does not decide that a duty rate changed.
"""

from __future__ import annotations

import hashlib
import http.client
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


_VOLATILE_RE = re.compile(
    r"<script\b[^>]*>.*?</script\s*>|<style\b[^>]*>.*?</style\s*>|<!--.*?-->",
    re.I | re.S,
)
CONTENT_HASH_BASIS = (
    "SHA-256 of the HTML after removing <script>, <style> and comment blocks and "
    "collapsing whitespace. Some government pages embed a per-request analytics "
    "nonce in a script tag, so the raw-byte hash changes on every fetch."
)


def content_digest(body: str) -> str:
    """Hash the page without blocks that change on every request."""
    text = _VOLATILE_RE.sub(" ", body)
    text = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _failed(entry: dict[str, Any], status: int | None, error: str) -> dict[str, Any]:
    return {
        "id": entry["id"],
        "url": entry["url"],
        "ok": False,
        "http_status": status,
        "error": error,
        "sha256": None,
        "content_sha256": None,
        "bytes": None,
        "markers": {},
    }


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
        return _failed(entry, exc.code, f"HTTP {exc.code}")
    except URLError as exc:
        return _failed(entry, None, str(exc.reason))
    except (TimeoutError, OSError, http.client.HTTPException) as exc:
        # A timeout or dropped connection on one page must not abort the whole check.
        return _failed(entry, None, f"{type(exc).__name__}: {exc}")

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
        "content_sha256": content_digest(text),
        "content_hash_basis": CONTENT_HASH_BASIS,
        "markers": _markers(text),
        "error": None,
        "interpretation": (
            "sha256 covers the raw HTTP body; content_sha256 ignores script, style and "
            "comment blocks. A change means the page changed. It does not identify a "
            "duty-rate amendment."
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
        elif prior.get("content_sha256") and observation.get("content_sha256"):
            if prior["content_sha256"] == observation["content_sha256"]:
                observation["change"] = "unchanged_since_baseline"
                if prior.get("sha256") != observation.get("sha256"):
                    observation["raw_bytes_differ_in_scripts_or_markup_only"] = True
            else:
                observation["change"] = "page_content_changed"
                observation["baseline_content_sha256"] = prior["content_sha256"]
        elif prior.get("sha256") == observation.get("sha256"):
            observation["change"] = "unchanged_since_baseline"
        else:
            # The baseline predates content hashing, so only raw bytes can be compared.
            observation["change"] = "page_bytes_changed"
            observation["baseline_sha256"] = prior.get("sha256")
            observation["baseline_has_no_content_hash"] = True

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
        "changed_count": sum(
            1 for item in observations if item["change"] in ("page_bytes_changed", "page_content_changed")
        ),
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
