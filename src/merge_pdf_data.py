# merging csvs extracted from Peritz WHO PDFs
# joey suen

import pandas as pd
import re
from pathlib import Path
from rapidfuzz import process

# =============================================================================
# LOAD RAW DATA
# =============================================================================

# main extracted PDF data (dictionary of sheets)
df = pd.read_excel("data/raw/2026-03-15_extracted_data.xlsx", sheet_name=None)

# inflation adjustment map (standardize to 2024 USD)
inflation = pd.read_csv("data/raw/inflation_adjust2024.csv")
inflation_adjustment_map = inflation.set_index("base_yr")["adjust"].to_dict()

# world bank country metadata
country = pd.read_excel("data/raw/wb_countries.xlsx")

# WHO revenue data (assessed + voluntary contributions by country/year)
who_revenue_frames = []
for file in Path("data/raw/who_revenue").iterdir():
    if file.suffix == ".csv":
        table = pd.read_csv(file)
    elif file.suffix == ".xlsx":
        table = pd.read_excel(file)
    table.columns = table.columns.str.lower().str.strip()
    table = table.rename(columns={"state": "contributor", "region": "contributor"})
    who_revenue_frames.append(table)

who_revenue = pd.concat(who_revenue_frames, ignore_index=True)

# =============================================================================
# PROCESS WHO REVENUE DATA
# =============================================================================

who_revenue["grant_type"] = who_revenue["grant_type"].str.strip().str.lower().str.replace(" ", "_")
who_revenue["contributor"] = who_revenue["contributor"].str.title()
who_revenue = who_revenue[who_revenue["grant_type"] != "revenue_from_other_activities"]

who_revenue_pivot = who_revenue.pivot_table(
    index=["contributor", "year"],
    columns="grant_type",
    values="amount"
).reset_index()

# =============================================================================
# GROUP / YEAR MAPPINGS
# =============================================================================

# assessed_contributions: annual assessed contributions per member state (2005, 2007, 2008)
# voluntary_contributions: earmarked voluntary contributions breakdown (2009-2023, excl. 2013)

groups = {
    "assessed_contributions": [
        "A58_31-en-table.pdf",
        "A60_ID6-en-table.pdf",
        "A61_ID1-en-table.pdf"
    ],
    "voluntary_contributions": [
        "A63_ID4-en.pdf (member states)",
        "A63_ID4-en.pdf (donors)",
        "A64_29Add1Corr1-en.pdf",
        "A65_29Add1-en.pdf (General)",
        "A66_29Add1-en.pdf (General)",
        "A68_INF1-en.pdf (General)",
        "A69_INF3-en.pdf (General)",
        "A70_INF4-en.pdf  (General)",
        "A71_INF2-en.pdf  (General)",
        "A72_INF5-en.pdf  (General)",
        "A73_INF3-eng.pdf  (General)",
        "a74_inf4-en.pdf (General)",
        "A75_INF5-en.pdf (General)",
        "a76_inf2-en.pdf (General)",
        "A77_INF2-en.pdf (General)"
    ]
}

