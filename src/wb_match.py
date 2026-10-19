"""
Shared World Bank region/income_group matching logic, used by both
build_long_format.py (voluntary_contributions_long) and
build_assessed_contributions.py (assessed_contributions_2005-2024), so the two
tables use one consistent set of country-name fixes rather than two copies
that could drift apart.
"""

import re

import pandas as pd

FOOTER_KEYWORDS = [
    "total", "grand total", "pass through", "refunds to", "miscellaneous",
    "member states", "general fund", "assessed members", "inactive members",
    "all members",
    # In the 2010-2011 biennium report the footer label "OTHER AND MISCELLANEOUS
    # RECEIPTS" wraps across two lines, and only the second line carries the
    # numbers - so it leaked in as a phantom $11.4M contributor named
    # "RECEIPTS" that "miscellaneous" above doesn't catch.
    "receipts",
]

# Known contributor-name variants mapped to a spelling that's already correctly
# matched somewhere in the data (i.e. a verified anchor, not a guessed classification).
ALIASES = {
    "COTE D'IVOIRE": "CÔTE D'IVOIRE",
    "SWAZILAND": "ESWATINI",
    "THE FORMER YUGOSLAV REP OF MACEDONIA": "NORTH MACEDONIA",
    "THE FORMER YUGOSLAV REPUBLIC OF MACEDONIA": "NORTH MACEDONIA",
    "CAPE VERDE": "CABO VERDE",
    "CZECH REPUBLIC": "CZECHIA",
    "VIET NAM": "VIETNAM",
    "TÜRKIYE": "TURKEY",
    "TURKIYE": "TURKEY",
    "BRUNEI DARUSSALAM": "BRUNEI",
    "YEMEN": "YEMEN, REP.",
}

# Countries with no correctly-matched anchor anywhere in the data at all.
# Sourced directly from the World Bank Data Help Desk (FY2025 country/lending
# groups: https://datahelpdesk.worldbank.org/knowledgebase/articles/906519),
# not inferred from in-data anchors. Label style matches this dataset's
# existing vocabulary (regions use '&', income groups have no hyphens).
WB_DIRECT = {
    "KYRGYZSTAN": ("Europe & Central Asia", "Lower middle income"),
    "LAO PEOPLE'S DEMOCRATIC REPUBLIC": ("East Asia & Pacific", "Lower middle income"),
    "REPUBLIC OF KOREA": ("East Asia & Pacific", "High income"),
    "DEMOCRATIC PEOPLE'S REP. OF KOREA": ("East Asia & Pacific", "Low income"),
    "DEMOCRATIC PEOPLE'S REPUBLIC OF KOREA": ("East Asia & Pacific", "Low income"),
    "SAINT KITTS AND NEVIS": ("Latin America & Caribbean", "High income"),
    "SAINT LUCIA": ("Latin America & Caribbean", "Upper middle income"),
    "SAINT VINCENT AND THE GRENADINES": ("Latin America & Caribbean", "Upper middle income"),
    "SAO TOME AND PRINCIPE": ("Sub-Saharan Africa", "Lower middle income"),
    "PALESTINE": ("Middle East & North Africa", "Lower middle income"),
    "KOREA (THE REPUBLIC OF)": ("East Asia & Pacific", "High income"),
}


def norm(s):
    if pd.isna(s):
        return s
    return " ".join(str(s).upper().replace("’", "'").replace("`", "'").split())


def strip_formal_qualifiers(key):
    """Strip UN-style formal-name noise, e.g. 'IRAN (ISLAMIC REPUBLIC OF)' -> 'IRAN',
    'BAHAMAS (THE)' -> 'BAHAMAS', so it can be matched against a shorter WB anchor."""
    stripped = re.sub(r"\([^)]*\)", "", key)
    stripped = re.sub(r"\bTHE\b", "", stripped)
    return " ".join(stripped.split()).rstrip(",")


def is_footer_row(contributor):
    c = str(contributor).lower()
    return any(kw in c for kw in FOOTER_KEYWORDS)


def build_wb_reference(*dfs):
    """Canonical (normalized contributor -> region, income_group) from rows that already matched,
    pooled across however many dataframes are passed in."""
    frames = []
    for df in dfs:
        good = df.loc[df["region"].notna(), ["contributor", "region", "income_group"]].copy()
        good["key"] = good["contributor"].map(norm)
        frames.append(good)
    combined = pd.concat(frames, ignore_index=True)
    ref = (
        combined.groupby("key")
        .agg({"region": "first", "income_group": "first"})
        .reset_index()
    )
    return ref.set_index("key")[["region", "income_group"]]


def build_stripped_reference(wb_ref):
    stripped = wb_ref.reset_index()
    stripped["skey"] = stripped["key"].map(strip_formal_qualifiers)
    stripped = stripped.drop_duplicates(subset="skey", keep="first")
    return stripped.set_index("skey")[["region", "income_group"]]


def fix_wb_match(df, wb_ref, wb_ref_stripped):
    df = df.copy()
    key = df["contributor"].map(norm)
    aliased_key = key.map(lambda k: ALIASES.get(k, k))

    still_missing = df["region"].isna()
    for idx in df.index[still_missing]:
        k = aliased_key.loc[idx]
        sk = strip_formal_qualifiers(k)
        if k in wb_ref.index:
            df.loc[idx, "region"] = wb_ref.loc[k, "region"]
            df.loc[idx, "income_group"] = wb_ref.loc[k, "income_group"]
        elif sk in wb_ref_stripped.index:
            df.loc[idx, "region"] = wb_ref_stripped.loc[sk, "region"]
            df.loc[idx, "income_group"] = wb_ref_stripped.loc[sk, "income_group"]
        elif key.loc[idx] in WB_DIRECT:
            region, income_group = WB_DIRECT[key.loc[idx]]
            df.loc[idx, "region"] = region
            df.loc[idx, "income_group"] = income_group
    return df
