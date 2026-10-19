"""
Builds voluntary_contributions_long: a long-format table (one row per
contributor/year/category) with USD_nominal / USD_2024_adjusted columns.

Verified during planning: the source amounts in voluntary_contributions.parquet
are nominal (as-reported) USD despite the old README claim of being
inflation-adjusted; USD_2024_adjusted here is a fresh forward computation using
WHO_funds/inflation_adjust2024.csv.

assessed_contributions is built separately by build_assessed_contributions.py
(kept wide, not reconciled with this script).
"""

import re

import pandas as pd

from wb_match import (
    build_stripped_reference,
    build_wb_reference,
    fix_wb_match,
    is_footer_row,
    norm,
)

SRC_DIR = "."
RAW_DIR = "../WHO_funds"

META_COLS = ["contributor", "region", "year", "income_group", "file"]

# Columns that are aggregates/derived rather than additive line-items.
SUMMARY_COLS = {
    "total_voluntary_contributions",
}

# Raw per-year wide CSVs (pdfplumber text extraction) that take priority over the
# vision-extracted parquet for any category they cover. Excludes the biennium file
# (WHO_voluntary_contributions_2010to2011_biennium.csv), which reports 2010+2011
# combined and can't be cleanly split into single-year rows.
RAW_CSV_YEARS = {
    2008: "WHO_voluntary_contributions_2008.csv",
    2010: "WHO_voluntary_contributions_2010.csv",
    2012: "WHO_voluntary_contributions_2012.csv",
    2014: "WHO_voluntary_contributions_2014.csv",
    2015: "WHO_voluntary_contributions_2015.csv",
    2016: "WHO_voluntary_contributions_2016.csv",
    2017: "WHO_voluntary_contributions_2017.csv",
    2018: "WHO_voluntary_contributions_2018.csv",
    2019: "WHO_voluntary_contributions_2019.csv",
    2020: "WHO_voluntary_contributions_2020.csv",
    2021: "WHO_voluntary_contributions_2021.csv",
    2022: "WHO_voluntary_contributions_2022.csv",
    2023: "WHO_voluntary_contributions_2023.csv",
    2024: "WHO_voluntary_contributions_2024.csv",
}

COLUMN_MAP = {
    "core voluntary contributions account": "core_voluntary_contributions_account",
    "other voluntary contributions - core": "voluntary_contributions_core",
    "voluntary contributions - core": "voluntary_contributions_core",
    "voluntary contributions - specified": "voluntary_contributions_specified",
    "special programmes and collaborative arrangements": "special_programmes_and_collaborative_arrangements",
    "outbreak and crisis response": "outbreak_and_crisis_response",
    "contingency fund for emergencies": "contingency_fund_for_emergencies",
    "special programme of research, development and research training in human reproduction": "special_programme_on_research_development_and_training_in_human_reproduction",
    "special programme of research development and research training in human reproduction": "special_programme_on_research_development_and_training_in_human_reproduction",
    "stop tb partnership": "stop_tb_partnership",
    "special programme for research and training in tropical diseases": "special_programme_for_research_and_training_in_tropical_diseases",
    "total revenue": "total_voluntary_contributions",
    "grand total": "total_voluntary_contributions",
    "roll back malaria partnership": "roll_back_malaria_partnership",
    "water supply and sanitation collaborative council": "water_supply_and_sanitation_collaborative_council",
    "total": "total_voluntary_contributions",
    # 2008-only categories (WHO_voluntary_contributions_2008.csv) - this report
    # breaks contributions into several named fund sections that no later
    # year reports separately; see who_extract_2008.py's docstring.
    "stop tb partnership global drug facility": "stop_tb_partnership_global_drug_facility",
    "who framework convention on tobacco control": "who_framework_convention_on_tobacco_control",
    "other partnerships (2008)": "other_partnerships_2008",
    "revolving fund for teaching and laboratory equipment": "revolving_fund_for_teaching_and_laboratory_equipment",
}

