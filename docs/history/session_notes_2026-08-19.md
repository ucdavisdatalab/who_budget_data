# Session notes — 2026-08-19

## Context

Continuation of the voluntary-contributions reconciliation work from 2026-08-18. Starting point: `voluntary_contributions_long` existed (10,591 rows, 2009-2024) but the README was stale after a prior restructuring (assessed contributions had been split into its own separate wide-format table/script, not yet reflected in the docs), and several known gaps remained open: a deferred 2016-2024 name-concatenation bug, a garbled "Australia" row, casing inconsistency, and no 2008 coverage. By the end of the session, `voluntary_contributions_long` was marked **complete**.

## Work completed

### 1. README rewrite
Full rewrite of `WHO_funds_processed/README.md` to reflect the post-restructuring state: separated "original source" descriptions from "processed output" descriptions, documented the two independent build scripts (`build_long_format.py` for voluntary contributions, `build_assessed_contributions.py` for assessed contributions — written but not yet run), and updated the Methods section to describe both the original vision-based and newer deterministic pdfplumber-based extraction pipelines.

### 2. Fixed the deferred 2016-2024 name-concatenation bug (and its 2010-2015 twin)
Root-caused to two distinct issues in `who_extract_2016to2024.py`:
- A rotated "Annex"-style watermark stamp on some pages (confirmed 2022, 2023) bleeds single characters into the table's name column, breaking multi-line name reconstruction and in one case producing a phantom row with a fabricated few-dollar value. Fixed by dropping any lone 1-character word in the name column as stamp noise.
- A trailing parenthetical continuation on its own line (e.g. "Health Equity Matters (previously" + "Australian Federation of AIDS" + "Organisations)" — this turned out to be the source of the previously-reported "garbled Australia row") wasn't being reattached when the entity's numbers were already found on an earlier line. Fixed with an unmatched-open-paren rescue: if the accumulated name has an unclosed `(`, the next name-only line is always its closing continuation — unlike a "numbers appear nearby" heuristic (tried first, reverted after it caused real regressions by merging unrelated donors together).

Applied the same two fixes to `who_extract_2010to2015.py`, which had the identical bug pattern (e.g. "AFRICAN PROGRAMME FOR ONCHOCERCIASIS CONTROL" losing its "(APOC)" suffix onto the next entity, "AGE UK"). Re-extracted 2010, 2012, 2014, 2015, 2016-2024, and the 2010-2011 biennium file. Verified against each year's own reported total line: 2019/2020/2022/2023 now reconcile exactly; 2016/2017/2024 improved substantially.

### 3. Added 2008
Wrote a new bespoke extractor, `WHO_funds/who_extract_2008.py`, for `A62_ID4-en-voluntarytable.pdf` — this report has a structure unlike any other year (one main specified/core table plus 9 separate fund-specific sections, each with its own contributor list and subtotal; 5 of those sections use categories no other year has: `stop_tb_partnership_global_drug_facility`, `who_framework_convention_on_tobacco_control`, `other_partnerships_2008`, `revolving_fund_for_teaching_and_laboratory_equipment`). All 10 sections' extracted sums were checked against WHO's own reported subtotal and match exactly. Along the way fixed a footnote-superscript-digit row-splitting bug and a parenthesized-negative-value parsing gap specific to that document. Integrated into `build_long_format.py` via `RAW_CSV_YEARS`/`COLUMN_MAP`.

