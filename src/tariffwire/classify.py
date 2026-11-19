"""Build a source-backed research packet without making a classification.

Title overlap and a short editorial expansion list are retrieval aids.
They are not General Rules, legal notes, or CBSA rulings. The packet keeps
classification, duty, origin, permit, SIMA, and surtax fields empty.
"""

from __future__ import annotations

import re
from typing import Any

from tariffwire.catalog import (
    chapter_by_number,
    chapters_catalog,
    document_by_id,
    normalize,
    tokens,
)

# Editorial retrieval words. None of these is a tariff legal note.
EXPANSIONS: dict[str, list[str]] = {
    "automobile": ["vehicle", "vehicles"],
    "automobiles": ["vehicle", "vehicles"],
    "car": ["vehicle", "vehicles"],
    "cars": ["vehicle", "vehicles"],
    "truck": ["vehicle", "vehicles"],
    "trucks": ["vehicle", "vehicles"],
    "aluminium": ["aluminum"],
    "tshirt": ["apparel", "clothing"],
    "t-shirt": ["apparel", "clothing"],
    "shirt": ["apparel", "clothing"],
    "shirts": ["apparel", "clothing"],
    "clothes": ["apparel", "clothing"],
    "shoe": ["footwear"],
    "shoes": ["footwear"],
    "boot": ["footwear"],
    "boots": ["footwear"],
    "cheese": ["dairy"],
    "milk": ["dairy"],
    "butter": ["dairy"],
    "yogurt": ["dairy"],
    "yoghurt": ["dairy"],
    "chocolate": ["cocoa"],
    "wine": ["beverages"],
    "beer": ["beverages"],
}

_CODE_RE = re.compile(
    r"\b(\d{4})(?:\.(\d{2}))(?:\.(\d{2}))?(?:\.(\d{2}))?\b|\b(\d{10})\b"
)
_CHAPTER_RE = re.compile(r"\b(?:chapter|ch)\s*0*(\d{1,2})\b", re.IGNORECASE)

_REVIEW_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\b(set|sets|kit|kits|assortment|assortments|gift)\b", re.I),
        "The description uses set, kit, assortment, or gift language. Sets are resolved with the General Rules and the legal notes, which this tool does not apply.",
    ),
    (
        re.compile(r"\b(part|parts|component|components|accessory|accessories)\b", re.I),
        "Parts and accessories are not identified by matching a finished article's name to a chapter title.",
    ),
    (
        re.compile(r"\b(mixture|mixtures|blend|blends|composite|composites)\b", re.I),
        "Mixtures and composite goods need the legal notes and the General Rules. Title overlap does not resolve them.",
    ),
    (
        re.compile(r"\b(used|second[- ]hand|refurbished|worn)\b", re.I),
        "Condition can change the legal analysis, including special classification provisions. This tool does not apply those provisions.",
    ),
    (
        re.compile(
            r"\b(steel|aluminum|aluminium|dairy|cheese|sugar|apparel|textile|vehicle|automobile|lumber|softwood)\b",
            re.I,
        ),
        "Goods of this kind are often named in surtax orders, trade-remedy measures, tariff-rate quotas, or permit regimes. This packet has not checked those lists for this description.",
    ),
]

_RATE_ASK_RE = re.compile(
    r"\b(duty|duties|rate|rates|how much|landed cost|tariff rate|surtax rate)\b",
    re.I,
)
_CLASSIFY_ASK_RE = re.compile(
    r"\b(classify|classification|hs code|tariff (?:item|code|number)|what code)\b",
    re.I,
)
_US_RE = re.compile(
    r"\b(united states|u\.s\.a?\.?|usa|american)\b",
    re.I,
)
_UK_RE = re.compile(
    r"\b(united kingdom|u\.k\.|uk|great britain|cptpp)\b",
    re.I,
)

