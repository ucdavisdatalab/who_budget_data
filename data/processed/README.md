## group1.parquet
Description: This data set contains data on assessed contributions determined by the WHO (World Health Organization) for different member states for the years 2005, 2007, and 2008. 
Source: WHO assessed contributions reports (A58, A60, A61)
Years covered: 2005, 2007, 2008
Unit of observation: one row per member state per year
Currency: USD, inflation-adjusted to 2024

| variable | type | description |
|---|---|---|
| contributor | string | WHO member state name, standardized to World Bank country names |
| region | string | World Bank geographic region |
| year | integer | Report year |
| income_group | string | World Bank income classification |
| file | string | Source file for row |
| credits_start_of_year | integer | Credit balance carried over from the previous year |
| current_year_assessment | integer | Amount assessed to the member state for the current year |
| total_amount_outstanding_start_of_year | integer | Total unpaid balance owed by the member state at the start of the year |
| receipts_credits_given_during_current_year | integer | Credits applied to balance during the current year |
| balances_due_from_1987_to_second_previous_year | integer | Arrears owed from 1987 up to two years prior to the current report year |
| balances_due_previous_year | integer | Arrears owed from the previous year |
| balances_due_current_year | integer | Unpaid balance remaining for the current report year |
| balances_due_total | integer | Sum of all outstanding balances across all periods |


## group2.parquet
Description: This data set contains data on voluntary contributions to the WHO (World Health Organization) from member states for the years 2009-2023, except for 2013. These voluntary contributions are broken down into contributions earmarked for specific purposes and programs. In addition, this data set includes the total assessed contributions for member states per year for years 2014-2022. 

Source: WHO voluntary contributions reports (A68, A69, A70, A71, A72, A73, A74, A75, A76)
Years covered: 2009, 2010, 2011, 2012, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023
Unit of observation: one row per member state per year
Currency: USD, inflation-adjusted to 2024

| variable | type | description |
|---|---|---|
| contributor | string | WHO member state name, standardized to World Bank country names |
| region | string | World Bank geographic region |
| year | integer | Report year |
| income_group | string | World Bank income classification |
| file | string | Source file for row |
| voluntary_contributions_specified | float | Total voluntary contributions earmarked for a specific purpose |
| special_programme_for_research_and_training_in_tropical_diseases | float | Contributions to the UNICEF/UNDP/WHO/World Bank Special Programme for Research and Training in Tropical Diseases (TDR) |
| stop_tb_partnership | float | Contributions to the Stop TB Partnership |
| special_programme_on_research_development_and_training_in_human_reproduction | float | Contributions to the WHO Special Programme of Research, Development and Research Training in Human Reproduction (HRP) |
| roll_back_malaria_partnership | float | Contributions to the Roll Back Malaria Partnership |
| water_supply_and_sanitation_collaborative_council | float | Contributions to the Water Supply and Sanitation Collaborative Council (WSSCC) |
| contingency_fund_for_emergencies | float | Contributions to the WHO Contingency Fund for Emergencies (CFE) |
| special_programmes_and_collaborative_arrangements | float | Contributions to other special programmes and collaborative arrangements not listed separately |
| outbreak_and_crisis_response | float | Contributions designated for WHO outbreak and crisis response activities |
| core_voluntary_contributions_account | float | Unearmarked voluntary contributions to the WHO Core Voluntary Contributions Account (CVCA) |
| voluntary_contributions_core | float | Core voluntary contributions not designated to a specific programme |
| total_voluntary_contributions | float | Total voluntary contributions across all categories |
| assessed_contributions | float | Mandatory assessed contributions owed by WHO member states based on the UN scale of assessments |