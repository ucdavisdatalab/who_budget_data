# Changelog for Voluntary Contributions (long)

This document contains additional information about the 2026-08-18 and
2026-08-19 changes to create the voluntary contributions (long) table.


## What Was Changed

Relative to the original (wide) table.

* **Currency correction**: despite an earlier version of this README claiming
  the wide table was "inflation-adjusted to 2024," verification against raw
  sources showed the stored amounts are actually nominal, as-reported USD.
  `USD_2024_adjusted` here is a fresh forward computation, not a correction of
  a prior adjustment.

* **Footer/summary rows dropped**: PDF table footers that had leaked in as if
  they were contributor rows (e.g. "Grand Total", "Pass Through Funding",
  "Refunds To Donors") were removed.

* **World Bank region/income_group re-matched**: real member states whose name
  didn't match the World Bank's canonical spelling (e.g. `Kyrgyzstan` → Kyrgyz
  Republic, `Lao People's Democratic Republic` → Lao PDR, formal UN-style names
  like `Bahamas (The)` / `Iran (Islamic Republic Of)`) were mapped via the
  alias list in `wb_match.py`, using classifications from the [World Bank Data
  Help
  Desk](https://datahelpdesk.worldbank.org/knowledgebase/articles/906519-world-bank-country-and-lending-groups)
  (FY2025) where no matching in-data anchor existed. Non-country contributors
  (foundations, NGOs, companies) correctly retain a blank region/income_group.

* **Raw-CSV priority merge**: years with a raw per-year wide CSV in
  `WHO_funds/` (`WHO_voluntary_contributions_YYYY.csv`, covering 2010, 2012,
  2014-2024 — pdfplumber direct text extraction) have their
  `component`/`total_voluntary_contributions` categories replaced by that CSV's
  values, since direct text extraction is more reliable than the original
  image+Claude vision extraction.

* **The `assessed_contributions` reference column is dropped from this table
  entirely** — it's a per-contributor annual assessed-contribution figure
  reported as a side reference within these voluntary-contributions reports,
  not something that belongs in this table's category taxonomy. 

* **2009 and 2011 biennium fix**: the WHA reports underlying 2009
  (`A63_ID4-en`) and 2011 (`A65_29Add1-en`) are structured as **2-year biennium
  totals** (2008-2009 and 2010-2011 respectively), with a "by fund and by
  donor" schedule spanning many donor-category sections (Member States, then
  research institutes/foundations/etc. that can share a country's name, e.g.
  "Research Centre (IDRC), Canada" is a distinct donor from "Canada"). The
  original vision extraction fragmented multi-line donor names across these
  sections.
    + `WHO_funds/who_extract_2009_biennium.py` deterministically re-extracts
      `A63_ID4-en-voluntarytable.pdf` into
      `WHO_voluntary_contributions_2008to2009_biennium.csv`, with proper
      multi-line donor-name reconstruction (donor-level total within 0.4% of
      the document's own stated "Total General Fund" figure). This 2008-2009
      biennium total is used as-is under `year=2009` — there's no 2008 annual
      baseline in this project to split it against, so it's **not** an annual
      figure (left unsplit rather than guessed, per user decision).
    + `WHO_voluntary_contributions_2010to2011_biennium.csv` is used for 2011,
      converted to a true annual figure: `annual_2011 =
      biennium_2010_2011_total − known_annual_2010` (per contributor per
      category), since a clean, independently-sourced annual 2010 figure
      exists. Whenever this subtraction would produce a negative value
      (verified as a genuine discrepancy between WHO's own two source documents
      for ~17 contributors, not an extraction error — e.g. Gynuity Health
      Projects), the pipeline falls back to the raw biennium figure instead of
      reporting an impossible negative amount.

* **"Belgium"/"Spain" duplicate-row bug fixed**: never real duplicates — both
  were donors ("Light For The World, Belgium", "Generalitat Valenciana, Spain")
  whose distinguishing name prefix was dropped during extraction by two bugs in
  `WHO_funds/who_extract_2010to2015.py`: (1) an overly broad `SKIP_KW`
  substring match on `'for the'` that also matched inside real donor names
  (fixed to require the phrase to start the line), and (2) a stray page-number
  token being mistaken for a row's actual data value (fixed to verify the token
  parses into a real column first). Re-extracted; resolved the entire remaining
  fragmentation issue in this table.

* **Document-code leak fixed**: `who_extract_2009_biennium.py`'s
  page-number/document-code filter only matched when both appeared combined on
  one text line; on pages where they appeared separately, the bare
  document-code line leaked into a donor's name (e.g. `"A63/INF.DOC./4
  Nepal"`). Fixed and re-extracted.