# The 2008-2009 and 2010-2011 WHA reports (A63, A65) report by BIENNIUM, not
# annual year - each donor row is a 2-year combined total. WHO_voluntary_
# contributions_2010to2011_biennium.csv was already cleanly extracted
# (donor names correctly disambiguated, e.g. "Flemish Government, Belgium" vs
# "Belgium"). WHO_voluntary_contributions_2008to2009_biennium.csv was newly
# extracted by who_extract_2009_biennium.py after the original vision-model
# extraction fragmented multi-line donor names (see that script's docstring).
#
# Per-user decision: for 2011, derive a true annual figure by subtracting the
# already-known clean annual 2010 (from RAW_CSV_YEARS) out of the 2010-2011
# biennium total, per contributor per category. For 2009, no 2008 annual
# baseline exists anywhere in the project, so the 2008-2009 biennium total is
# used as-is under the year=2009 label (replacing the old fragmented data,
# but not attempting to split it into an annual figure).
BIENNIUM_2009_PATH = "WHO_voluntary_contributions_2008to2009_biennium.csv"
BIENNIUM_2010_2011_PATH = "WHO_voluntary_contributions_2010to2011_biennium.csv"

# The `file` column should record WHO's own original published PDF, not the
# intermediate WHO_voluntary_contributions_YYYY.csv this pipeline extracted
# from it (the "-voluntarytable"/"-biennium" suffixed files in WHO_funds/ are
# locally-cropped derivatives of these, not something WHO published under
# that name). 2013 has no PDF source here at all - it comes from
# who_revenue2013.csv, a different (non-WHA-report) data lineage - so it's
# deliberately left out of this map and keeps its own filename.
YEAR_TO_SOURCE_PDF = {
    2008: "A62_ID4-en.pdf",
    2009: "A63_ID4-en.pdf",
    2010: "A64_29Add1Corr1-en.pdf",
    2011: "A65_29Add1-en.pdf",
    2012: "A66_29Add1-en.pdf",
    2014: "A68_INF1-en.pdf",
    2015: "A69_INF3-en.pdf",
    2016: "A70_INF4-en.pdf",
    2017: "A71_INF2-en.pdf",
    2018: "A72_INF5-en.pdf",
    2019: "A73_INF3-en.pdf",
    2020: "A74_INF4-en.pdf",
    2021: "A75_INF5-en.pdf",
    2022: "A76_INF2-en.pdf",
    2023: "A77_INF2-en.pdf",
    2024: "A78_INF3-en.pdf",
}


def apply_source_pdf_filenames(long_df):
    mapping = {float(y): p for y, p in YEAR_TO_SOURCE_PDF.items()}
    override = long_df["year"].map(mapping)
    long_df["file"] = override.fillna(long_df["file"])
    return long_df


def normalize_header(h):
    return " ".join(h.replace("–", "-").replace("’", "'").lower().split())


def parse_amount(v):
    if pd.isna(v):
        return None
    s = str(v).strip().replace(",", "")
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_raw_csv_year(year, path):
    df = pd.read_csv(path, dtype=str)
    rename = {}
    for col in df.columns:
        if col == "Contributor":
            continue
        key = normalize_header(col)
        if key not in COLUMN_MAP:
            raise ValueError(f"Unmapped column '{col}' in {path}")
        rename[col] = COLUMN_MAP[key]
    df = df.rename(columns={"Contributor": "contributor", **rename})
    df = df[~df["contributor"].apply(is_footer_row)].copy()
    value_cols = sorted(set(rename.values()))
    for c in value_cols:
        df[c] = df[c].map(parse_amount)
    df["year"] = float(year)
    df["file"] = path.split("/")[-1]
    df["region"] = None
    df["income_group"] = None
    return df[META_COLS + value_cols], set(value_cols)


