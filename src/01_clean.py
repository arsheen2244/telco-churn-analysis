"""Step 1: audit and clean the raw Telco churn data.

Usage: python -I src/01_clean.py data/telco_raw.csv data/telco_clean.csv
"""
import sys

import pandas as pd

raw_path, out_path = sys.argv[1], sys.argv[2]
df = pd.read_csv(raw_path, dtype=str)

print("=== DATA QUALITY AUDIT ===")
print(f"Rows: {len(df):,} | Columns: {df.shape[1]}")
print(f"Duplicate customerIDs: {df['customerID'].duplicated().sum()}")

# Blank strings hide as 'non-null' in raw CSVs, so check them explicitly
blank = (df.apply(lambda s: s.str.strip() == "")).sum()
print("Blank-string cells per column (non-zero only):")
print(blank[blank > 0].to_string() if (blank > 0).any() else "  none")

# ---- cleaning ----
df["tenure"] = pd.to_numeric(df["tenure"])
df["MonthlyCharges"] = pd.to_numeric(df["MonthlyCharges"])
df["SeniorCitizen"] = df["SeniorCitizen"].map({"0": "No", "1": "Yes"})

# TotalCharges: blanks belong to brand-new customers (tenure = 0) who have not been billed yet
df["TotalCharges"] = pd.to_numeric(df["TotalCharges"].str.strip(), errors="coerce")
new_customers = df["TotalCharges"].isna()
# errors="coerce" would also hide any non-numeric junk, so confirm only the audited blanks were affected
assert new_customers.sum() == blank["TotalCharges"], "unexpected non-numeric TotalCharges values"
print(f"\nTotalCharges missing: {new_customers.sum()} rows")
print(f"  of which tenure == 0: {(df.loc[new_customers, 'tenure'] == 0).sum()}")
df.loc[new_customers, "TotalCharges"] = 0.0

# Collapse 'No internet service' / 'No phone service' into 'No' for add-on flags
addons = ["OnlineSecurity", "OnlineBackup", "DeviceProtection",
          "TechSupport", "StreamingTV", "StreamingMovies"]
for col in addons:
    df[col] = df[col].replace({"No internet service": "No"})
df["MultipleLines"] = df["MultipleLines"].replace({"No phone service": "No"})

# ---- derived columns ----
df["churn_flag"] = (df["Churn"] == "Yes").astype(int)
df["tenure_band"] = pd.cut(
    df["tenure"], bins=[-1, 12, 24, 48, 72],
    labels=["0-12 mo", "13-24 mo", "25-48 mo", "49-72 mo"],
).astype(str)
df["charge_tier"] = pd.cut(
    df["MonthlyCharges"], bins=[0, 35, 70, 90, 200],
    labels=["Low (<=35)", "Mid (35-70)", "High (70-90)", "Premium (>90)"],
).astype(str)
df["num_addons"] = sum((df[c] == "Yes").astype(int) for c in addons)
df["has_internet"] = (df["InternetService"] != "No").astype(int)
df["auto_pay"] = df["PaymentMethod"].str.contains("automatic").map({True: "Yes", False: "No"})

df.to_csv(out_path, index=False)
print(f"\nCleaned file written: {out_path}  ({len(df):,} rows, {df.shape[1]} columns)")
print(f"Overall churn rate: {df['churn_flag'].mean():.1%}")
