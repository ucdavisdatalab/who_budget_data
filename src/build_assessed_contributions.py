"""
Builds assessed_contributions_2005-2024: a cleaned version of
assessed_contributions.parquet, kept WIDE (one row per contributor/year, one
column per field - credits_start_of_year, current_year_assessment,
balances_due_*, etc.), matching the shape of the original
assessed_contributions.rds/.parquet.

Nominal USD only (no inflation-adjustment column). Cleanup applied: footer/
summary rows dropped, World Bank region/income_group re-matched. No further
extensions (no relocation from voluntary contributions, no 2009/2024
upgrades) - those were validated separately in an earlier long-format version
and can be re-added deliberately later; this is a deliberate rebuild from the
original wide source only (per user decision 2026-08-19).
"""

import pandas as pd

from wb_match import build_stripped_reference, build_wb_reference, fix_wb_match, is_footer_row

SRC_DIR = "."
AC_WIDE_NAME = "assessed_contributions_2005-2024"

META_COLS = ["contributor", "region", "year", "income_group", "file"]


def main():
    ac = pd.read_parquet(f"{SRC_DIR}/assessed_contributions.parquet")

    ac = ac[~ac["contributor"].apply(is_footer_row)].reset_index(drop=True)
    print(f"assessed_contributions: {len(ac)} rows after dropping footer/summary labels")

    wb_ref = build_wb_reference(ac)
    wb_ref_stripped = build_stripped_reference(wb_ref)
    ac = fix_wb_match(ac, wb_ref, wb_ref_stripped)
    print(f"assessed_contributions blank region: {ac['region'].isna().sum()} / {len(ac)}")

    col_order = META_COLS + [c for c in ac.columns if c not in META_COLS]
    ac = ac[col_order].sort_values(["year", "contributor"]).reset_index(drop=True)

    before = len(ac)
    ac = ac.drop_duplicates().reset_index(drop=True)
    residual = ac.duplicated(subset=["contributor", "year"], keep=False).sum()
    print(
        f"{AC_WIDE_NAME}: dropped {before - len(ac)} exact-duplicate rows; "
        f"{residual} rows remain with the same (contributor, year) but different values "
        f"(pre-existing source fragmentation, not resolved here)"
    )

    ac.to_parquet(f"{SRC_DIR}/{AC_WIDE_NAME}.parquet", index=False)
    ac.to_csv(f"{SRC_DIR}/{AC_WIDE_NAME}.csv", index=False)
    print(f"\nWrote {AC_WIDE_NAME}: {len(ac)} rows")


if __name__ == "__main__":
    main()
