# World Health Organization Budget Data

[top]: #world-health-organization-budget-data

_Authors: Joey Suen, Nick Ulle, Lauren Peritz_  
_Maintainer: Nick Ulle <<naulle@ucdavis.edu>>_  

This repository contains code to post-process data extracted from World Health
Organization Budget PDFs (the data were extracted with Claude Sonnet 4.5). The
repository also contains code for some initial exploratory analysis of the
data. 

The purpose of this project is to make historical data about voluntary
contributions to the World Health Organization more easily accessible. The
project was proposed by Lauren Peritz and carried out by the [UC Davis
DataLab][datalab].

[datalab]: https://datalab.ucdavis.edu/


## File and Directory Structure

> [!IMPORTANT]
>
> Do not commit large files (> 1 MB) to the repository. Upload these to cloud
> storage (such as Google Drive or Box) instead.
>
> When you clone this repository, Git will not necessarily create directories
> that only contain large, untracked files (typically `data/` and `outputs/`).
> Instead you must manually create these directories and download their files
> from cloud storage.

The directory structure for the project is:

```
data/           Datasets
figures/        Graphics and figures
notebooks/      Notebooks (`.ipynb`, `.Rmd`, ...)
src/            Python/Java/... (non-R) source code
R/              R source code
.gitattributes  Paths Git should give special treatment
.gitignore      Paths Git should ignore
LICENSE         License for the project
README.md       This file
pixi.lock
pixi.toml
```

<!--
The files in the `data/` directory are:

```

```
-->

([back to top][top])


## Data

This dataset is an adaptation of original works published by the World Health
Organization (WHO). License: [CC BY-NC-SA 3.0
IGO](https://creativecommons.org/licenses/by-nc-sa/3.0/igo/). This adaptation
was not created by WHO. WHO is not responsible for the content or accuracy of
this adaptation. The original edition shall be the binding and authentic
edition.

Version: 1.0

### Assessed Contributions

Description: This dataset, contained in `assessed_contributions.parquet`,
contains data on assessed contributions determined by the WHO (World Health
Organization) for different member states for the years 2005, 2007, and 2008.
For more information on how the WHO is funded, please visit [this page from the
WHO][who-funding]. For more information on how countries are classified into
income groups, please visit [this article from The World
Bank][world-bank-income-groups]. Please note that this article provides
information on country income classifications in the 2026 fiscal year, while
this dataset uses the classifications from the 2025 fiscal year.

[who-funding]: https://www.who.int/about/funding/
[world-bank-income-groups]: https://datahelpdesk.worldbank.org/knowledgebase/articles/906519-world-bank-country-and-lending-groups

Source: WHO assessed contributions reports (A58, A60, A61)
Years covered: 2005, 2007-2008
Unit of observation: one row per member state per year
Currency: USD, inflation-adjusted to 2024

| Variable                                         | Type    | Description                                                             |
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

Description: This dataset, contained in `voluntary_contributions.parquet`,
contains data on voluntary contributions to the WHO (World Health Organization)
from member states for the years 2009-2023, except for 2013. These voluntary
contributions are broken down into contributions earmarked for specific
purposes and programs. In addition, this dataset includes the total assessed
contributions for member states per year for years 2014-2022. For more
information on how the WHO is funded, please visit [this page from the
WHO][who-funding]. For more information on how countries are classified into
income groups, please visit [this article from The World
Bank][world-bank-income-groups]. Please note that this article provides
information on country income classifications in the 2026 fiscal year, while
this dataset uses the classifications from the 2025 fiscal year.

Source: WHO voluntary contributions reports (A68, A69, A70, A71, A72, A73, A74, A75, A76)
Years covered: 2009-2012, 2014-2024
Unit of observation: one row per member state per year
Currency: USD, inflation-adjusted to 2024

| Variable                                                                       | Type    | Description                                                                                                            |
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
26.02.0 (Poppler). The resulting images were then uploaded to Claude Sonnet 4.5
(Anthropic), which extracted the tabular data and returned it as CSV strings.
Extracted CSVs were manually reviewed and saved. 

Extracted data was cross-validated against a separate extraction of the same
WHO voluntary contributions reports by Lauren Peritz, who utilized a Python
pipeline based on the pdfplumber package.

Extracted data was then cleaned and standardized using a Python processing
pipeline. Contributor names were standardized to World Bank country names using
fuzzy string matching (RapidFuzz). World Bank region and income group
classifications were merged in based on matched country names. All monetary
values were inflation-adjusted to 2024 USD.

([back to top][top])


## Installation

([back to top][top])


## Contributing

([back to top][top])
