# merging csvs extracted from Peritz WHO PDFs
# joey suen

# packages
import pandas as pd
import re
from pathlib import Path
from IPython import display
from rapidfuzz import process # for column name standardization

# import data
BASE_DIR = Path(__file__).resolve().parent
file_path = BASE_DIR.parent / "data" / "final csvs.xlsx"
df = pd.read_excel(file_path, sheet_name=None) # note: df is a dictionary

# pre-processing
for sheet_name, table in df.items():

    # drop columns with "unnamed" column headers
    df[sheet_name] = table.loc[:, ~table.columns.str.contains("^unnamed", case=False)]

    # append file name as column
    name = re.search(r"A.*?(?=\.pdf)", sheet_name, re.IGNORECASE)
    table["File"] = name.group()

    # standardize capitalization of column names
    df[sheet_name].columns = df[sheet_name].columns.str.lower().str.strip()

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
               "A65_29Add1-en.pdf (General Fund",
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

# GROUP 1 --------------------------------------
g1_cols = ["Members", "Credits (Start of Year)", "Current Year Assessment",
                            "Total Amount Outstanding (Start of Year)", "Receipts/Credits Given During Current Year",
                            "Balances Due 1987 - (Second Previous Year)", "Balances Due Previous Year",
                            "Balances Due Current Year", "Balances Due Total"]

for filename in groups["group1"]:

    # key all dataframes in group 1
    table = df[filename]

    # append "Year" column
    assessment_cols = [col for col in table.columns if "assessment" in col.lower()]
    if assessment_cols:
        assessment_col = assessment_cols[0]
        year = re.search(r"\d{4}", assessment_col).group()
        table["Year"] = int(year)
    
    # generalizing table column names
    cols = list(table.columns)
    cols[:9] = g1_cols
    table.columns = cols

# concatenate group 1
g1_concat = pd.concat([df[f] for f in groups["group1"]], ignore_index=True)

# GROUP 3 --------------------------------------
g3_cols = ["contributor", 
           "core voluntary contributions account", 
           "voluntary contributions - core", 
           "voluntary contributions - specified", 
           "stop tb partnership",
           "roll back malaria partnership",
           "special programmes and collaborative arrangements", 
           "outbreak and crisis response",  
           "contingency fund for emergencies", 
           "special programme of research, development and research training in human reproduction", 
           "special programme for research and training in tropical diseases", 
           "grand total",
           "water supply and sanitation collaborative council",
           "file"]

# standardize column names
for filename in groups["group3"]:

    # contributor/donor column name
    df[filename] = df[filename].rename(columns={"donor": "contributor"})

    # rename column - total revenue -> grand total
    df[filename].columns = [re.sub(r"total revenue", "grand total", col) for col in df[filename].columns]

    # generalize all other column names
    df[filename] = fuzzy_rename(df[filename], g3_cols, 80)

# concatenate group 3
g3_concat = pd.concat([df[f] for f in groups["group3"]], ignore_index=True)

# MERGING / OUTPUT -----------------------------

# (TO DO: MAKE LOOP FOR ALL GROUPS)
file_path = BASE_DIR.parent / "data" / "group1.parquet"
g1_concat.to_parquet(file_path)

#file_path = BASE_DIR.parent / "data" / "group3.parquet"
#g3_concat.to_parquet(file_path)

# check the parquet file:
check = pd.read_parquet(file_path)
print(check)