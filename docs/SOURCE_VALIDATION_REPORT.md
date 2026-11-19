# Source validation report

**Read on:** 13 November 2026  
**Jurisdiction in scope:** Canada, federal public sources only  
**Live tariff integration:** none

This report records what was actually opened, what was stored, and what TariffWire must not be treated as. It is not a legal opinion and not a CBSA ruling.

## 1. Repository audit

| Item | Finding |
| --- | --- |
| Starting commit | `a3d1207`, message "Initial commit" |
| Starting tree | `README.md` only: "Regulatory updates, import/export compliance and up-to-date tariff information source" |
| Application code | None |
| Tariff data | None |
| Update job | None |
| Tests | None |

The README stated an intention. Nothing in the tree implemented it. There was no hidden data file, scraper, or integration to review.

## 2. How sources were checked

Public HTTPS pages were fetched without an account. The CARM Client Portal was not opened. No CBSA internal system, broker portal, or paid database was used. Where a page was summarized, the summary is limited to sentences read on that page. Where only a title or a reachability check was done, the catalogue says so.

On 13 November 2026 at 00:23:47 UTC the page-fingerprint check requested 14 watchlist URLs. All 14 returned HTTP 200. That check stored a SHA-256 of each body. It did not store the bodies. The Department of Finance counter-tariff page was about 1.5 MB because the product table is on the page; the table was not copied into this repository.

Chapter titles were parsed from the T2026-2 HTML index. The parser keeps a row only when that row is in the HTML. It rejects an index that is not chapters 1 through 99, so a broken parse cannot silently drop a chapter and still be saved.

## 3. Authority, in the order a rate should be read

These are separate texts. TariffWire does not collapse them into one "current rate."

1. **The legal instrument.** The Customs Tariff, S.C. 1997, c. 36, consolidated on Justice Laws. On 13 November 2026 that page said the Act is current to 2026-10-19 and was last amended on 2026-09-01. "Current to" is the consolidation currency date, not the effective date of every provision. Orders such as SOR/2026-186 are regulations under that Act. Justice Laws said SOR/2026-186 is current to 2026-10-19 and was last amended on 2026-09-08.
2. **The Canada Gazette.** `gazette.gc.ca` is where those orders are published. The homepage responded. No Gazette issue was copied.
3. **The CBSA departmental consolidation.** The CBSA publishes the working tariff files and says they are updated at least once a year, or whenever necessary, and that it issues a customs notice when there is an amendment. The 2026 menu listed T2026-2 effective 2026-09-01, T2026-1 effective 2026-08-06, and T2026 effective 2026-01-01. A cover read from `01-99-2026-eng.pdf` is labelled T2026(E) and says the departmental consolidation is prepared for convenience of reference only and has no official sanction. That cover was not the T2026-2 file. The same warning should be assumed to matter for any consolidation edition until the edition in front of the reader is checked.
4. **Customs Notices.** The CBSA says notices tell clients about proposed changes and are not an ongoing reference. Ongoing material is moved into D-memoranda. A notice can explain an order. It is not the order.
5. **Departmental pages that describe themselves in two ways.** The Department of Finance counter-tariff page says it remains the authoritative source for its complete list of U.S. products, including tariff items, effective dates, and rates, and that the list was updated as of 26 August 2026 with effect from 12:01 a.m. on 8 September 2026. The same page says the consolidated list is prepared for information purposes only and has no official sanction, that the HS headings are illustrative, and that the list should be read with the Schedule to the Customs Tariff. Both sentences are on the page. This project copies neither the table nor a line rate.
6. **Rulings.** An advance ruling for tariff classification is binding between the CBSA and the person to whom it is issued, on the conditions the CBSA states. A TariffWire packet is not a ruling. Memorandum D11-11-3 (Ottawa, 21 October 2024) describes the program under paragraph 43.1(1)(c) of the Customs Act and quotes the regulation that an application shall be made not less than 120 days before the proposed date of importation. The memorandum says a ruling is optional. It also mentions the CARM Client Portal as a channel. This project does not connect to CARM.

The CBSA classification guide says it does not replace the legislation, the regulations, or the D-memoranda, and that its examples are for information only. Its numbering page uses 9507.90.10.00 to show how a 10-digit number is built, and says the first two digits indicate the chapter. TariffWire uses that only to open a chapter when a user types a number. It does not check that the rest of the number exists.

## 4. What was stored

| Stored | Source | Retrieved | What it is not |
| --- | --- | --- | --- |
| 99 chapter titles, section titles, index effective dates, HTML and PDF links | CBSA T2026-2 chapter index | 2026-11-13 | Headings, legal notes, tariff items, duty rates |
| Bibliographic records for the Act, SOR/2026-186, selected CBSA guides, D11-11-3, Customs Notices 26-22 and 26-23, the notices index, the SIMA measures page, the Finance list page, Global Affairs controls and the agreements catalogue, the Gazette homepage, the CITT homepage, and the BIS contact page | The pages linked from `data/documents.json` | 2026-11-13 | Substitutes for those pages |
| SHA-256 fingerprints | The 14 URLs in `data/watchlist.json` | 2026-11-13 00:23:47 UTC | A parsed amendment feed |