def build_raw_csv_long(wb_ref, wb_ref_stripped):
    frames = []
    categories_by_year = {}
    wide_by_year = {}
    for year, fname in RAW_CSV_YEARS.items():
        wide, categories = load_raw_csv_year(year, f"{RAW_DIR}/{fname}")
        wide = fix_wb_match(wide, wb_ref, wb_ref_stripped)
        frames.append(melt_to_long(wide, META_COLS))
        categories_by_year[float(year)] = categories
        wide_by_year[float(year)] = wide
    return pd.concat(frames, ignore_index=True), categories_by_year, wide_by_year


def build_2009_biennium_long(wb_ref, wb_ref_stripped):
    """2008-2009 biennium total, used as-is under year=2009 (no annual baseline exists to split it)."""
    wide, categories = load_raw_csv_year(2009, f"{RAW_DIR}/{BIENNIUM_2009_PATH}")
    wide = fix_wb_match(wide, wb_ref, wb_ref_stripped)
    return melt_to_long(wide, META_COLS), {2009.0: categories}


def build_2011_annual_from_biennium(wb_ref, wb_ref_stripped, wide_2010):
    """True annual 2011 = (2010-2011 biennium total) - (known annual 2010), per contributor/category."""
    wide_biennium, categories = load_raw_csv_year(2011, f"{RAW_DIR}/{BIENNIUM_2010_2011_PATH}")
    wide_biennium = fix_wb_match(wide_biennium, wb_ref, wb_ref_stripped)

    value_cols = sorted(categories)
    biennium_key = wide_biennium["contributor"].map(norm)
    wide_2010_indexed = wide_2010.copy()
    wide_2010_indexed["key"] = wide_2010_indexed["contributor"].map(norm)
    wide_2010_indexed = wide_2010_indexed.drop_duplicates(subset="key").set_index("key")

    # For some contributors the biennium (2010-2011) total is smaller than their
    # standalone 2010 total alone - verified against both source PDFs directly
    # (e.g. Gynuity Health Projects: A64 2010 report says 500,905; A65 biennium
    # report says 400,724 for the same fund) - a genuine discrepancy between WHO's
    # own two reports, not an extraction error. Subtracting produces a nonsensical
    # negative "2011" figure in that case. Per user decision (2026-08-19): fall
    # back to the raw biennium figure for that (contributor, category) instead of
    # subtracting, rather than reporting an impossible negative amount.
    annual_2011 = wide_biennium.copy()
    for col in value_cols:
        prior_2010 = biennium_key.map(
            lambda k: wide_2010_indexed.loc[k, col] if k in wide_2010_indexed.index and col in wide_2010_indexed.columns else 0.0
        ).fillna(0.0)
        has_value = annual_2011[col].notna()
        raw_biennium_value = annual_2011.loc[has_value, col]
        subtracted = raw_biennium_value - prior_2010[has_value]
        annual_2011.loc[has_value, col] = subtracted.where(subtracted >= 0, raw_biennium_value)

    still_negative = (annual_2011[value_cols] < 0).any(axis=1)
    if still_negative.any():
        print(
            f"  Note: {still_negative.sum()} contributors still have a negative value in the raw "
            f"biennium source itself (not from subtraction) - kept as-is: "
            f"{annual_2011.loc[still_negative, 'contributor'].tolist()}"
        )

    return melt_to_long(annual_2011, META_COLS), {2011.0: categories}


def apply_raw_csv_priority(long_df, replacement_long, categories_by_year):
    """Drop (year, category) pairs now covered by a higher-priority source, replace with its values."""
    drop_pairs = {(yr, cat) for yr, cats in categories_by_year.items() for cat in cats}
    key = list(zip(long_df["year"], long_df["category"]))
    mask = pd.Series(key, index=long_df.index).isin(drop_pairs)
    kept = long_df[~mask]
    return pd.concat([kept, replacement_long], ignore_index=True)


