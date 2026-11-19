"""Load and search the bundled public-source catalogue."""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from typing import Any

from tariffwire.paths import CHAPTERS_PATH, DOCUMENTS_PATH, SOURCES_PATH

_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "goods",
    "import",
    "imported",
    "into",
    "item",
    "items",
    "nor",
    "not",
    "of",
    "on",
    "or",
    "product",
    "products",
    "the",
    "to",
    "with",
}


def _load(path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def chapters_catalog() -> dict[str, Any]:
    return _load(CHAPTERS_PATH)


@lru_cache(maxsize=1)
def documents_catalog() -> dict[str, Any]:
    return _load(DOCUMENTS_PATH)


@lru_cache(maxsize=1)
def sources_catalog() -> dict[str, Any]:
    return _load(SOURCES_PATH)


def clear_caches() -> None:
    chapters_catalog.cache_clear()
    documents_catalog.cache_clear()
    sources_catalog.cache_clear()


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _WS_RE.sub(" ", stripped).strip().lower()


def tokens(text: str) -> list[str]:
    return [token for token in _TOKEN_RE.findall(normalize(text)) if token not in _STOPWORDS and len(token) >= 3]


def chapter_by_number(number: int) -> dict[str, Any] | None:
    for item in chapters_catalog()["chapters"]:
        if item["chapter"] == number:
            return item
    return None


def document_by_id(document_id: str) -> dict[str, Any] | None:
    for item in documents_catalog()["documents"]:
        if item["id"] == document_id:
            return item
    return None


def source_by_id(source_id: str) -> dict[str, Any] | None:
    for item in sources_catalog()["sources"]:
        if item["id"] == source_id:
            return item
    return None


def _chapter_hit(chapter: dict[str, Any], *, score: int, reason: str, terms: list[str]) -> dict[str, Any]:
    catalog = chapters_catalog()
    return {
        "kind": "chapter",
        "id": f"chapter-{chapter['chapter']:02d}",
        "chapter": chapter["chapter"],
        "title": f"Chapter {chapter['chapter']} — {chapter['title']}",
        "chapter_title": chapter["title"],
        "section": chapter["section"],
        "section_title": chapter["section_title"],
        "score": score,
        "match_reason": reason,
        "matched_terms": terms,
        "jurisdiction": "Canada",
        "publisher": "Canada Border Services Agency",
        "edition": catalog["edition"],
        "effective_date": chapter["effective_date"],
        "effective_date_label": "Effective date printed on the chapter index row",
        "retrieved_at": catalog["retrieved_at"],
        "html_url": chapter["html_url"],
        "pdf_url": chapter["pdf_url"],
        "index_url": catalog["index_url"],
        "duty_rate": None,
        "tariff_classification": None,
        "limitation": catalog["caveat"],
    }


def _document_hit(document: dict[str, Any], *, score: int, reason: str, terms: list[str]) -> dict[str, Any]:
    return {
        "kind": "document",
        "id": document["id"],
        "title": document["title"],
        "score": score,
        "match_reason": reason,
        "matched_terms": terms,
        "jurisdiction": document["jurisdiction"],
        "publisher": document["publisher"],
        "instrument": document["instrument"],
        "published": document.get("published"),
        "revised": document.get("revised"),
        "effective": document.get("effective"),
        "date_labels": document.get("date_labels", {}),
        "retrieved_at": document["retrieved_at"],
        "url": document["url"],
        "summary": document["summary"],
        "duty_rate": None,
        "tariff_classification": None,
        "limitation": document["limitation"],
    }


def search(query: str, *, limit: int = 30) -> dict[str, Any]:
    """Search chapter titles and curated public-document records.

    A hit is a retrieval result. It is not a classification and it has no duty rate.
    """
    raw = (query or "").strip()
    folded = normalize(raw)
    query_tokens = tokens(raw)
    hits: list[dict[str, Any]] = []

    chapter_request = re.fullmatch(r"(?:chapter|ch)\s*0*(\d{1,2})", folded)
    if chapter_request:
        number = int(chapter_request.group(1))
        chapter = chapter_by_number(number)
        if chapter:
            hits.append(
                _chapter_hit(
                    chapter,
                    score=100,
                    reason="The query names this chapter number. The chapter title is from the CBSA index.",
                    terms=[str(number)],
                )
            )

    dotted_code = re.search(r"\b(\d{4})\.(\d{2})(?:\.(\d{2}))?(?:\.(\d{2}))?\b", raw)
    ten_digit = re.search(r"\b(\d{10})\b", raw)
    code_digits = None
    code_display = None
    if dotted_code:
        code_digits = "".join(part for part in dotted_code.groups() if part)
        code_display = dotted_code.group(0)
    elif ten_digit:
        code_digits = ten_digit.group(1)
        code_display = code_digits
    if code_digits and len(code_digits) >= 4:
        number = int(code_digits[:2])
        chapter = chapter_by_number(number)
        if chapter and not (chapter_request and int(chapter_request.group(1)) == number):
            hits.append(
                _chapter_hit(
                    chapter,
                    score=80,
                    reason=(
                        f"{code_display} was read as a classification-style number. The CBSA numbering "
                        "guide says the first two digits indicate the chapter. This search did not check "
                        "whether the full number exists."
                    ),
                    terms=[code_display or code_digits],
                )
            )

    for chapter in chapters_catalog()["chapters"]:
        if chapter_request and int(chapter_request.group(1)) == chapter["chapter"]:
            continue
        haystack = normalize(f"{chapter['title']} {chapter['section_title']}")
        hay_tokens = set(tokens(chapter["title"]))
        matched = [token for token in query_tokens if token in haystack]
        if not matched:
            continue
        unique = list(dict.fromkeys(matched))
        if hay_tokens and hay_tokens <= set(unique):
            score = 85
            reason = "Every significant word in the official chapter title appears in the query."
        elif len(unique) >= 2:
            score = 70
            reason = "More than one query word appears in the official chapter or section title."
        else:
            score = 55
            reason = "A query word appears in the official chapter or section title."
        hits.append(_chapter_hit(chapter, score=score, reason=reason, terms=unique))

    for document in documents_catalog()["documents"]:
        title_norm = normalize(document["title"])
        summary_norm = normalize(document.get("summary", ""))
        keyword_norm = normalize(" ".join(document.get("keywords", [])))
        matched = [
            token
            for token in query_tokens
            if token in title_norm or token in summary_norm or token in keyword_norm
        ]
        phrase_in_title = bool(folded) and folded in title_norm
        phrase_in_record = phrase_in_title or (bool(folded) and folded in f"{title_norm} {summary_norm}")
        if not matched and not phrase_in_record:
            continue
        unique = list(dict.fromkeys(matched))
        if phrase_in_title:
            score = 90
            reason = "The query matches this public document's title."
        elif len(unique) >= 2 or phrase_in_record:
            score = 65
            reason = "The query matches this public document's title, summary, or keywords."
        else:
            score = 45
            reason = "One query word matches this public document's title, summary, or keywords."
        hits.append(_document_hit(document, score=score, reason=reason, terms=unique))

    best = {}
    for hit in hits:
        key = (hit["kind"], hit["id"])
        if key not in best or hit["score"] > best[key]["score"]:
            best[key] = hit
    hits = list(best.values())
    hits.sort(key=lambda item: (-item["score"], item["kind"], item["title"]))
    trimmed = hits[:limit]
    return {
        "query": raw,
        "result_count": len(trimmed),
        "truncated": len(hits) > len(trimmed),
        "live_tariff_integration": False,
        "disclaimer": (
            "Search matches titles and curated descriptions of public documents. "
            "A match is not a tariff classification, an origin decision, or a duty rate."
        ),
        "results": trimmed,
    }
