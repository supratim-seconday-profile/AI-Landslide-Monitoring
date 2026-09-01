import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# FILES
# ============================================================

INPUT_FILE = Path(
    "data/processed/landslide_dem_features.csv"
)

OUTPUT_FILE = Path(
    "data/processed/landslide_rainfall_features.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

print("Loading dataset...")

df = pd.read_csv(
    INPUT_FILE
)

print(
    f"Loaded {len(df)} records."
)


# ============================================================
# DATE
# ============================================================

df["event_date"] = pd.to_datetime(
    df["event_date"],
    errors="coerce"
)


# ============================================================
# EXISTING RAINFALL
# ============================================================

df["rainfall_24h_mm"] = pd.to_numeric(
    df["rainfall_24h_mm"],
    errors="coerce"
)


# ============================================================
# CREATE RAINFALL FEATURE COLUMNS
# ============================================================

rainfall_columns = [
    "rainfall_1h_mm",
    "rainfall_6h_mm",
    "rainfall_12h_mm",
    "rainfall_48h_mm",
    "rainfall_72h_mm",
    "rainfall_7d_mm"
]


for column in rainfall_columns:

    if column not in df.columns:

        df[column] = np.nan


# ============================================================
# RAINFALL QUALITY FLAGS
# ============================================================

df["rainfall_24h_available"] = (
    df["rainfall_24h_mm"]
    .notna()
    .astype(int)
)


df["event_date_available"] = (
    df["event_date"]
    .notna()
    .astype(int)
)


# ============================================================
# EXISTING 24-HOUR RAINFALL CATEGORIES
# ============================================================

def classify_rainfall(value):

    if pd.isna(value):
        return "UNKNOWN"

    if value < 25:
        return "LOW"

    elif value < 50:
        return "MODERATE"

    elif value < 100:
        return "HIGH"

    else:
        return "VERY_HIGH"


df["rainfall_24h_category"] = (
    df["rainfall_24h_mm"]
    .apply(classify_rainfall)
)


# ============================================================
# SAVE
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)


df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n==========================================")
print("RAINFALL FEATURE TEMPLATE CREATED")
print("==========================================")

print(
    "Records:",
    len(df)
)

print(
    "24h rainfall available:",
    df["rainfall_24h_mm"].notna().sum()
)

print(
    "Event dates available:",
    df["event_date"].notna().sum()
)

print(
    "\nRainfall columns:"
)

for column in [
    "rainfall_1h_mm",
    "rainfall_6h_mm",
    "rainfall_12h_mm",
    "rainfall_24h_mm",
    "rainfall_48h_mm",
    "rainfall_72h_mm",
    "rainfall_7d_mm"
]:

    print(
        f"{column}: "
        f"{df[column].notna().sum()} available"
    )


print(
    "\nSaved:",
    OUTPUT_FILE
)