def melt_to_long(df, id_vars):
    value_cols = [c for c in df.columns if c not in id_vars]
    long = df.melt(id_vars=id_vars, value_vars=value_cols, var_name="category", value_name="USD_nominal")
    long = long.dropna(subset=["USD_nominal"])
    long["category_type"] = long["category"].apply(lambda c: "summary" if c in SUMMARY_COLS else "component")
    return long


# Words kept lowercase inside a title-cased name (never as the first word).
SMALL_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "de", "del", "des", "di", "du",
    "for", "from", "in", "of", "on", "or", "the", "to", "van", "von", "y",
}


def is_all_caps_name(s):
    letters = [c for c in str(s) if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


def name_key(s):
    """Case/punctuation/whitespace-insensitive key for matching the same
    contributor across years. Deliberately NOT fuzzy - this project has a
    history of near-miss donor names being wrongly merged (e.g. "Research
    Centre (IDRC), Canada" is a different donor from "Canada"), so only
    differences in case and punctuation are treated as the same entity."""
    s = str(s).lower()
    for ch, repl in (("’", "'"), ("‘", "'"), ("–", "-"), ("—", "-")):
        s = s.replace(ch, repl)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def build_case_vocab(names):
    """Derive, from the data itself, which tokens are acronyms and which are
    ordinary words.

    Returns (acronyms, normal_words). A token counts as an ordinary word if it
    is ever seen containing a lowercase letter ("Foundation", "the", "Other").
    Acronyms are all-caps tokens that are NEVER seen in ordinary case - the
    check has to be that strict because the original vision-extracted names
    contain spuriously-capitalised real words ("FOUNDATION for Genomics...",
    "THE Fred Hollows FOUNDATION"), so "appears all-caps somewhere" on its own
    would wrongly classify FOUNDATION, THE and INTERNATIONAL as acronyms."""
    caps_tokens, normal_words = set(), set()
    for n in names:
        all_caps_name = is_all_caps_name(n)
        for tok in str(n).split():
            core = tok.strip("(),.[]'’-")
            letters = [c for c in core if c.isalpha()]
            if not letters:
                continue
            if any(c.islower() for c in core):
                normal_words.add(core.lower())
            elif not all_caps_name and len(letters) >= 2 and len(core) <= 8:
                # all-caps token sitting inside an otherwise cased name
                caps_tokens.add(core.upper())
    return caps_tokens - {t.upper() for t in normal_words}, normal_words


def _cap_word(word):
    """Capitalize a single word, respecting hyphenated compounds and the
    O'/D'/L' contraction pattern (so CHRISTOFFEL-BLINDENMISSION becomes
    Christoffel-Blindenmission and O'NEILL becomes O'Neill, while PEOPLE'S
    stays People's)."""
    parts = [p.capitalize() if p else p for p in word.split("-")]
    out = "-".join(parts)
    m = re.match(r"^(o|d|l|mc)'(\w)(.*)$", out, flags=re.IGNORECASE)
    if m:
        out = f"{m.group(1).capitalize()}'{m.group(2).upper()}{m.group(3)}"
    return out


def smart_title(name, acronyms, normal_words, is_country=False):
    """Title-case an ALL-CAPS name while preserving acronyms and digit-bearing
    tokens (3M, AG, NV) and lowercasing connecting words.

    A standalone single-token name is ambiguous - it could be an organisation
    that really is an acronym (FAO, UNAIDS, BRAC) or just a shouted country
    name (CHILE, POLAND). It's only title-cased when there's positive evidence
    it isn't an acronym: either World Bank matched it as a country, or the word
    is one that appears in ordinary case elsewhere in the data. Otherwise it's
    left alone rather than inventing a spelling like "Brac"."""
    # "NAME(ACRONYM)" -> "NAME (ACRONYM)" so the acronym tokenizes separately
    # and keeps its capitalisation.
    tokens = re.sub(r"(?<=[A-Za-z])\(", " (", str(name)).split()
    if len(tokens) == 1:
        core = tokens[0].strip("(),.")
        if any(c.isdigit() for c in core):
            return name  # e.g. ICARE4AUTISM
        # Only a plain unbroken word can be a bare acronym; anything with
        # internal structure (hyphen, apostrophe) is a real name to case.
        if core.isalpha() and not is_country and core.lower() not in normal_words:
            return name
    out = []
    for idx, tok in enumerate(tokens):
        pre, core, post = re.match(r"^(\W*)(.*?)(\W*)$", tok, flags=re.UNICODE).groups()
        if not core:
            out.append(tok)
        elif core.upper() in acronyms or any(c.isdigit() for c in core):
            out.append(pre + core.upper() + post)
        elif idx > 0 and core.lower() in SMALL_WORDS:
            out.append(pre + core.lower() + post)
        else:
            out.append(pre + _cap_word(core.lower()) + post)
    return " ".join(out)


def normalize_contributor_casing(long_df):
    """The pre-2015 WHA reports print contributor names in ALL CAPS, so 2008 and
    2010-2012/2014 arrive shouting while 2009 and 2015+ are properly cased.
    Map each all-caps name to its existing properly-cased spelling elsewhere in
    the data; fall back to acronym-aware title-casing for names that only ever
    appear in the all-caps years (per user decision 2026-08-19)."""
    all_names = long_df["contributor"].dropna().unique()
    reference = {}
    for n in all_names:
        if not is_all_caps_name(n):
            reference.setdefault(name_key(n), n)

    # A World Bank region match is positive evidence the contributor is a
    # country rather than an acronym-named organisation.
    countries = set(long_df.loc[long_df["region"].notna(), "contributor"].dropna().unique())

    acronyms, normal_words = build_case_vocab(all_names)
    mapping, matched, titled = {}, 0, 0
    for n in all_names:
        if not is_all_caps_name(n):
            continue
        ref = reference.get(name_key(n))
        if ref is not None:
            mapping[n], matched = ref, matched + 1
        else:
            titled_name = smart_title(n, acronyms, normal_words, is_country=n in countries)
            if titled_name != n:
                mapping[n], titled = titled_name, titled + 1

    if not mapping:
        return long_df
    long_df["contributor"] = long_df["contributor"].map(lambda c: mapping.get(c, c))
    print(
        f"Contributor casing: normalized {len(mapping)} all-caps names "
        f"({matched} matched an existing cased spelling, {titled} title-cased)"
    )
    return long_df


def add_missing_summary_rows(long_df):
    """Every contributor-year should carry a `total_voluntary_contributions`
    summary row, but 2008's source report has no per-contributor grand-total
    column spanning its 11 fund sections (verified against A62_ID4-en: the main
    table's own Total column equals specified+core exactly, and summing every
    component across all sections reproduces the document's published GRAND
    TOTAL of 1,111,325,223). So where the summary is absent, derive it as the
    sum of that contributor-year's components - matching how the later years'
    reported Grand Total relates to their own category columns."""
    summary_col = "total_voluntary_contributions"
    components = long_df[long_df["category_type"] == "component"]
    have = set(
        map(tuple, long_df.loc[long_df["category"] == summary_col, ["contributor", "year"]].values)
    )

    totals = (
        components.groupby(["contributor", "year"], as_index=False)
        .agg({"USD_nominal": "sum", "region": "first", "income_group": "first", "file": "first"})
    )
    missing = totals[~totals.apply(lambda r: (r["contributor"], r["year"]) in have, axis=1)].copy()
    if missing.empty:
        return long_df

    missing["category"] = summary_col
    missing["category_type"] = "summary"
    by_year = missing["year"].value_counts().sort_index()
    print(
        f"Derived {len(missing)} missing '{summary_col}' summary rows "
        f"(by year: {', '.join(f'{int(y)}:{n}' for y, n in by_year.items())})"
    )
    return pd.concat([long_df, missing[long_df.columns]], ignore_index=True)


def apply_inflation(long_df, inflation):
    merged = long_df.merge(
        inflation.rename(columns={"base_yr": "year", "adjust": "adjust_factor"})[["year", "adjust_factor"]],
        on="year",
        how="left",
    )
    merged["adjust_factor"] = merged["adjust_factor"].fillna(1.0)
    merged.loc[merged["year"] == 2024, "adjust_factor"] = 1.0
    merged["USD_2024_adjusted"] = merged["USD_nominal"] * merged["adjust_factor"]
    return merged.drop(columns=["adjust_factor"])


def main():
    vc = pd.read_parquet(f"{SRC_DIR}/voluntary_contributions.parquet")
    inflation = pd.read_csv(f"{RAW_DIR}/inflation_adjust2024.csv")

    vc = vc[~vc["contributor"].apply(is_footer_row)].reset_index(drop=True)
    print(f"voluntary_contributions: {len(vc)} rows after dropping footer/summary labels")

    wb_ref = build_wb_reference(vc)
    wb_ref_stripped = build_stripped_reference(wb_ref)
    vc = fix_wb_match(vc, wb_ref, wb_ref_stripped)
    print(f"voluntary_contributions blank region: {vc['region'].isna().sum()} / {len(vc)}")

    # The 'assessed_contributions' reference column doesn't belong in this table's
    # category taxonomy - assessed_contributions_2005-2024 (built separately by
    # build_assessed_contributions.py) is the home for that figure.
    vc = vc.drop(columns=["assessed_contributions"])

    vc_long = melt_to_long(vc, META_COLS)

    raw_long, categories_by_year, wide_by_year = build_raw_csv_long(wb_ref, wb_ref_stripped)

    long_2009, cats_2009 = build_2009_biennium_long(wb_ref, wb_ref_stripped)
    long_2011, cats_2011 = build_2011_annual_from_biennium(wb_ref, wb_ref_stripped, wide_by_year[2010.0])
    raw_long = pd.concat([raw_long, long_2009, long_2011], ignore_index=True)
    categories_by_year.update(cats_2009)
    categories_by_year.update(cats_2011)

    pre_rows = len(vc_long)
    vc_long = apply_raw_csv_priority(vc_long, raw_long, categories_by_year)
    print(
        f"\nRaw-CSV priority merge: {pre_rows} -> {len(vc_long)} voluntary rows "
        f"({len(raw_long)} rows sourced from raw/biennium CSVs across {len(categories_by_year)} years)"
    )

    # Casing first, so the summary rows below group on the final contributor
    # names (and don't get stranded under a now-renamed spelling).
    vc_long = normalize_contributor_casing(vc_long)
    vc_long = add_missing_summary_rows(vc_long)

    vc_long = apply_inflation(vc_long, inflation)
    vc_long = apply_source_pdf_filenames(vc_long)

    col_order = META_COLS + ["category", "category_type", "USD_nominal", "USD_2024_adjusted"]
    vc_long = vc_long[col_order].sort_values(["year", "contributor", "category"]).reset_index(drop=True)

    before = len(vc_long)
    vc_long = vc_long.drop_duplicates().reset_index(drop=True)
    residual = vc_long.duplicated(subset=["contributor", "year", "category"], keep=False).sum()
    print(
        f"voluntary_contributions_long: dropped {before - len(vc_long)} exact-duplicate rows; "
        f"{residual} rows remain with same (contributor, year, category) but different values "
        f"(pre-existing source fragmentation, not resolved here)"
    )

    vc_long.to_parquet(f"{SRC_DIR}/voluntary_contributions_long.parquet", index=False)
    vc_long.to_csv(f"{SRC_DIR}/voluntary_contributions_long.csv", index=False)
    print(f"\nWrote voluntary_contributions_long: {len(vc_long)} rows")


if __name__ == "__main__":
    main()