Every stored government URL is on a `gc.ca` or `canada.ca` host. Third-party APIs have no URL in the catalogue because they were not used.

## 5. What was deliberately not stored

- The Finance Canada line-level counter-tariff table, including every tariff item and rate on that page.
- The schedules to SOR/2026-186.
- Any MFN, preferential, or general duty rate from the Customs Tariff.
- The SIMA measures-in-force rows. The CBSA page says that if the list and a finding or order disagree, the finding or order takes precedence.
- Individual D10 commodity memoranda. Only the series index was opened.
- CITT case headlines. They change, and copying one would look like a case status.
- WCO Harmonized System Explanatory Notes. They are not a free Canadian legal text and were not reproduced.
- TradeFacts.io and any similar commercial tariff API. They are not the CBSA, Justice Laws, or the Gazette.
- CARM account data, rulings filed through CARM, and any system that requires a credential.

## 6. Disagreements left unresolved

### CPTPP and the United Kingdom

Customs Notice 26-22, dated Ottawa, 1 September 2026 and updated 16 September 2026, says the CPTPP enters into force for the United Kingdom on 1 September 2026, and that T2026-2 reflects the Comprehensive and Progressive United Kingdom Tariff (CPUKT), treatment code 35, for the United Kingdom, the Channel Islands, and the Isle of Man.

The Global Affairs Canada agreements catalogue, read the same day, still described the CPTPP country grouping as not yet in force for the United Kingdom. It listed the Canada-United Kingdom Trade Continuity Agreement as in force since 1 April 2021. The catalogue says its treaty texts are for information only and points readers to the Canada Treaty Series.

TariffWire shows both statements when a description mentions the United Kingdom or the CPTPP. It does not decide which tariff treatment applies, and it does not show a CPUKT rate.

Notice 26-22 also said, in paragraph 4, that T2026-2 was being published in HTML and Access only and that the PDF would follow, and in paragraph 5 that all formats were available as of 16 September 2026. The CBSA 2026 menu, read on 13 November 2026, listed a T2026-2 PDF. The menu is the later publication page. This project still does not parse that PDF.

### Outside-Canada BIS telephone number

The BIS contact page and Customs Notice 26-22 both print toll-free 1-800-461-9999 and TTY 1-866-335-3237.

They do not print the same outside-Canada number. The notice prints 1-204-983-3550 or 1-506-636-5064. The contact page, retrieved 13 November 2026, prints 1-204-983-3500 and does not print the 506 number. The product tells the reader to use the contact page. The contact page that day also said live agents are available Monday to Friday, 8 am to 4 pm local time in Canada and the United States, closed on federal statutory holidays, and that inquiry volume was higher than normal. Those hours are a retrieval-date statement, not a promise.

## 7. Retrieval approach that is reliable enough for this stage

There is no CBSA developer API on the tariff menu. The machine-readable file the CBSA offers is a Microsoft Access database inside a zip, beside HTML chapters and PDFs. A responsible update path is:

1. Pin an edition (today, T2026-2, effective date printed as 2026-09-01).
2. Record the URL, the retrieval time, and a hash of the file before parsing it.
3. Parse only after the edition token in the file matches the pin. If it does not, stop and show the mismatch.
4. Keep the previous edition readable. The menu still publishes T2026-1 and T2026.
5. Never fill a missing cell with a guessed rate. A missing parse is a gap.
6. Show the consolidation warning with every rate that eventually comes from a departmental file.
7. Join changes to a Gazette order or a customs notice by citation, not by assuming that a changed HTML file and a notice are the same amendment.
8. Re-fetch on a schedule, but label the result as a page check until a structured diff exists.

The on-demand fingerprint in this repository is step 8's honest minimum. It is not step 3.

## 8. Pages confirmed in the fingerprint

All of these returned HTTP 200 on the check above. Markers below are phrases found in the page text on that run.

| Page | Marker observed on that run |
| --- | --- |
| CBSA 2026 tariff menu | T2026-2, T2026-1, T2026 |
| T2026-2 chapter index | T2026-2 |
| Customs Tariff on Justice Laws | Act current to 2026-10-19; last amended on 2026-09-01 |
| SOR/2026-186 | Regulations are current to 2026-10-19; last amended on 2026-09-08 |
| Customs Notice 26-22 | T2026-2 and CPUKT |
| Customs notices index, Notice 26-23, rulings overview, D11-11-3, SIMA list, Finance list, Global Affairs catalogue, BIS contact, tariff home | HTTP 200; no extra marker is claimed |

A later run that reports `page_bytes_changed` means those bytes changed. It does not name the amendment. Re-read the page.

## 9. Display rules this build follows

Every chapter and document screen shows the publisher, jurisdiction (Canada), the retrieval date, and a labelled date rather than one undifferentiated "as of." When a page did not state a single effective date, the screen says that. Classification and duty are shown as not determined. The banner on every screen says the tool is not a customs determination.
