# World Health Organization Budget Dataset

[top]: #world-health-organization-budget-data

_Authors: Joey Suen, Nick Ulle, Lauren Peritz_  
_Maintainer: Nick Ulle <<naulle@ucdavis.edu>>_  

This is a collection of contributions data extracted from World Health
Organization (WHO) Budget PDFs

The purpose of this project is to make historical data about voluntary
contributions to the WHO more easily accessible. The project was proposed by
Lauren Peritz and carried out by the [UC Davis DataLab][datalab].

[datalab]: https://datalab.ucdavis.edu/


## Dataset Documentation

_Version: 1.0_  
_License: [CC BY-NC-SA 4.0 International](LICENSE-DATA)_  

The dataset consists of two parts: assessed contributions and voluntary
contributions. We provide data dictionaries for these two parts and a
description of how they were extracted in the subsequent sections.

These two parts are deliberately *not merged with each other* and have
*different shapes* (voluntary contributions is long; assessed contributions is
wide, matching its original shape). This was a deliberate restructuring
decision on 2026-08-19.

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

The file `assessed_contributions.parquet`/`.rds` contains data on assessed
contributions determined by the WHO for different member states for the years
2005-2008.

Property            | Value
---                 | ---
Source              | WHO assessed contributions reports (A58, A60, A61)
Years covered       | 2005-2008
Unit of observation | One row per member state per year
Currency            | US dollars, nominal (as reported)

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


### Voluntary Contributions (long)

The file `voluntary_contributions_long.parquet`/`.rds` contains data on
voluntary contributions to the WHO (World Health Organization) from member
states for the years 2008-2024 (2013 has totals only).

This file is in long format, with one row per (contributor, year, funding
category) combination, rather than one row per (contributor, year) combination
with many category columns. See `build_long_format.py` for how this file was
generated.

Property            | Value
---                 | ---
Source              | WHO voluntary contributions reports (A68, A69, A70, A71, A72, A73, A74, A75, A76)
Years covered       | 2008-2024 (2013 has totals only)
Unit of observation | One row per member state per year per funding category
Currency            | US dollars, nominal (as reported); except `USD_2024_adjusted` (see below)

Columns in the file (data dictionary):

Column              | Type    | Description
---                 | ---     | ---
`contributor`       | string  | Contributor name
`region`            | string  | World Bank geographic region (blank for non-country contributors)
`year`              | integer | Year the contribution applies to
`income_group`      | string  | World Bank income classification (blank for non-country contributors)
`file`              | string  | WHO's original published PDF the row was extracted from (e.g. `A72_INF5-en.pdf` for 2018) — not the intermediate `WHO_voluntary_contributions_YYYY.csv` this pipeline extracted from it. 2013 is the one exception: it comes from `who_revenue2013.csv`, a different (non-WHA-report) data source, so there's no PDF to name
`category`          | string  | Which original wide-table column this row came from, e.g. `core_voluntary_contributions_account`, `total_voluntary_contributions`
`category_type`     | string  | `component` (an additive line-item) or `summary` (the aggregate `total_voluntary_contributions`) — sum only `component` rows to avoid double-counting. Every contributor-year has exactly one `summary` row: the report's own stated total where one exists, otherwise derived as the sum of that contributor-year's components
`USD_nominal`       | float   | As-reported dollar amount for that category, unadjusted
`USD_2024_adjusted` | float   | `USD_nominal` multiplied by the year's inflation factor from `inflation_adjust2024.csv` (2024 rows use factor 1.0)

The source for 2008 is `WHO_voluntary_contributions_2008.csv`, which is not
included with this dataset. It uses a report structure unlike any other year:
one main table
(`voluntary_contributions_specified`/`voluntary_contributions_core`) plus nine
separate fund-specific sections, each with their own contributor list and
WHO-reported subtotal. Four of those nine sections map onto categories already
used by later years (TDR, HRP, Stop TB Partnership, Water Supply and Sanitation
Collaborative Council); the other five are 2008-only categories not present in
any other year:

* `stop_tb_partnership_global_drug_facility`
* `who_framework_convention_on_tobacco_control`
* `other_partnerships_2008`
* `revolving_fund_for_teaching_and_laboratory_equipment`

All ten sections' extracted sums were checked against WHO's own reported
subtotal for that section and match exactly (main table: $972,931,392; grand
total across all sections: $1,111,325,223).


### Voluntary Contributions

The file `voluntary_contributions.parquet`/`.rds` contains data on voluntary
contributions to the WHO (World Health Organization) from member states for the
years 2009-2023, except for 2013. These voluntary contributions are broken down
into contributions earmarked for specific purposes and programs. In addition,
this data includes the total assessed contributions for member states per year
for years 2014-2022.

See [Voluntary Contributions (long)](#voluntary-contributions-long) above for
another version with additional cleaning and reconciliation. The long-format
table above additionally covers 2008 (not present in this file), sourced from a
dedicated 2008 extraction with its own set of fund-specific categories not used
in any other year.

Property            | Value
---                 | ---
Source              | WHO voluntary contributions reports (A68, A69, A70, A71, A72, A73, A74, A75, A76)
Years covered       | 2009-2024 (2013 has totals only)
Unit of observation | One row per member state per year
Currency            | US dollars, nominal (as reported)

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

Tabular data was originally extracted from WHO World Health Assembly PDF
documents using a semi-automated pipeline. For each source document, pages
containing contribution tables were converted to JPEG images at 300 DPI using
pdftocairo 26.02.0 ([Poppler][]). The resulting images were then uploaded to
Claude Sonnet 4.5 ([Anthropic][]), which extracted the tabular data and
returned it as CSV strings. Extracted CSVs were manually reviewed and saved. 

[Poppler]: https://poppler.freedesktop.org/
[Anthropic]: https://www.anthropic.com/

Extracted data were also cleaned and standardized using a Python processing
pipeline. Contributor names were standardized to World Bank country names using
fuzzy string matching ([RapidFuzz][]). World Bank region and income group
classifications were merged in based on matched country names.

[RapidFuzz]: https://rapidfuzz.github.io/RapidFuzz/

On 2026-08-18, we used Claude to generate a new *deterministic, model-free PDF
extraction pipeline* based on the [pdfplumber][] package. This pipeline
consists of the files:

[pdfplumber]: https://github.com/jsvine/pdfplumber

* `build_long_format.py`
*_`build_assessed_contributions.py`

These were used to build the long-format voluntary contributions table
described above. These are preferred over the original vision-based extraction
wherever a source PDF/CSV is available, since it's exact/reproducible rather
than model-dependent, and easier to debug and verify against the source PDF
page-by-page. See `docs/history/` for a changelog with more details.

([back to top][top])
