# TariffWire

Informational reading room for public Canadian import and export sources.

TariffWire is not the Canada Border Services Agency, not a broker, and not a system of record. It does not assign a tariff classification, an origin, a permit, or a duty rate. A result is a pointer to a public page, with the date that page was read and a statement of what was not decided.

## What was here

The repository started as a one-line README (`a3d1207`). There was no application, no tariff data, and no updater. This tree is the first working slice.

## What this slice does

- Searches the CBSA T2026-2 chapter titles and a small catalogue of public instruments.
- Opens a mobile-friendly record that shows jurisdiction, the kind of date (published, revised, effective, or consolidation currency), the retrieval date, and a link to the official page.
- Builds a classification research packet. The packet can point at chapter titles that share words with a description. It always stays at high uncertainty, always requires professional review, and leaves classification and duty fields empty.
- Surfaces two disagreements that were visible on 13 November 2026 instead of picking a winner: CPTPP status for the United Kingdom, and the CBSA's outside-Canada telephone number.
- Fingerprints a fixed list of public pages. A hash change means the page bytes changed. It does not mean a duty rate was parsed.

Duty tables, tariff-item text, SIMA measure rows, and the Finance Canada counter-tariff table are not stored. Commercial tariff APIs, the CARM Client Portal, and the WCO Explanatory Notes are not used.

## Run it

```bash
PYTHONPATH=src python3 -m tariffwire serve
```

Then open <http://127.0.0.1:8765>. Other commands:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m tariffwire search "coffee"
PYTHONPATH=src python3 -m tariffwire classify "chocolate and a ceramic mug set"
PYTHONPATH=src python3 -m tariffwire refresh-index
PYTHONPATH=src python3 -m tariffwire monitor
```

`refresh-index` re-reads the public CBSA chapter index and refuses to write a file that is not chapters 1 through 99. `monitor` fetches only the URLs in `data/watchlist.json`.

## Read these before treating any number as current

- [Source validation report](docs/SOURCE_VALIDATION_REPORT.md) — what was opened, what was copied, and what was refused.
- [Roadmap](docs/ROADMAP.md) — the change-monitoring design, the classification safeguards, and the work that is still unsafe to pretend is done.

Chapter titles in `data/chapters.json` are copied from the CBSA index and remain Crown copyright. They are a finding aid for that edition, retrieved 2026-11-13.
