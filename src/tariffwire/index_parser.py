"""Parse the public CBSA chapter-by-chapter Customs Tariff index.

The parser copies titles, effective dates, and links that are present in the
HTML. It does not invent missing chapters, duty rates, or tariff items.
"""

from __future__ import annotations

import hashlib
import html
import re
from datetime import date
from typing import Any
from urllib.parse import urljoin

CBSA_ORIGIN = "https://www.cbsa-asfc.gc.ca"
INDEX_URL = (
    "https://www.cbsa-asfc.gc.ca/trade-commerce/tariff-tarif/"
    "2026/html/tblmod-2-eng.html"
)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_EDITION_RE = re.compile(r"\b(T20\d{2}(?:-\d+)?)\b")
_SECTION_RE = re.compile(
    r"<h3\b[^>]*>\s*Section\s+([IVXLC]+)\s*:\s*(.*?)</h3>",
    re.IGNORECASE | re.DOTALL,
)
_TR_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
_TH_RE = re.compile(r"<th\b[^>]*>(.*?)</th>", re.IGNORECASE | re.DOTALL)
_TD_RE = re.compile(r"<td\b[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)
_CHAPTER_RE = re.compile(r"^Chapter\s+(\d+)\s+-\s+(.*)$", re.IGNORECASE)
_HREF_RE = re.compile(
    r'<a\b[^>]*href="([^"]+)"[^>]*>\s*(HTML|PDF)\b',
    re.IGNORECASE,
)


def _clean(fragment: str) -> str:
    text = _TAG_RE.sub(" ", fragment)
    text = html.unescape(text).replace("\xa0", " ")
    text = _WS_RE.sub(" ", text).strip()
    # Inline tags such as <i> sit against parentheses in the CBSA index.
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    return text


def _links(cell_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for href, kind in _HREF_RE.findall(cell_html):
        if href.startswith("#"):
            continue
        found[kind.lower()] = urljoin(CBSA_ORIGIN, href)
    return found


def parse_chapter_index(
    page_html: str,
    *,
    index_url: str = INDEX_URL,
    retrieved_on: str | None = None,
) -> dict[str, Any]:
    """Return edition metadata, preface rows, and chapter records."""
    h1_match = _H1_RE.search(page_html)
    h1 = _clean(h1_match.group(1)) if h1_match else ""
    edition_match = _EDITION_RE.search(h1)
    if not edition_match:
        raise ValueError(f"Could not read a Customs Tariff edition from h1: {h1!r}")

    sections: list[tuple[int, str, str]] = []
    for match in _SECTION_RE.finditer(page_html):
        sections.append((match.start(), match.group(1).upper(), _clean(match.group(2))))

    def section_at(position: int) -> tuple[str, str]:
        current = ("", "")
        for start, number, title in sections:
            if start < position:
                current = (number, title)
            else:
                break
        return current

    preface: list[dict[str, Any]] = []
    chapters: list[dict[str, Any]] = []
    seen: set[int] = set()
    for match in _TR_RE.finditer(page_html):
        row_html = match.group(1)
        headings = [_clean(fragment) for fragment in _TH_RE.findall(row_html)]
        cells = _TD_RE.findall(row_html)
        if len(headings) != 1 or len(cells) < 2:
            continue
        title = headings[0]
        effective_match = re.search(r"\d{4}-\d{2}-\d{2}", _clean(cells[0]))
        if not effective_match:
            continue
        effective = effective_match.group(0)
        links = _links(cells[1])
        chapter_match = _CHAPTER_RE.match(title)
        if not chapter_match:
            preface.append(
                {
                    "title": title,
                    "effective_date": effective,
                    "html_url": links.get("html"),
                    "pdf_url": links.get("pdf"),
                }
            )
            continue
        number = int(chapter_match.group(1))
        if number in seen:
            raise ValueError(f"Duplicate chapter {number} in Customs Tariff index")
        seen.add(number)
        section_number, section_title = section_at(match.start())
        if not section_number:
            raise ValueError(f"Chapter {number} appears before any section heading")
        chapters.append(
            {
                "chapter": number,
                "title": _clean(chapter_match.group(2)),
                "section": section_number,
                "section_title": section_title,
                "effective_date": effective,
                "html_url": links.get("html"),
                "pdf_url": links.get("pdf"),
            }
        )

    chapters.sort(key=lambda item: item["chapter"])
    return {
        "edition": edition_match.group(1),
        "index_title": h1,
        "index_url": index_url,
        "publisher": "Canada Border Services Agency",
        "jurisdiction": "Canada",
        "retrieved_at": retrieved_on or date.today().isoformat(),
        "source_sha256": hashlib.sha256(page_html.encode("utf-8")).hexdigest(),
        "contains_duty_rates": False,
        "contains_tariff_items": False,
        "caveat": (
            "Titles, dates, and links are copied from the CBSA chapter index for "
            "the named departmental-consolidation edition. The index is a finding "
            "aid. It is not the Schedule to the Customs Tariff and it does not "
            "state a duty rate."
        ),
        "preface": preface,
        "chapters": chapters,
    }


def require_complete_chapter_span(catalog: dict[str, Any]) -> None:
    """Reject a catalog that skips, repeats, or extends the chapter span."""
    numbers = [item["chapter"] for item in catalog["chapters"]]
    expected = list(range(1, 100))
    if numbers != expected:
        missing = [n for n in expected if n not in numbers]
        extra = [n for n in numbers if n not in expected]
        raise ValueError(f"Expected chapters 1-99. missing={missing} extra={extra}")
    for item in catalog["chapters"]:
        if not item.get("html_url") or not item.get("title") or not item.get("effective_date"):
            raise ValueError(f"Incomplete chapter record: {item.get('chapter')}")
        if "rate" in item or "duty" in item:
            raise ValueError("Chapter records must not carry duty fields")
