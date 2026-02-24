# merging csvs extracted from Peritz WHO PDFs
# joey suen

# packages
import pandas as pd
import re
from IPython.display import display

# (WORK IN PROGRESS) must make reproducible
csvs = ['/Users/joeysuen/Downloads/final csvs - A58_31-en-table.pdf.csv', 
        '/Users/joeysuen/Downloads/final csvs - A60_ID6-en-table.pdf.csv',
        '/Users/joeysuen/Downloads/final csvs - A61_ID1-en-table.pdf.csv']

# initialize dictionary of dataframes
dfs = {}

for csv in csvs:
    # set up dictionary
    name = (re.search(r"A.*?(?=\.pdf)", csv)).group()
    dfs[name] = pd.read_csv(csv)

    # append "Filename" column
    dfs[name]["Filename"] = name

    # append "Year" column
    assessment_col = [col for col in dfs[name].columns if "assessment" in col.lower()][0]
    year = re.search(r"\d{4}", assessment_col).group()
    dfs[name]["Year"] = int(year)

    # (WORK IN PROGRESS) generalizing column names
    generalized_cols = ["Members", "Credits (Start of Year)", "Current Year Assessment",
                        "Total Amount Oustanding (Start of Year)", "Receipts/Credits Given During Current Year",
                        "Balances Due 1987 - (Second Previous Year)", "Balances Due Previous Year",
                        "Balances Due Current Year", "Balances Due Total"]
    cols = list(dfs[name].columns)
    cols[:9] = generalized_cols
    dfs[name].columns = cols

merged_df = pd.concat(dfs, ignore_index=True)

# (WORK IN PROGRESS) change path name
merged_df.to_parquet('/Users/joeysuen/Desktop/merged_df.parquet')