DISCLAIMER = (
    "Informational research aid only. This is not a tariff classification, "
    "a duty calculation, an origin or value determination, a permit decision, "
    "or a ruling of the Canada Border Services Agency. Do not copy it onto a "
    "commercial accounting declaration."
)


def _expanded_terms(description: str) -> tuple[list[str], list[dict[str, Any]]]:
    raw_tokens = tokens(description)
    expansions: list[dict[str, Any]] = []
    terms = list(raw_tokens)
    folded = normalize(description)
    for key, values in EXPANSIONS.items():
        key_norm = normalize(key)
        if re.search(rf"\b{re.escape(key_norm)}\b", folded) and values:
            expansions.append({"from": key, "to": values, "status": "editorial_search_aid"})
            terms.extend(values)
    # Preserve order and drop duplicates.
    unique = list(dict.fromkeys(terms))
    return unique, expansions


def _candidate(chapter: dict[str, Any], matched: list[str]) -> dict[str, Any]:
    catalog = chapters_catalog()
    return {
        "chapter": chapter["chapter"],
        "title": chapter["title"],
        "section": chapter["section"],
        "section_title": chapter["section_title"],
        "basis": "official_chapter_title_overlap",
        "confidence": "not_a_classification",
        "matched_terms": matched,
        "effective_date_on_index": chapter["effective_date"],
        "edition": catalog["edition"],
        "html_url": chapter["html_url"],
        "pdf_url": chapter["pdf_url"],
        "index_url": catalog["index_url"],
    }


def _citation(document_id: str) -> dict[str, Any] | None:
    document = document_by_id(document_id)
    if not document:
        return None
    return {
        "id": document["id"],
        "title": document["title"],
        "url": document["url"],
        "publisher": document["publisher"],
        "retrieved_at": document["retrieved_at"],
        "jurisdiction": document["jurisdiction"],
    }


def _user_code(description: str) -> dict[str, Any] | None:
    match = _CODE_RE.search(description or "")
    if not match:
        return None
    if match.group(5):
        digits = match.group(5)
        display = f"{digits[:4]}.{digits[4:6]}.{digits[6:8]}.{digits[8:10]}"
    else:
        parts = [match.group(1), match.group(2), match.group(3), match.group(4)]
        display = ".".join(part for part in parts if part)
        digits = "".join(part for part in parts if part)
    chapter_number = int(digits[:2])
    chapter = chapter_by_number(chapter_number)
    return {
        "as_entered": match.group(0),
        "normalized": display,
        "unverified": True,
        "exists_in_stored_schedule": None,
        "reason": (
            "The number was supplied in the description. This build does not store "
            "tariff items, so it cannot confirm that the number exists or is current."
        ),
        "chapter_pointer": (
            {
                "chapter": chapter["chapter"],
                "title": chapter["title"],
                "html_url": chapter["html_url"],
                "basis": "The CBSA numbering guide says the first two digits indicate the chapter. Opening that chapter does not confirm this number.",
            }
            if chapter
            else None
        ),
    }


