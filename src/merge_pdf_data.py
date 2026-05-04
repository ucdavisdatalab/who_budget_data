# merging csvs extracted from Peritz WHO PDFs
# joey suen

# packages
import pandas as pd
import re
from pathlib import Path
from rapidfuzz import process # for column name standardization

# import main data
data_path = "data/raw/2026-03-15_extracted_data.xlsx"
df = pd.read_excel(data_path, sheet_name=None) # note: df is a dictionary

# import inflation & country data
inflation = pd.read_csv("data/raw/inflation_adjust2024.csv")
inflation_adjustment_map = inflation.set_index("base_yr")["adjust"].to_dict()

country = pd.read_excel("data/raw/wb_countries.xlsx").loc[:, "CountryName"]

# groupings of similarly formatted PDFs
groups = {
    "group1": ["A58_31-en-table.pdf",
               "A60_ID6-en-table.pdf",
               "A61_ID1-en-table.pdf"],

    "group2": ["A62_30-en.pdf",
               "A63_33-en.pdf"],

    "group3": ["A63_ID4-en.pdf (member states)",
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
               "A77_INF2-en.pdf (General)"]
}

# year mappings
years = {"A58_31-en-table.pdf": 2005,
        "A60_ID6-en-table.pdf": 2007,
        "A61_ID1-en-table.pdf": 2008,
        "A62_30-en.pdf": 2008,
        "A63_33-en.pdf": 2009,
        "A63_ID4-en.pdf (member states)": 2009,
        "A63_ID4-en.pdf (donors)": 2009,
        "A64_29Add1Corr1-en.pdf": 2010,
        "A65_29Add1-en.pdf (General)": 2010,
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

# function: fuzzy match values (general case)
def fuzzy_rename(labels, base_labels, threshold=80):
    results = []
    for label in labels:
        result = process.extractOne(label, base_labels)
        if result == None:
            results.append(label)
        else:
            match, score, _ = result
            if score >= threshold:
                results.append(match)
            else:
                # add original label to list so no length mismatch
                results.append(label) 
    return results

# function: fuzzy match column names
def fuzzy_rename_df(df, col_names, threshold=80):
    return df.rename(columns = dict(zip(df.columns, fuzzy_rename(df.columns, col_names, threshold))))

# pre-processing
for sheet_name, table in df.items():

    table = table.copy()

    # drop columns with "unnamed" column headers
    table = table.loc[:, ~table.columns.str.contains("^unnamed", case=False)]

    # standardize column names
    table.columns = table.columns.str.lower().str.strip() # capitalization
    table.columns = [re.sub(r'[^\w]', '_', col) for col in table.columns] # replace non-alphanumerics with underscore
    table.columns = [re.sub(r'_+', '_', col).strip('_') for col in table.columns] # remove consecutive underscores

    # append file name as column
    name = re.search(r"A.*?(?=\.pdf)", sheet_name, re.IGNORECASE)
    table["file"] = name.group()

    # append year as column
    if sheet_name in groups["group1"]: # group 1
        assessment_cols = [col for col in table.columns if "assessment" in col.lower()]
        if assessment_cols:
            year = re.search(r"\d{4}", assessment_cols[0]).group()
            table["year"] = int(year)
    elif sheet_name in years:
        table["year"] = years[sheet_name]

    # adjust numbers for inflation (standardize to 2024 USD)
    if ("year" in table.columns) and ("year" in range(2000, 2023)):
        table_year = table["year"].iloc[0]
        usd_cols = table.select_dtypes(include="number").columns.difference(["year"])
        table[usd_cols] *= inflation_adjustment_map[table_year]

    # standardize contributor names using fuzzy match
    table.iloc[:, 0] = (table.iloc[:, 0]).str.title()
    table.iloc[:, 0] = fuzzy_rename(table.iloc[:, 0], country, 80)

    # standardize 
    df[sheet_name] = table

# GROUP 1
def clean_group1(df=df, groups=groups):
    g1_cols = ["members",
            "credits_start_of_year",
            "current_year_assessment",
            "total_amount_outstanding_start_of_year",
            "receipts_credits_given_during_current_year",
            "balances_due_from_1987_to_second_previous_year",
            "balances_due_previous_year",
            "balances_due_current_year",
            "balances_due_total",
            "file",
            "year"]

    for sheet in groups["group1"]:

        # key all dataframes in group 1
        table = df[sheet].copy()

        # generalizing table column names
        rename_map = dict(zip(table.columns[:9], g1_cols[:9]))
        df[sheet] = table.rename(columns=rename_map)

    # concatenate group 1
    g1_concat = pd.concat([df[f] for f in groups["group1"]], ignore_index=True)

    # drop "membres" column (same as members, but French)
    g1_concat = g1_concat.drop('membres', axis=1)

    return g1_concat

# GROUP 2 
def clean_group2(df=df, groups=groups):

    # A63_33-en.pdf is just an updated version of A62_30-en.pdf, so we'll just drop A62
    g2 = df["A63_33-en.pdf"].copy()

    g2_cols = {
            "members_and_associate_members": "members", 
            "biennial_assessment_2008": "biennial_assessment_prev_year",
            "biennial_assessment_2009": "biennial_assessment_curr_year",
            "collected_or_adjusted_for_current_biennium_including_prepayment_2008": "collected_or_adjusted_including_prev_year_prepayment",
            "collected_or_adjusted_for_current_biennium_including_prepayment_2009": "collected_or_adjusted_including_curr_year_prepayment",
            "balance_for_prior_years_as_on_31_december_2007": "prior_years_balance",
            "rescheduled_assessment_as_on_31_december_2007": "rescheduled_assessment_as_on_prev_year",
            "collected_or_adjusted_during_current_biennium": "collected_or_adjusted_current_biennium"
    }

    g2 = g2.rename(columns=g2_cols)

    return g2

# GROUP 3
def clean_group3(df=df, groups=groups):

    g3_cols = ["contributor",
            "core_voluntary_contributions_account",
            "voluntary_contributions_core",
            "voluntary_contributions_specified",
            "stop_tb_partnership",
            "roll_back_malaria_partnership",
            "special_programmes_and_collaborative_arrangements",
            "outbreak_and_crisis_response",
            "contingency_fund_for_emergencies",
            "special_programme_on_research_development_and_training_in_human_reproduction",
            "special_programme_for_research_and_training_in_tropical_diseases",
            "grand_total",
            "water_supply_and_sanitation_collaborative_council",
            "file"]

    # standardize column names
    for filename in groups["group3"]:

        # contributor/donor column name
        df[filename] = df[filename].rename(columns={"donor": "contributor"})

        # replace "total revenue" to "grand total" in column names
        df[filename].columns = [re.sub(r"total_revenue", "grand_total", col) for col in df[filename].columns]

        # generalize all other column names
        df[filename] = fuzzy_rename_df(df[filename], g3_cols, 80)
        
    # concatenate group 3
    g3_concat = pd.concat([df[f] for f in groups["group3"]], ignore_index=True)

    return g3_concat

# MERGING / OUTPUT -----------------------------

processed_data_dir = Path("data/processed")
processed_data_dir.mkdir(parents=True, exist_ok=True)

g1 = clean_group1()
g1.to_parquet(processed_data_dir / "group1.parquet")

g2 = clean_group2()
g2.to_parquet(processed_data_dir / "group2.parquet")

g3 = clean_group3()
g3.to_parquet(processed_data_dir / "group3.parquet")

