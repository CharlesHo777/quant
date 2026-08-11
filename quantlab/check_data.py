# check_data.py — sanity checks before trusting the data
import pandas as pd
px = pd.read_parquet("data/close.parquet")
print("Date range:", px.index.min().date(), "->", px.index.max().date())
print("Symbols:", px.shape[1])
print("\nMost missing data (fraction of days):")
print(px.isna().mean().sort_values(ascending=False).head(5).round(3))
print("\nMost 'stale' series (fraction of zero-move days — a red flag if high):")
print((px.pct_change() == 0).mean().sort_values(ascending=False).head(5).round(3))