years = {
    "A58_31-en-table.pdf": 2005,
    "A60_ID6-en-table.pdf": 2007,
    "A61_ID1-en-table.pdf": 2008,
    "A62_30-en.pdf": 2008,
    "A63_33-en.pdf": 2009,
    "A63_ID4-en.pdf (member states)": 2009,
    "A63_ID4-en.pdf (donors)": 2009,
    "A64_29Add1Corr1-en.pdf": 2010,
    "A65_29Add1-en.pdf (General)": 2011,
    "A66_29Add1-en.pdf (General)": 2012,
    "A68_INF1-en.pdf (General)": 2014,
    "A69_INF3-en.pdf (General)": 2015,
    "A70_INF4-en.pdf  (General)": 2016,
    "A71_INF2-en.pdf  (General)": 2017,
    "A72_INF5-en.pdf  (General)": 2018,
    "A73_INF3-eng.pdf  (General)": 2019,
    "a74_inf4-en.pdf (General)": 2020,
    "A75_INF5-en.pdf (General)": 2021,
    "a76_inf2-en.pdf (General)": 2022,
    "A77_INF2-en.pdf (General)": 2023
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def fuzzy_rename(labels, base_labels, threshold=80):
    results = []
    for label in labels:
        result = process.extractOne(label, base_labels)
        if result is None:
            results.append(label)
        else:
            match, score, _ = result
            results.append(match if score >= threshold else label)
    return results

def fuzzy_rename_df(df, col_names, threshold=80):
    return df.rename(columns=dict(zip(df.columns, fuzzy_rename(df.columns, col_names, threshold))))

# =============================================================================
# PRE-PROCESSING (applied to all sheets)
# =============================================================================

for sheet_name, table in df.items():
    table = table.copy()

    # drop unnamed columns
    table = table.loc[:, ~table.columns.str.contains("^unnamed", case=False)]

    # standardize column names
    table.columns = table.columns.str.lower().str.strip()
    table.columns = [re.sub(r'[^\w]', '_', col) for col in table.columns]
    table.columns = [re.sub(r'_+', '_', col).strip('_') for col in table.columns]

    # append source file name
    name = re.search(r"A.*?(?=\.pdf)", sheet_name, re.IGNORECASE)
    table["file"] = name.group()

    # append year
    if sheet_name in groups["assessed_contributions"]:
        assessment_cols = [col for col in table.columns if "assessment" in col.lower()]
        if assessment_cols:
            year = re.search(r"\d{4}", assessment_cols[0]).group()
            table["year"] = int(year)
    elif sheet_name in years:
        table["year"] = years[sheet_name]

    # inflation adjustment
    if ("year" in table.columns) and (table["year"].iloc[0] in range(2000, 2023)):
        table_year = table["year"].iloc[0]
        usd_cols = table.select_dtypes(include="number").columns.difference(["year"])
        table[usd_cols] *= inflation_adjustment_map[table_year]

    # standardize contributor names to world bank country names
    table.iloc[:, 0] = table.iloc[:, 0].str.title()
    table.iloc[:, 0] = fuzzy_rename(table.iloc[:, 0], country["CountryName"], 80)

    # merge in world bank region and income group
    table = table.merge(
        country[["CountryName", "Region", "IncomeGroup"]].rename(
            columns={"Region": "region", "IncomeGroup": "income_group"}),
        left_on=table.columns[0],
        right_on="CountryName",
        how="left"
    ).drop(columns="CountryName")

    df[sheet_name] = table

# =============================================================================
# ASSESSED CONTRIBUTIONS (2005, 2007, 2008)
# =============================================================================

def clean_assessed_contributions(df=df, groups=groups):

    col_names = ["contributor", "credits_start_of_year", "current_year_assessment",
                 "total_amount_outstanding_start_of_year", "receipts_credits_given_during_current_year",
                 "balances_due_from_1987_to_second_previous_year", "balances_due_previous_year",
                 "balances_due_current_year", "balances_due_total", "file", "year"]

    for sheet in groups["assessed_contributions"]:
        table = df[sheet].copy()
        rename_map = dict(zip(table.columns[:9], col_names[:9]))
        df[sheet] = table.rename(columns=rename_map)

    concat = pd.concat([df[f] for f in groups["assessed_contributions"]], ignore_index=True)
    concat = concat.drop('membres', axis=1)

    concat = concat[['contributor', 'region', 'year', 'income_group', 'file',
                     'credits_start_of_year', 'current_year_assessment',
                     'total_amount_outstanding_start_of_year',
                     'receipts_credits_given_during_current_year',
                     'balances_due_from_1987_to_second_previous_year',
                     'balances_due_previous_year', 'balances_due_current_year',
                     'balances_due_total']]

    return concat

# =============================================================================
# VOLUNTARY CONTRIBUTIONS (2009-2023, excl. 2013)
# =============================================================================

def clean_voluntary_contributions(df=df, groups=groups):

    col_names = ["contributor", "core_voluntary_contributions_account",
                 "voluntary_contributions_core", "voluntary_contributions_specified",
                 "stop_tb_partnership", "roll_back_malaria_partnership",
                 "special_programmes_and_collaborative_arrangements", "outbreak_and_crisis_response",
                 "contingency_fund_for_emergencies",
                 "special_programme_on_research_development_and_training_in_human_reproduction",
                 "special_programme_for_research_and_training_in_tropical_diseases",
                 "grand_total", "water_supply_and_sanitation_collaborative_council", "file"]

    for filename in groups["voluntary_contributions"]:
        df[filename] = df[filename].rename(columns={"donor": "contributor"})
        df[filename].columns = [re.sub(r"total_revenue", "grand_total", col) for col in df[filename].columns]
        df[filename] = fuzzy_rename_df(df[filename], col_names, 80)
        df[filename] = df[filename].rename(columns={"grand_total": "total_voluntary_contributions"})

    concat = pd.concat([df[f] for f in groups["voluntary_contributions"]], ignore_index=True)

    # merge in assessed contributions from who_revenue
    concat = concat.merge(
        who_revenue_pivot[["contributor", "year", "assessed_contributions"]],
        on=["contributor", "year"],
        how="left"
    )
   
    # append 2013 (no PDF source exists for this year, use who_revenue only)
    vol_2013 = who_revenue_pivot[who_revenue_pivot["year"] == 2013][
        ["contributor", "year", "voluntary_contributions", "assessed_contributions"]
    ].rename(columns={"voluntary_contributions": "total_voluntary_contributions"})

    vol_2013 = vol_2013.merge(
        country[["CountryName", "Region", "IncomeGroup"]].rename(
            columns={"Region": "region", "IncomeGroup": "income_group"}),
        left_on="contributor", right_on="CountryName", how="left"
    ).drop(columns="CountryName")

    concat = pd.concat([concat, vol_2013], ignore_index=True)

    # reorder columns and sort
    concat = concat[['contributor', 'region', 'year', 'income_group', 'file',
                     'voluntary_contributions_specified',
                     'special_programme_for_research_and_training_in_tropical_diseases',
                     'stop_tb_partnership',
                     'special_programme_on_research_development_and_training_in_human_reproduction',
                     'roll_back_malaria_partnership', 'water_supply_and_sanitation_collaborative_council',
                     'contingency_fund_for_emergencies', 'special_programmes_and_collaborative_arrangements',
                     'outbreak_and_crisis_response', 'core_voluntary_contributions_account',
                     'voluntary_contributions_core', 'total_voluntary_contributions',
                     'assessed_contributions']]

    concat["year"] = pd.to_numeric(concat["year"], errors="coerce")
    concat = concat.sort_values(["year", "contributor"]).reset_index(drop=True)

    return concat

# =============================================================================
# OUTPUT
# =============================================================================

processed_data_dir = Path("data/processed")
processed_data_dir.mkdir(parents=True, exist_ok=True)

assessed = clean_assessed_contributions()
assessed.to_parquet(processed_data_dir / "assessed_contributions.parquet")
assessed.to_csv(processed_data_dir / "assessed_contributions.csv")

voluntary = clean_voluntary_contributions()
voluntary.to_parquet(processed_data_dir / "voluntary_contributions.parquet")
voluntary.to_csv(processed_data_dir / "voluntary_contributions.csv")


