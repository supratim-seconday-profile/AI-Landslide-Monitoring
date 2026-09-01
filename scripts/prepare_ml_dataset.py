import pandas as pd
import numpy as np


# ==========================================================
# CONFIGURATION
# ==========================================================

INPUT = "data/processed/sih_ml_dataset_684_raw.csv"

OUTPUT = "data/processed/sih_ml_dataset_684.csv"

BANDS = [
    "B2",
    "B3",
    "B4",
    "B5",
    "B6",
    "B7",
    "B8",
    "B8A",
    "B11",
    "B12",
]

INDICES = [
    "NDVI",
    "NDMI",
    "NDWI",
    "NBR",
]

QUALITY_FEATURES = [
    "hls_image_count",
    "hls_valid_image_count",
]

ID_COLUMNS = [
    "record_id",
]

TARGET = "landslide_target"


# ==========================================================
# LOAD DATA
# ==========================================================

print("=" * 60)
print("        SIH ML DATASET PREPARATION")
print("=" * 60)

df = pd.read_csv(INPUT)

print()
print("Input rows:", len(df))
print("Input columns:", len(df.columns))


# ==========================================================
# CHECK TARGET
# ==========================================================

print()
print("--- TARGET CHECK ---")

print(df[TARGET].value_counts(dropna=False))


if df[TARGET].isna().any():
    raise ValueError("Target contains missing values.")


if set(df[TARGET].unique()) != {0, 1}:
    raise ValueError("Target must contain exactly 0 and 1.")


# ==========================================================
# CHECK REQUIRED FEATURES
# ==========================================================

required = BANDS + INDICES + QUALITY_FEATURES + ID_COLUMNS

missing_columns = [
    c for c in required
    if c not in df.columns
]

if missing_columns:

    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )


# ==========================================================
# CHECK DUPLICATE IDS
# ==========================================================

print()
print("--- ID CHECK ---")

duplicate_ids = df["record_id"].duplicated().sum()

print("Duplicate record IDs:", duplicate_ids)

if duplicate_ids != 0:

    raise ValueError(
        "Duplicate record IDs detected."
    )


# ==========================================================
# CHECK MISSING VALUES
# ==========================================================

print()
print("--- MISSING VALUES BEFORE CLEANING ---")

missing = df[required].isna().sum()

print(
    missing[missing > 0].to_string()
    if missing.sum() > 0
    else "No missing values"
)


# ==========================================================
# CONVERT NUMERIC FEATURES
# ==========================================================

for column in BANDS + INDICES + QUALITY_FEATURES:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# ==========================================================
# CHECK FINITE VALUES
# ==========================================================

print()
print("--- NON-FINITE VALUES ---")

numeric_columns = (
    BANDS
    + INDICES
    + QUALITY_FEATURES
)

nonfinite = (
    ~np.isfinite(df[numeric_columns])
).sum()

print(
    nonfinite[nonfinite > 0].to_string()
    if nonfinite.sum() > 0
    else "No non-finite values"
)


# ==========================================================
# HANDLE DERIVED INDICES
#
# NDVI, NDMI, NDWI and NBR theoretically lie within
# [-1, +1].
#
# We clip ONLY the derived indices.
# Original spectral bands are NOT clipped here.
# ==========================================================

print()
print("--- INDEX RANGE BEFORE CLEANING ---")

for column in INDICES:

    print(
        f"{column}: "
        f"min={df[column].min():.6f}, "
        f"max={df[column].max():.6f}"
    )


for column in INDICES:

    df[column] = df[column].clip(
        lower=-1.0,
        upper=1.0
    )


print()
print("--- INDEX RANGE AFTER CLEANING ---")

for column in INDICES:

    print(
        f"{column}: "
        f"min={df[column].min():.6f}, "
        f"max={df[column].max():.6f}"
    )


# ==========================================================
# BAND QUALITY REPORT
#
# IMPORTANT:
# We DO NOT clip spectral bands.
# We simply report their range.
# ==========================================================

print()
print("--- SPECTRAL BAND RANGES ---")

for column in BANDS:

    print(
        f"{column:5s} "
        f"min={df[column].min():.6f} "
        f"max={df[column].max():.6f}"
    )


# ==========================================================
# BUILD ML DATASET
# ==========================================================

final_columns = (
    ID_COLUMNS
    + BANDS
    + INDICES
    + QUALITY_FEATURES
    + [TARGET]
)

ml = df[final_columns].copy()


# ==========================================================
# FINAL MISSING CHECK
# ==========================================================

print()
print("--- FINAL MISSING CHECK ---")

missing_final = ml.isna().sum()

if missing_final.sum() == 0:

    print("No missing values.")

else:

    print(
        missing_final[
            missing_final > 0
        ].to_string()
    )

    raise ValueError(
        "Missing values remain in ML dataset."
    )


# ==========================================================
# FINAL FINITE CHECK
# ==========================================================

print()
print("--- FINAL FINITE CHECK ---")

feature_columns = (
    BANDS
    + INDICES
    + QUALITY_FEATURES
)

if np.isfinite(
    ml[feature_columns].to_numpy()
).all():

    print("All numeric values are finite.")

else:

    raise ValueError(
        "Non-finite values remain."
    )


# ==========================================================
# TARGET BALANCE
# ==========================================================

print()
print("--- FINAL TARGET DISTRIBUTION ---")

print(
    ml[TARGET]
    .value_counts()
    .sort_index()
)


# ==========================================================
# SAVE
# ==========================================================

ml.to_csv(
    OUTPUT,
    index=False
)


# ==========================================================
# FINAL SUMMARY
# ==========================================================

print()
print("=" * 60)
print("        ML DATASET CREATED SUCCESSFULLY")
print("=" * 60)

print()
print("Rows:", len(ml))
print("Columns:", len(ml.columns))

print()
print("Features used by model:")

for column in BANDS + INDICES + QUALITY_FEATURES:

    print("  -", column)

print()
print("Identifier:")
print("  - record_id")

print()
print("Target:")
print("  - landslide_target")

print()
print("Saved:")
print(OUTPUT)

print()
print("=" * 60)