def research_packet(
    description: str,
    *,
    materials: str = "",
    function: str = "",
    condition: str = "",
    origin: str = "",
    importation: str = "",
) -> dict[str, Any]:
    """Return a packet that reports uncertainty and never fills a rate or code."""
    combined = " ".join(
        part.strip()
        for part in (description, materials, function, condition, origin, importation)
        if part and part.strip()
    )
    catalog = chapters_catalog()
    reasons = [
        "No section notes, chapter notes, headings, tariff items, or duty rates were applied.",
        "Chapter title overlap is a way to open the official index. It is not classification under the General Rules.",
    ]
    triggers: list[str] = []
    citations = [
        item
        for item in (
            _citation("cbsa-classification-guide"),
            _citation("cbsa-classification-numbering"),
            _citation("cbsa-advance-rulings"),
            _citation("cbsa-d11-11-3"),
            _citation("cbsa-t2026-2-chapter-index"),
        )
        if item
    ]
    conflicts: list[dict[str, Any]] = []

    if not (description or "").strip():
        return _finish(
            status="need_more_information",
            reasons=["A goods description is required before any chapter title can be compared."] + reasons,
            triggers=["Describe the goods, their materials, their function, and whether they are a set, part, or mixture."],
            candidates=[],
            citations=citations,
            conflicts=conflicts,
            expansions=[],
            user_code=None,
            catalog=catalog,
        )

    for pattern, message in _REVIEW_RULES:
        if pattern.search(combined):
            triggers.append(message)

    if _RATE_ASK_RE.search(combined):
        triggers.append(
            "A duty or rate was requested. This tool does not store or calculate duty, surtax, excise, GST/HST, or SIMA duty."
        )
    if _CLASSIFY_ASK_RE.search(description):
        triggers.append(
            "A classification number was requested. This tool does not assign one. A CBSA advance ruling, or a qualified customs professional applying the legal text, is the route to a number that can be relied on."
        )

    if origin.strip() or _US_RE.search(combined):
        triggers.append(
            "Origin was mentioned or inferred from the text. Origin and preferential entitlement are separate from classification. This packet does not decide either one."
        )
        if _US_RE.search(f"{origin} {combined}"):
            triggers.append(
                "Certain goods originating in the United States are named in the United States Surtax Order (2026). This packet does not decide whether these goods are listed or which rate in that Order would apply."
            )
            for document_id in ("cn-26-23", "sor-2026-186", "finance-us-counter-tariffs"):
                citation = _citation(document_id)
                if citation:
                    citations.append(citation)
        else:
            citation = _citation("gac-agreements-catalogue")
            if citation:
                citations.append(citation)

    if _UK_RE.search(combined):
        conflicts.append(
            {
                "topic": "CPTPP treatment of the United Kingdom",
                "level": "unresolved",
                "observation": (
                    "On 2026-11-13, Customs Notice 26-22 said the CPTPP enters into force for the "
                    "United Kingdom on 2026-09-01 and that T2026-2 reflects CPUKT tariff treatment code 35. "
                    "The Global Affairs Canada agreements catalogue, read the same day, still described "
                    "the CPTPP country grouping as not yet in force for the United Kingdom, and listed "
                    "the Canada-UK Trade Continuity Agreement as in force since 2021-04-01. "
                    "This tool does not choose between those public statements."
                ),
            }
        )
        for document_id in ("cn-26-22", "gac-agreements-catalogue"):
            citation = _citation(document_id)
            if citation:
                citations.append(citation)

    user_code = _user_code(description)
    terms, expansions = _expanded_terms(combined)
    by_chapter: dict[int, list[str]] = {}
    for chapter in catalog["chapters"]:
        haystack = normalize(chapter["title"])
        matched = [term for term in terms if re.search(rf"\b{re.escape(term)}\b", haystack)]
        if matched:
            by_chapter[chapter["chapter"]] = list(dict.fromkeys(matched))

    named = _CHAPTER_RE.search(description or "")
    if named:
        number = int(named.group(1))
        chapter = chapter_by_number(number)
        if chapter:
            by_chapter.setdefault(number, [])
            if "chapter-number" not in by_chapter[number]:
                by_chapter[number].append("named chapter number")

    candidates = [
        _candidate(chapter_by_number(number), matched)  # type: ignore[arg-type]
        for number, matched in sorted(by_chapter.items())
        if chapter_by_number(number)
    ]
    sections = {item["section"] for item in candidates}
    if not candidates:
        reasons.append(
            "No stored T2026-2 chapter title contains the significant words in this description. No chapter was guessed."
        )
        triggers.append(
            "Add material, construction, and function in the words used by the Customs Tariff, or go to the full schedule and the advance-ruling program. Do not treat silence from this index as a classification."
        )
    elif len(sections) > 1:
        reasons.append(
            f"Title overlap touches {len(sections)} sections ({', '.join(sorted(sections))}). The description is ambiguous at chapter-title level."
        )
        triggers.append(
            "More than one section matches. Do not pick the highest-scoring title. Read the legal notes for each candidate in the official schedule."
        )
    else:
        reasons.append(
            "Title overlap is confined to one section, and it is still only title overlap."
        )

    if user_code:
        reasons.append(user_code["reason"])

    status = "not_a_classification"
    if len(sections) > 1:
        status = "ambiguous_title_overlap"
    elif not candidates:
        status = "no_title_overlap"

    return _finish(
        status=status,
        reasons=reasons,
        triggers=triggers,
        candidates=candidates,
        citations=_unique_citations(citations),
        conflicts=conflicts,
        expansions=expansions,
        user_code=user_code,
        catalog=catalog,
    )


