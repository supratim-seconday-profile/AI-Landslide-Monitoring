import pandas as pd
import numpy as np


INPUT = "data/processed/sih_ml_dataset_684_raw.csv"

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


print("=" * 60)
print("        SIH HLS VALUE QUALITY INVESTIGATION")
print("=" * 60)


# ==========================================================
# LOAD DATA
# ==========================================================

df = pd.read_csv(INPUT)

print()
print("Rows:", len(df))
print("Columns:", len(df.columns))


# ==========================================================
# BAND OUT-OF-RANGE CHECK
# Expected reflectance range: 0 to 1
# ==========================================================

print()
print("--- BAND OUT-OF-RANGE COUNTS ---")

bad_band = (df[BANDS] < 0) | (df[BANDS] > 1)

band_counts = bad_band.sum().sort_values(ascending=False)

print(band_counts.to_string())

print()
print("Total bad band values:", int(bad_band.sum().sum()))


# ==========================================================
# BAD VALUES BY TARGET
# ==========================================================

df["bad_band_count"] = bad_band.sum(axis=1)

print()
print("--- BAD VALUES BY TARGET ---")

target_summary = (
    df.groupby("landslide_target")["bad_band_count"]
    .agg(["count", "sum", "mean", "max"])
)

print(target_summary.to_string())


# ==========================================================
# NUMBER OF AFFECTED ROWS
# ==========================================================

bad_rows = df[df["bad_band_count"] > 0].copy()

print()
print("--- ROWS WITH BAD BANDS ---")

print("Rows affected:", len(bad_rows))


# ==========================================================
# SHOW AFFECTED ROWS
# ==========================================================

print()

show_columns = [
    "record_id",
    "landslide_target",
] + BANDS

print(
    bad_rows[show_columns]
    .head(30)
    .to_string(index=False)
)


# ==========================================================
# INDEX RANGE CHECK
# Expected range: -1 to +1
# ==========================================================

print()
print("--- INDEX VIOLATIONS ---")

for column in INDICES:

    invalid = (
        (df[column] < -1)
        | (df[column] > 1)
    )

    print(
        f"{column}: {int(invalid.sum())} violations"
    )


# ==========================================================
# EXTREME VALUES
# ==========================================================

print()
print("--- EXTREME VALUES ---")

for column in BANDS + INDICES:

    minimum = df[column].min()
    maximum = df[column].max()

    print(
        f"{column:5s} "
        f"min={minimum:.6f} "
        f"max={maximum:.6f}"
    )


# ==========================================================
# BAD BAND VALUES BY CLASS
# ==========================================================

print()
print("--- BAD BAND VALUES BY CLASS ---")

for target in sorted(df["landslide_target"].unique()):

    subset = df[df["landslide_target"] == target]

    bad = (
        (subset[BANDS] < 0)
        | (subset[BANDS] > 1)
    )

    print(
        f"Target {target}: "
        f"{int(bad.sum().sum())} bad values "
        f"across {int((bad.sum(axis=1) > 0).sum())} rows"
    )


# ==========================================================
# CLEAN TEMPORARY COLUMN
# ==========================================================

df.drop(columns=["bad_band_count"], inplace=True)


# ==========================================================
# FINISHED
# ==========================================================

print()
print("=" * 60)
print("INVESTIGATION COMPLETE")
print("=" * 60)