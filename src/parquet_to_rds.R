library(arrow)

assessed <- read_parquet("data/processed/assessed_contributions.parquet")
voluntary <- read_parquet("data/processed/voluntary_contributions.parquet")

saveRDS(assessed, "data/processed/assessed_contributions.rds")
saveRDS(voluntary, "data/processed/voluntary_contributions.rds")