def _unique_citations(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for citation in citations:
        if citation["id"] in seen:
            continue
        seen.add(citation["id"])
        unique.append(citation)
    return unique


def _finish(
    *,
    status: str,
    reasons: list[str],
    triggers: list[str],
    candidates: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    expansions: list[dict[str, Any]],
    user_code: dict[str, Any] | None,
    catalog: dict[str, Any],
) -> dict[str, Any]:
    packet = {
        "product": "TariffWire",
        "kind": "classification_research_packet",
        "status": status,
        "disclaimer": DISCLAIMER,
        "uncertainty": {"level": "high", "reasons": reasons},
        "professional_review_required": True,
        "review_triggers": triggers,
        "candidate_chapters": candidates,
        "search_expansions_used": expansions,
        "search_expansion_status": "Editorial retrieval aid only. Not a legal note and not from the Customs Tariff.",
        "user_supplied_code": user_code,
        "tariff_classification": None,
        "duty_rate": None,
        "origin_determination": None,
        "value_for_duty_determination": None,
        "permit_determination": None,
        "sima_determination": None,
        "surtax_determination": None,
        "not_determined": [
            "10-digit tariff classification",
            "customs duty rate",
            "preferential tariff treatment",
            "origin",
            "value for duty",
            "surtax",
            "SIMA duty",
            "GST/HST or excise",
            "import or export permits",
            "other government department requirements",
        ],
        "next_steps": [
            "Open the linked CBSA chapter HTML and read the section notes, chapter notes, and headings.",
            "Read the General Rules for the Interpretation of the Harmonized System in the Customs Tariff, using the CBSA guide as an explanation rather than as a substitute.",
            "If a preferential rate, surtax, SIMA measure, or permit may be involved, read the cited instrument itself.",
            "For a number that can be relied on, request a CBSA advance ruling under the program described in Memorandum D11-11-3, or have a qualified customs professional prepare the classification.",
            "Confirm the edition and effective date on the CBSA site before accounting for the goods. This packet is tied to the stored index retrieval date.",
        ],
        "edition": {
            "id": catalog.get("edition"),
            "index_url": catalog.get("index_url"),
            "index_retrieved_at": catalog.get("retrieved_at"),
            "live_tariff_integration": False,
        },
        "citations": citations,
        "conflicts": conflicts,
        "jurisdiction": "Canada",
    }
    _guard(packet)
    return packet


def _guard(packet: dict[str, Any]) -> None:
    """Fail closed if a future change starts emitting a determination."""
    if packet["tariff_classification"] is not None or packet["duty_rate"] is not None:
        raise RuntimeError("Refusing to emit a classification or duty rate")
    if packet["uncertainty"]["level"] != "high":
        raise RuntimeError("Refusing to emit a classification packet below high uncertainty")
    if packet["professional_review_required"] is not True:
        raise RuntimeError("Professional review flag was turned off")
    for candidate in packet["candidate_chapters"]:
        if candidate.get("confidence") != "not_a_classification":
            raise RuntimeError("Candidate confidence must stay not_a_classification")
        if "duty" in candidate or "rate" in candidate:
            raise RuntimeError("Candidate chapters cannot carry a rate")
