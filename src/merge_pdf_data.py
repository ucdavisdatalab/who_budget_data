# merging csvs extracted from Peritz WHO PDFs
# joey suen

# packages
import pandas as pd
import re
from pathlib import Path
from rapidfuzz import process # for column name standardization

# import data
file_path = "data/raw/2026-03-15_extracted_data.xlsx"
df = pd.read_excel(file_path, sheet_name=None) # note: df is a dictionary

# pre-processing
for sheet_name, table in df.items():

    # drop columns with "unnamed" column headers
    df[sheet_name] = table.loc[:, ~table.columns.str.contains("^unnamed", case=False)]

    # append file name as column
    name = re.search(r"A.*?(?=\.pdf)", sheet_name, re.IGNORECASE)
    df[sheet_name].loc[:, "file"] = name.group()

    # standardize column names
    df[sheet_name].columns = df[sheet_name].columns.str.lower().str.strip() # capitalization
    df[sheet_name].columns = [re.sub(r'[^\w]', '_', col) for col in df[sheet_name].columns] # replace non-alphanumerics with underscore
    df[sheet_name].columns = [re.sub(r'_+', '_', col).strip('_') for col in df[sheet_name].columns] # remove consecutive underscores

# grouping similarly formatted PDFs
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

# function: standardizing column names
def fuzzy_rename(df, col_names, threshold=80):
    rename_map = {}
    for col in df.columns:
        match, score, _ = process.extractOne(col, col_names)
        if score >= threshold and col != match:
            rename_map[col] = match
    return df.rename(columns=rename_map)

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
        table = df[sheet]

        # append "year" column
        assessment_cols = [col for col in table.columns if "assessment" in col.lower()]
        if assessment_cols:
            assessment_col = assessment_cols[0]
            year = re.search(r"\d{4}", assessment_col).group()
<<<<<<< Updated upstream:src/merge_pdf_data.py
            table["year"] = int(year)

=======
            df[sheet]["year"] = int(year)
        
>>>>>>> Stashed changes:src/peritz_who-pdfs_csv-merge.py
        # generalizing table column names
        rename_map = dict(zip(table.columns[:9], g1_cols[:9]))
        table = table.rename(columns=rename_map)
        df[sheet] = table

    # concatenate group 1
    g1_concat = pd.concat([df[f] for f in groups["group1"]], ignore_index=True)

    # drop "membres" column (same as members, but French)
    g1_concat = g1_concat.drop('membres', axis=1)

    return g1_concat

# GROUP 2 --------------------------------------

# upon first inspection, these tables appear to be the same,
# except A63_33-en.pdf contains additional information

# standarize column names (to allow for checking for overlap)
df["A63_33-en.pdf"] = df["A63_33-en.pdf"].rename(columns = {
    "balance_for_prior_years_as_on_31_december_2007": "balance_for_prior_years_31_dec_2007",
    "rescheduled_assessment_as_on_31_december_2007": "rescheduled_assessment_31_dec_2007",
    "collected_or_adjusted_during_current_biennium": "collected_adjusted_during_biennium",
})

df1 = df["A62_30-en.pdf"]
df2 = df["A63_33-en.pdf"] # larger table

# check if df1 rows exist in df2
merged = df1.merge(df2, on=list(df1.columns), how="left", indicator=True)
# (COMMENTED OUT): print(merged["_merge"].value_counts())
    # there are 90 "left_only" values, indicating df1 and df2 have different values


# upon inspection of the original PDFs, A63_33-en.pdf contains information up to
# 2009, while A62_30-en.pdf contains information up to 2008 - thus, the following columns
# differ: 'collected or adjusted during current biennum', 'balance outstanding (b))',
# and 'total outstanding (a+b)'

# thus, I will just add a year to these columns and merge


# adding year to differentiate columns
df1.columns = [col + "_as_on_2008" if col in
                               ["collected_adjusted_during_biennium",
                                "balance_outstanding_a",
                                "balance_outstanding_b",
                                "total_outstanding_a_b"]
                                else col for col in df1.columns]
df2.columns = [col + "_as_on_2009" if col in
                               ["collected_adjusted_during_biennium",
                                "balance_outstanding_a",
                                "balance_outstanding_b",
                                "total_outstanding_a_b"]
                                else col for col in df2.columns]

shared_cols = list(set(df1.columns) & set(df2.columns))
g2_merged = pd.merge(df1, df2, on=shared_cols, how='outer')

def find_group2_mismatches():
    for col in shared_cols:
        if col != "members_and_associate_members":
            mismatches = df1.merge(df2, on="members_and_associate_members")[
                [f"{col}_x", f"{col}_y"]
            ]
            mismatches = mismatches[mismatches[f"{col}_x"] != mismatches[f"{col}_y"]]
            if len(mismatches) > 0:
                print(f"\n{col}:")
                print(mismatches.head())

# Two mismatches, Kyrgyzstan and Panama, are disrupting the merging
    # Kyrgystan: differs on rescheduled assessment (31 dec 2007)
        # reschedule assessment from a63 = balance for prior yeras 31 dec 2007 from a62
        # gonna trust the updated one
    # Panama: differs on balance prior years (31 dec 2007)
        # this one is a bit more complicated, because the other numbers for collected/adjusted
        # during biennium and balance outstanding actually match up
        # I think I'm just gonna throw this row out

g2_merged = g2_merged[g2_merged["members_and_associate_members"] != "panama"]


# GROUP 3
def clean_group3(df=df, groups=groups):
<<<<<<< Updated upstream:src/merge_pdf_data.py
    g3_cols = ["contributor",
            "core_voluntary_contributions_account",
            "voluntary_contributions_core",
            "voluntary_contributions_specified",
=======

    g3_cols = ["contributor", 
            "core_voluntary_contributions_account", 
            "voluntary_contributions_core", 
            "voluntary_contributions_specified", 
>>>>>>> Stashed changes:src/peritz_who-pdfs_csv-merge.py
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
    
    g3_years = {
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


    # standardize column names
    for filename in groups["group3"]:

        # contributor/donor column name
        df[filename] = df[filename].rename(columns={"donor": "contributor"})

        # rename column - total revenue -> grand total
        df[filename].columns = [re.sub(r"total_revenue", "grand_total", col) for col in df[filename].columns]

        # generalize all other column names
        df[filename] = fuzzy_rename(df[filename], g3_cols, 80)

        # append "year" column
        df[filename].loc[:, "year"] = g3_years[filename]
        
    # concatenate group 3
    g3_concat = pd.concat([df[f] for f in groups["group3"]], ignore_index=True)

    return g3_concat

# MERGING / OUTPUT -----------------------------

processed_data_dir = Path("data/processed")
processed_data_dir.mkdir(parents=True, exist_ok=True)

g1_concat = clean_group1()
g1_concat.to_parquet(processed_data_dir / "group1.parquet")

g2_merged.to_parquet(processed_data_dir / "group2.parquet")

g3_concat = clean_group3()
g3_concat.to_parquet(processed_data_dir / "group3.parquet")
