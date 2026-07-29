# World Health Organization Budget Dataset

[top]: #world-health-organization-budget-data

_Authors: Joey Suen, Nick Ulle, Lauren Peritz_  
_Maintainer: Nick Ulle <<naulle@ucdavis.edu>>_  

This repository contains code to post-process data extracted from World Health
Organization (WHO) Budget PDFs. The repository also contains code for some
initial exploratory analysis of the dataset. 

> [!IMPORTANT]
>
> This repository only contains the code and documentation for the dataset. It
> does not include the dataset itself (nor the `data/` directory).
>
> The dataset is provided separately.

The purpose of this project is to make historical data about voluntary
contributions to the WHO more easily accessible. The project was proposed by
Lauren Peritz and carried out by the [UC Davis DataLab][datalab].

[datalab]: https://datalab.ucdavis.edu/


## File and Directory Structure

The directory structure for the project is:

```
data/               Datasets
figures/            Graphics and figures
notebooks/          Notebooks (`.ipynb`, `.Rmd`, ...)
src/                Python/Java/... (non-R) source code
R/                  R source code
.gitattributes      Paths Git should give special treatment
.gitignore          Paths Git should ignore
CONTRIBUTING.md     Instructions for contributing to this project
LICENSE             License for the code
LICENSE-DATA        License for the dataset
README.md           This file
pixi.lock           Exact description of Pixi environment (dependencies)
pixi.toml           Project metadata file (including dependencies)
```

<!--
The files in the `data/` directory are:

```

```
-->

([back to top][top])


## Dataset Documentation

_Version: 1.0_  
_License: [CC BY-NC-SA 4.0 International](LICENSE-DATA)_  

The dataset consists of two parts: assessed contributions and voluntary
contributions. We provide data dictionaries for these two parts and a
description of how they were extracted in the subsequent sections.

For more information on how the WHO is funded, please visit [this page from the
WHO][who-funding]. For more information on how countries are classified into
income groups, please visit [this article from The World
Bank][world-bank-income-groups]. Please note that this article provides
information on country income classifications in the 2026 fiscal year, while
this dataset uses the classifications from the 2025 fiscal year.

[who-funding]: https://www.who.int/about/funding/
[world-bank-income-groups]: https://datahelpdesk.worldbank.org/knowledgebase/articles/906519-world-bank-country-and-lending-groups

This dataset is an adaptation of original works published by the World Health
Organization (WHO) under the [CC BY-NC-SA 3.0 IGO][] license. This adaptation
was not created by WHO. WHO is not responsible for the content or accuracy of
this adaptation. The original edition shall be the binding and authentic
edition.

[CC BY-NC-SA 3.0 IGO]: https://creativecommons.org/licenses/by-nc-sa/3.0/igo/


### Assessed Contributions

The file `assessed_contributions.parquet` contains data on assessed
contributions determined by the WHO for different member states for the years
2005, 2007, and 2008.

Property            | Value
---                 | ---
Source              | WHO assessed contributions reports (A58, A60, A61)
Years covered       | 2005, 2007-2008
Unit of observation | one row per member state per year
Currency            | US dollars, inflation-adjusted to 2024

Columns in the file (data dictionary):

| Column                                           | Type    | Description                                                             |
| ---                                              | ---     | ---                                                                     |
| `contributor`                                    | string  | WHO member state name, standardized to World Bank country names         |
| `region`                                         | string  | World Bank geographic region                                            |
| `year`                                           | integer | Year in which contributions were made                                   |
| `income_group`                                   | string  | World Bank income classification (for Fiscal Year 2025)                 |
| `file`                                           | string  | Source file for row                                                     |
| `credits_start_of_year`                          | integer | Credit balance carried over from the previous year                      |
| `current_year_assessment`                        | integer | Amount assessed to the member state for the current year                |
| `total_amount_outstanding_start_of_year`         | integer | Total unpaid balance owed by the member state at the start of the year  |
| `receipts_credits_given_during_current_year`     | integer | Credits applied to balance during the current year                      |
| `balances_due_from_1987_to_second_previous_year` | integer | Arrears owed from 1987 up to two years prior to the current report year |
| `balances_due_previous_year`                     | integer | Arrears owed from the previous year                                     |
| `balances_due_current_year`                      | integer | Unpaid balance remaining for the current report year                    |
| `balances_due_total`                             | integer | Sum of all outstanding balances across all periods                      |


### Voluntary Contributions

The file `voluntary_contributions.parquet` contains data on voluntary
contributions to the WHO (World Health Organization) from member states for the
years 2009-2023, except for 2013. These voluntary contributions are broken down
into contributions earmarked for specific purposes and programs. In addition,
this data includes the total assessed contributions for member states per year
for years 2014-2022.

Property            | Value
---                 | ---
Source              | WHO voluntary contributions reports (A68, A69, A70, A71, A72, A73, A74, A75, A76)
Years covered       | 2009-2012, 2014-2024
Unit of observation | one row per member state per year
Currency            | US dollars, inflation-adjusted to 2024