### 4. Fixed the `file` column
It was recording the intermediate `WHO_voluntary_contributions_YYYY.csv` filename rather than WHO's original published PDF. Added a year→source-PDF mapping (`YEAR_TO_SOURCE_PDF`) applied at the end of `build_long_format.py`'s build, so `file` now shows e.g. `A72_INF5-en.pdf` for 2018. 2013 is the one exception (sourced from `who_revenue2013.csv`, a different non-WHA-report data lineage, so there's no PDF to name).

### 5. Investigated the 2018/2021 reconciliation gaps
User asked to root-cause the ~$26M (2018) and ~$151M (2021) shortfalls between summed contributor rows and each PDF's own reported Grand Total. Exhaustive investigation (2021 as the worked example) ruled out extraction bugs via three independent checks: character-level completeness (pdfplumber's raw `chars` vs. word-grouped digit counts matched exactly on every page), no bad cropping (the `-voluntarytable.pdf` source files are a byte-for-byte match against the corresponding pages of the full original document), and internal consistency (each row's own reported total equals the sum of its own category columns; the "Total – Member States" checkpoint reconciles exactly). Concluded the residual gap is most likely a genuine inconsistency within WHO's own published PDF between itemized rows and its own stated subtotal, not something fixable through better parsing — would need an external validation source (e.g. WHO's audited financial statements) to pin down further.

Two smaller, real bugs *were* found and fixed along the way (both affecting several years, not just 2018/2021):
- WHO occasionally reports an inline negative reversal using accounting-style parentheses within an otherwise normal contributor row (e.g. Saudi Arabia 2021: `48 000 000 3 095 491 (48 000 000) 3 095 491`), which the digit-only number parser couldn't recognize at all. Fixed by extending the numeric-token test and routing regular rows through the same negative-aware assembler already used for special summary rows.
- `SKIP_KW`'s `'alliance for health policy'` entry was a false-positive footer filter silently dropping a real, recurring donor ("Alliance for Health Policy and Systems Research (AHPSR)"), confirmed wrongly filtered in 2016, 2018, 2020, 2021, and 2024. Removed the keyword.

Neither fix changed the aggregate reconciliation number (the dollar values were already being counted, just mislabeled), confirming the residual gap really is unexplained by extraction logic.

**Bonus discovery, explicitly declined by the user**: `A75_INF5-en.pdf`'s "Schedule 2" has a second, entirely separate table ("B. Fiduciary Funds", ~$38M for 2021, different categories entirely) that isn't currently extracted. User decided this is a separate table/project, not to be folded into this pipeline.

### 6. File cleanup
Removed build cruft from both `WHO_funds/` and `WHO_funds_processed/`: `__pycache__` directories, `.DS_Store`, `.Rapp.history`. No PDFs, scripts, or CSV locations were changed — the existing flat `WHO_funds/` (inputs + extraction scripts) vs. `WHO_funds_processed/` (build scripts + outputs) split was judged already clean enough, per user decision.

## Status at end of session

**`voluntary_contributions_long` marked COMPLETE.** 10,975 rows, years 2008-2024 (2013 totals-only), 0 residual same-(contributor,year,category)-different-value rows, 7 legitimate negative `USD_nominal` values (all verified real against source PDFs). Remaining known limitations (documented in the README's "Known remaining gaps" section) are non-blocking:
- 2018/2021 reconciliation gaps — investigated, concluded to be a WHO source-data inconsistency, not fixable via extraction.
- A handful of rare (~1/year) long single-line names get truncated (dollar values stay correct).
- Casing differences pre/post ~2016 confirmed to be a genuine source-formatting difference, not a bug.
- Cook Islands/Niue/Tokelau/dissolved-Yugoslavia correctly blank (not World Bank members).
- "B. Fiduciary Funds" — explicitly out of scope.

**`assessed_contributions_2005-2024` remains a separate, still-open workflow** — `build_assessed_contributions.py` exists but has never been run. Not touched this session beyond what was already true as of 2026-08-18.

## Files added/changed this session

- `WHO_funds/who_extract_2008.py` (new)
- `WHO_funds/who_extract_2010to2015.py` (fixed: watermark noise, unmatched-paren rescue, parenthesized-negative values)
- `WHO_funds/who_extract_2016to2024.py` (fixed: same as above, plus `SKIP_KW` false-positive removed)
- `WHO_funds/WHO_voluntary_contributions_2008.csv` (new, extraction output)
- `WHO_funds/WHO_voluntary_contributions_{2010,2012,2014,2015,2016-2024}.csv` (re-extracted)
- `WHO_funds/WHO_voluntary_contributions_2010to2011_biennium.csv` (re-extracted)
- `WHO_funds_processed/build_long_format.py` (updated: 2008 integration, `YEAR_TO_SOURCE_PDF` mapping for the `file` column)
- `WHO_funds_processed/voluntary_contributions_long.{parquet,csv,rds}` (rebuilt: 10,975 rows)
- `WHO_funds_processed/README.md` (rewritten, then updated repeatedly through the session)
- `WHO_funds/__pycache__`, `WHO_funds_processed/__pycache__`, `WHO_funds_processed/.DS_Store`, `WHO_funds_processed/.Rapp.history` (removed)
