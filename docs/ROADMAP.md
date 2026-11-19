# Roadmap

The priority is to stay accurate while the corpus grows. A feature that would display a rate, a 10-digit classification, or a permit answer before the source is pinned and cited is not a candidate, however useful it would look.

## Safeguards that stay in force

These are product rules, not a later enhancement.

- A research packet is not a tariff classification. `tariff_classification` and `duty_rate` stay null. The code refuses to start the server path if those fields are filled or if uncertainty is lowered.
- Chapter suggestions come from official T2026-2 titles, plus a short editorial word list (for example "chocolate" to the word "cocoa", which is the word in the chapter title). The list is labelled as a search aid. It is not a legal note. Words that are not in a title, such as "laptop" or "mug", do not get a guessed chapter.
- Sets, kits, parts, mixtures, and used goods always raise a review trigger. The General Rules are not applied here. The user is sent to the Customs Tariff and the CBSA guide.
- Goods that are often named in surtax orders, SIMA measures, quotas, or permit regimes (steel, aluminum, dairy, apparel, vehicles, and the others listed in the code) get a warning to check those lists. The warning does not say the goods are on a list.
- A number typed by the user is echoed as unverified. The first two digits open the chapter the CBSA numbering guide says they indicate. The rest of the number is not confirmed, because the schedule is not stored.
- United States origin adds links to Customs Notice 26-23, SOR/2026-186, and the Finance list, and still does not pick a rate.
- United Kingdom or CPTPP wording shows the unresolved conflict between Customs Notice 26-22 and the Global Affairs catalogue.
- Professional review is required on every packet. The route to a number that can be relied on is a CBSA advance ruling under Memorandum D11-11-3, or a qualified customs professional applying the legal text. Telephone information from the Border Information Service is not presented as a ruling.
- Screens show jurisdiction, a labelled date, and the retrieval date. Consolidation currency ("Act current to") is not displayed as an effective date.
- The interface does not use the Canada wordmark or the Government of Canada header. It is an unofficial reading room.

## Change monitoring

### What is built

`data/watchlist.json` is a fixed list of public HTTPS URLs. `python -m tariffwire monitor`, and the "Check the public pages now" button, fetch only that list. For each page the tool stores:

- HTTP status
- final URL
- byte length
- SHA-256 of the body
- a few literal phrases when they are present (edition tokens such as T2026-2, "Act current to", "last amended on", "Regulations are current to", SOR numbers, CPUKT)

The first successful save is the baseline. A later save compares hashes. The states are `unchanged_since_baseline`, `page_bytes_changed`, `check_failed`, and `baseline_created`. Nothing in those states is a duty-rate delta.

The baseline in this branch was taken on 13 November 2026 at 00:23:47 UTC. Fourteen pages returned HTTP 200.

### What a real amendment monitor still requires

1. **Edition pin.** Download the CBSA HTML chapter, the PDF, or the Access zip for a named edition. Hash the file. Refuse to parse it if the edition token differs from the pin.
2. **Structured extract.** Parse tariff items into records with edition id, chapter, item, description, unit, and each tariff-treatment column, all copied from that file. Empty cells stay empty.
3. **Diff.** Compare item keys between two pins. Emit added, removed, and changed fields. Quote both values and both edition ids. Do not describe a hash change of the Finance HTML page as a list of amended items.
4. **Citation join.** When a Canada Gazette order or a CBSA customs notice is published, store the instrument as its own record. Link a tariff diff to that instrument only when the instrument names the items or the edition. Otherwise show the diff and the notice as neighbours, not as cause and effect.
5. **Notices versus ongoing text.** Customs notices expire as reference material. A monitor should flag a notice that disappears from the index, and should not keep serving its body as current policy after the CBSA has folded it into a D-memorandum or an order.
6. **Failure behaviour.** A failed fetch keeps the last good pin on screen and says the check failed. It does not fall back to a model, a commercial API, or the previous rate without the date.
7. **No authenticated systems.** CARM, ACE filing, and any credentialed CBSA system stay out of the monitor.

Until steps 1 to 3 exist, the product must keep saying that it does not have live tariff data.

## Priority order

### P0 — In this branch

- Source registry with retrieval dates and an explicit "not used" list.
- Search over chapter titles and the curated public documents.
- Research packet that cannot emit a classification or a rate.
- Mobile layout: large type, 44 px targets, no hover-only actions, hash routes for search, chapters, documents, the research aid, sources, and the page check.
- Tests that fail if a packet gains a rate, if a chapter is dropped from the index parse, or if a stored document pairs a tariff item with a percentage.
- This report and the validation notes above.

### P1 — Schedule ingest, still not a calculator

Parse one pinned CBSA edition into tariff items with citations. Show a rate only next to the edition, the column name (for example the treatment code printed in the file), the retrieval hash, and the consolidation warning. If the parse is incomplete, show the gap. Do not compute value for duty, surtax, SIMA duty, excise, or GST/HST.

Prefer the CBSA HTML or Access file over a third-party API. Record the file hash in the same way the chapter index records `source_sha256`.

### P2 — Amendment diffs tied to instruments

Diff two pinned editions. Separately ingest new Customs Notices and Gazette orders as documents with their own dates. Show them on the change screen. Link a diff line to an instrument only on a demonstrated citation.

### P3 — Published rulings as citations, not as answers

Where the CBSA has published a ruling with the recipient's consent, index the ruling number, the date, the goods description the CBSA used, and the URL. A search hit must say the ruling binds the recipient on the CBSA's conditions, not the person searching. Do not scrape CARM to obtain unpublished rulings.

### P4 — Other government requirements as a separate layer

Global Affairs controls, CFIA, Health Canada, Environment and Climate Change Canada, and the other D19 regimes are permits and restrictions, not tariff classification. Add them as requirement checklists that link to the official notice and never say "no permit is required" merely because this catalogue is silent.

### P5 — French

Federal texts are published in both official languages. The reading room should offer French titles and links from the same CBSA and Justice Laws pages, without translating a rate or a legal note by machine and presenting the translation as the law.

### P6 — Work for a person who will sign the entry

Audit log of which edition and which retrieved_at a human looked at. Export a research packet as a source list a broker can attach to a working file. Still no declaration, no CARM submission, and no "accepted classification" state inside TariffWire.

## Explicitly out of scope

- Logging into CARM or any protected CBSA system.
- Presenting TariffWire as the Government of Canada.
- Filling an unknown rate with a model, a similar heading, or a commercial API.
- Treating a page-hash change as proof of which duty changed.