* **2016-2024 name-concatenation bugs fixed** (2026-08-19): the same `'for
  the'` `SKIP_KW` over-match from the 2010-2015 fix above also existed in
  `who_extract_2016to2024.py`, but fixing it in isolation exposed two further,
  previously-hidden bugs, all now root-caused and fixed:
    + A rotated "Annex"-style watermark stamp on some pages (2022, 2023
      confirmed) bleeds single characters into the table's name column,
      breaking multi-line name reconstruction and once produced a phantom row
      with a fabricated few-dollar value (e.g. "European Hearing Instrument
      Manufacturers Association" split off from its real "(EHIMA)" row). Fixed
      by dropping any lone 1-character word in the name column as stamp noise.
    + A trailing parenthetical continuation on its own line (e.g. `"Health
      Equity Matters (previously"` + `"Australian Federation of AIDS"` +
      `"Organisations)"`) wasn't being reattached when the entity's numbers
      were already found on an earlier line. Fixed with an unmatched-open-paren
      rescue: if the name accumulated so far has an unclosed `(`, the next
      name-only line is always treated as its closing continuation — a
      condition with no false-positive risk against a genuinely new, unrelated
      entity's name (unlike a "numbers appear nearby" heuristic, which was
      tried first and caused real regressions by merging unrelated donors
      together before being reverted to a narrower, gated version).
    + Applied the same two fixes to `who_extract_2010to2015.py` (2010, 2012,
      2014, 2015, and the 2010-2011 biennium file), which had the identical bug
      pattern (e.g. "AFRICAN PROGRAMME FOR ONCHOCERCIASIS CONTROL" losing its
      "(APOC)" suffix, which got wrongly glued onto the next entity, "AGE UK").
    + Re-extracted all of 2010, 2012, 2014, 2015, 2016-2024, and the 2010-2011
      biennium file. Verified against each year's own reported "Grand
      Total"/"Total General Fund" line: 2019, 2020, 2022, 2023 now reconcile
      exactly; 2016, 2017, 2024 improved substantially; 2018 and 2021 still
      have large reconciliation gaps that predate this fix and were not
      introduced by it — see "Known remaining gaps" below for the follow-up
      investigation.

* **Parenthesized-negative values in regular contributor rows now parsed**
  (2026-08-19): WHO occasionally reports an inline reversal/correction using
  accounting-style parentheses within an otherwise normal row (e.g. Saudi
  Arabia 2021: `48 000 000 3 095 491 (48 000 000) 3 095 491`), which the
  digit-only number parser silently dropped entirely. Fixed in
  `who_extract_2016to2024.py`, re-extracted 2016-2024. Surfaced 2 more
  legitimate negative values (Saudi Arabia 2021, Royal Tropical Institute (KIT)
  2016) that were previously present but zeroed-out/misattributed rather than
  correctly negative.

