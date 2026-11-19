"""Filesystem locations for bundled data and the web client."""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
DATA_DIR = REPO_ROOT / "data"
WEB_DIR = REPO_ROOT / "web"
MONITOR_DIR = DATA_DIR / "monitor"

CHAPTERS_PATH = DATA_DIR / "chapters.json"
DOCUMENTS_PATH = DATA_DIR / "documents.json"
SOURCES_PATH = DATA_DIR / "sources.json"
WATCHLIST_PATH = DATA_DIR / "watchlist.json"
MONITOR_LATEST_PATH = MONITOR_DIR / "latest.json"
MONITOR_BASELINE_PATH = MONITOR_DIR / "baseline.json"