Columns in the file (data dictionary):

| Column                                                                         | Type    | Description                                                                                                            |
| ---                                                                            | ---     | ---                                                                                                                    |
| `contributor`                                                                  | string  | WHO member state name, standardized to World Bank country names                                                        |
| `region`                                                                       | string  | World Bank geographic region                                                                                           |
| `year`                                                                         | integer | Year in which contributions were made                                                                                  |
| `income_group`                                                                 | string  | World Bank income classification (for Fiscal Year 2025)                                                                |
| `file`                                                                         | string  | Source file for row                                                                                                    |
| `voluntary_contributions_specified`                                            | float   | Total voluntary contributions earmarked for a specific purpose                                                         |
| `special_programme_for_research_and_training_in_tropical_diseases`             | float   | Contributions to the UNICEF/UNDP/WHO/World Bank Special Programme for Research and Training in Tropical Diseases (TDR) |
| `stop_tb_partnership`                                                          | float   | Contributions to the Stop TB Partnership                                                                               |
| `special_programme_on_research_development_and_training_in_human_reproduction` | float   | Contributions to the WHO Special Programme of Research, Development and Research Training in Human Reproduction (HRP)  |
| `roll_back_malaria_partnership`                                                | float   | Contributions to the Roll Back Malaria Partnership                                                                     |
| `water_supply_and_sanitation_collaborative_council`                            | float   | Contributions to the Water Supply and Sanitation Collaborative Council (WSSCC)                                         |
| `contingency_fund_for_emergencies`                                             | float   | Contributions to the WHO Contingency Fund for Emergencies (CFE)                                                        |
| `special_programmes_and_collaborative_arrangements`                            | float   | Contributions to other special programmes and collaborative arrangements not listed separately                         |
| `outbreak_and_crisis_response`                                                 | float   | Contributions designated for WHO outbreak and crisis response activities                                               |
| `core_voluntary_contributions_account`                                         | float   | Unearmarked voluntary contributions to the WHO Core Voluntary Contributions Account (CVCA)                             |
| `voluntary_contributions_core`                                                 | float   | Core voluntary contributions not designated to a specific programme                                                    |
| `total_voluntary_contributions`                                                | float   | Total voluntary contributions across all categories                                                                    |
| `assessed_contributions`                                                       | float   | Mandatory assessed contributions owed by WHO member states based on the UN scale of assessments                        |


### Methods

Tabular data was extracted from WHO World Health Assembly PDF documents using a
semi-automated pipeline. For each source document, pages containing
contribution tables were converted to JPEG images at 300 DPI using pdftocairo
26.02.0 ([Poppler][]). The resulting images were then uploaded to Claude Sonnet
4.5 ([Anthropic][]), which extracted the tabular data and returned it as CSV
strings. Extracted CSVs were manually reviewed and saved. 

[Poppler]: https://poppler.freedesktop.org/
[Anthropic]: https://www.anthropic.com/

Extracted data was validated against a separate extraction of the same WHO
voluntary contributions reports by Lauren Peritz, who used Claude Sonnet 4.5 to
develop a Python pipeline based on the [pdfplumber][] package.

[pdfplumber]: https://github.com/jsvine/pdfplumber

Extracted data was then cleaned and standardized using a Python processing
pipeline. Contributor names were standardized to World Bank country names using
fuzzy string matching ([RapidFuzz][]). World Bank region and income group
classifications were merged in based on matched country names. All monetary
values were inflation-adjusted to 2024 US dollars.

[RapidFuzz]: https://rapidfuzz.github.io/RapidFuzz/

([back to top][top])


## Installation

To get started, open a terminal (Git Bash on Windows) and clone a copy of this
repo:

```
git clone git@github.com:datalab-dev/2025_law_youtube.git
```

Then follow the instructions in the next section to set up the necessary
software environment.


### Pixi

We use [Pixi][], a fast package manager based on the conda ecosystem, to
install the packages required to build this reader. To install Pixi, follow
[the official instructions][Pixi]. 

[pixi]: https://pixi.sh/

The `pixi.toml` file in this repo lists required packages, while the
`pixi.lock` file lists package versions for each platform. When the lock file
is present, Pixi will attempt to install the exact versions listed. Deleting
the lock file allows Pixi to install other versions, which might help if
installation fails (but beware of inconsistencies between package versions).

To install the required packages, open a terminal and navigate to this repo's
directory. Then run:

```sh
pixi install
```

This will automatically create a virtual environment and install the packages.

To open a shell in the virtual environment, run:

```sh
pixi shell
```

You can run the `pixi shell` command from the repo directory or any of its
subdirectories. Use the virtual environment to run any commands related to
building the reader. When you're finished using the virtual environment, you
can use the `exit` command to exit the shell.

([back to top][top])