* **`'alliance for health policy'` removed from `SKIP_KW`** (2026-08-19): this
  footer-filter keyword was a false positive that silently dropped a real,
  recurring donor - "Alliance for Health Policy and Systems Research (AHPSR)" -
  confirmed present and being wrongly filtered in 2016, 2018, 2020, 2021, and
  2024. Fixed and re-extracted; the donor's name and value are now correctly
  attributed (the dollar amount was never actually lost - it was landing on the
  next entity's row).

* **2008 added** (2026-08-19): extracted from `A62_ID4-en-voluntarytable.pdf`
  by a new bespoke script, `WHO_funds/who_extract_2008.py` — see the 2008 note
  above for its unique structure. Along the way, fixed a
  footnote-superscript-digit row-splitting bug (a footnote marker glued onto
  "OTHER" shifted that word's bounding box just enough to land in a different
  table row than its own values, splitting one row into two) and a
  parenthesized-negative-value parser gap (WHO reports a negative "Other"
  adjustment line as `(7 235 160)`, which the existing digit-only number parser
  couldn't recognize as numeric at all).

* **Missing `total_voluntary_contributions` summary rows derived**
  (2026-08-19): 2008 arrived with no summary row at all (271 contributors),
  because its source report — unlike 2009+ — has no single per-contributor
  grand-total column spanning its 11 separate fund sections. Four later years
  were each missing one as well (2018-2021). Where the summary is absent it is
  now computed as the sum of that contributor-year's `component` rows.
  Validated against the source: in A62_ID4-en the main table's own Total column
  equals `specified + core` for all 25 contributors that populate both, and the
  derived 2008 summaries sum to exactly $1,111,325,223 — the document's own
  published GRAND TOTAL. Where a year's report *does* state its own total, that
  reported figure is kept as-is rather than recomputed (so WHO's own rounding
  and the 2018/2021 discrepancies below are preserved rather than silently
  papered over).

* **Contributor name casing normalized** (2026-08-19): the pre-2015 WHA reports
  print contributor names in ALL CAPS, so 2008 and 2010-2012/2014 arrived
  shouting while 2009 and 2015+ were properly cased — the same donor appeared
  under two different spellings depending on year, which broke cross-year
  grouping. 846 all-caps names were normalized: 480 matched an existing
  properly-cased spelling elsewhere in the data (matched case- and
  punctuation-insensitively, deliberately **not** fuzzily — this project has a
  history of near-miss donor names being wrongly merged), and 366 were
  title-cased with an acronym-aware caser. Acronyms, digit-bearing tokens
  (`3M`, `AG`, `NV`, `ICARE4AUTISM`) and connecting words are handled from a
  vocabulary derived from the data itself rather than a hardcoded list. Genuine
  standalone acronyms (`FAO`, `UNICEF`, `BRAC`, `UNAIDS`…) are deliberately
  left uppercase; a bare single-token name is only re-cased when there's
  positive evidence it isn't an acronym — either World Bank matched it as a
  country (`CHILE`→`Chile`, `POLAND`→`Poland`) or the word appears in ordinary
  case elsewhere. 216 of 271 2008 contributors now share an exact name with a
  2009-2024 row.

* **Phantom "RECEIPTS" contributor dropped** (2026-08-19): in the 2010-2011
  biennium report the footer label "OTHER AND MISCELLANEOUS RECEIPTS" wraps
  across two lines with only the second line carrying the numbers, so it leaked
  in as an $11.4M contributor literally named `RECEIPTS`. Added `receipts` to
  the footer-keyword filter in `wb_match.py`.

* **Name-embedded numbers no longer eaten as data in the 2009 source**
  (2026-08-19): `who_extract_2009_biennium.py` treated *any* numeric token as a
  value regardless of where it sat on the page, so a number forming part of a
  donor's name was consumed as data and concatenated onto the real figure. This
  invented a **$2,007,178,010** amount for "The Asian Pacific Digestive Week
  2007 (APDW)" (whose actual contribution is $178,010 — the `2007` is part of
  the event name). Fixed by requiring a numeric token to also sit in the data
  area (x0 ≥ 180) to count as a value. The same fix corrected two more rows:
  "The Bone and Joint Decade 2000–2010" (name truncated and its $111,752 lost
  from the category column) and "David and Lucile Packard Foundation" (a stray
  `-` column placeholder glued onto the name). All three verified line-by-line
  against `A63_ID4-en-voluntarytable.pdf`.

* Exact-duplicate rows (same contributor/year/category/value, from the original
  source repeating a value once per fragmented sub-row) are dropped.


## Known Remaining Gaps

* **2018 and 2021 have large reconciliation gaps against their own PDF's
  reported "Grand Total" (2018: ~$26M short, 2021: ~$151M short) that are NOT
  extraction bugs** — investigated exhaustively (2026-08-19): every digit
  character in the source PDF is confirmed captured (character-count parity
  between pdfplumber's raw `chars` and its word-grouped tokens, on every page),
  the extracted CSV's row-level sums are internally consistent (each row's own
  reported total equals the sum of its own category columns), and the "Total –
  Member States" checkpoint reconciles exactly to WHO's own figure. The
  shortfall is concentrated entirely in the "other contributors"
  (non-member-state) portion of specific categories (2021: mostly
  `special_programmes_and_collaborative_arrangements`, short by ~$74M) with no
  missing text findable anywhere in the document. Two real, smaller bugs *were*
  found and fixed along the way (both apply across several years, not just
  2018/2021): (1) WHO occasionally reports a negative reversal inline in a
  regular contributor row using accounting-style parentheses (e.g. "Saudi
  Arabia ... 48 000 000 ... (48 000 000) ... 3 095 491"), which the extractor's
  digit-only number parser couldn't recognize at all; (2) `SKIP_KW`'s
  `'alliance for health policy'` entry was a false-positive footer filter that
  silently dropped a real, recurring donor ("Alliance for Health Policy and
  Systems Research (AHPSR)", confirmed present in 2016/2018/2020/2021/2024).
  Neither fix changes the aggregate reconciliation gap (the affected dollar
  values were already being counted, just mislabeled), confirming the residual
  $26M/$151M really is unexplained by extraction logic. Best remaining
  hypothesis: a genuine inconsistency within WHO's own published PDF between
  itemized rows and its own stated subtotal - would need a different validation
  source (e.g. WHO's audited financial statements) to pin down further.

* A handful of unusually long single-line names (donor name + numbers sharing
  one PDF line, with the name itself wrapping past the assumed name-column
  boundary) get truncated — e.g. 2016's "Kobe Group (Hyogo Prefecture Kobe
  Chamber of Commerce and Industry and Kobe Steel, Ltd.)" loses its middle/tail
  words though its dollar value stays correct. Rare (~1 case per year
  observed); the fixed-x0 name/number column split used by these extractors is
  the root cause, not yet reworked to be fully dynamic.

* Contributor name casing is now normalized across all years (see "What was
  changed" above), so the source's own all-caps/title-case split no longer
  leaks into the output. Two residual cosmetic wrinkles remain, both inherited
  from the *original vision-extracted* rows rather than the all-caps years: a
  few names carry a mis-cased parenthetical acronym (`(Hmn)`, `(Cdf)` instead
  of `(HMN)`, `(CDF)`), and a few carry a spuriously capitalized ordinary word
  mid-name (`'THE Fred Hollows FOUNDATION'`). These were already mixed-case so
  the casing pass deliberately left them untouched rather than risk re-casing a
  correct name.

* Cook Islands, Niue, Tokelau, and dissolved pre-2001 Yugoslavia are
  legitimately outside current World Bank classification and correctly remain
  blank.
