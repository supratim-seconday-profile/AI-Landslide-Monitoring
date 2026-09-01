import pandas as pd
import numpy as np


INPUT = "data/processed/sih_ml_dataset_684.csv"


FEATURES = [
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
    "NDVI",
    "NDMI",
    "NDWI",
    "NBR",
    "hls_image_count",
    "hls_valid_image_count",
]

TARGET = "landslide_target"


print("=" * 70)
print("             SIH ML FEATURE ANALYSIS")
print("=" * 70)


# ==========================================================
# LOAD
# ==========================================================

df = pd.read_csv(INPUT)

print()
print("Rows:", len(df))
print("Features:", len(FEATURES))


# ==========================================================
# CLASS DISTRIBUTION
# ==========================================================

print()
print("--- CLASS DISTRIBUTION ---")

print(
    df[TARGET]
    .value_counts()
    .sort_index()
)


# ==========================================================
# CLASS-WISE STATISTICS
# ==========================================================

print()
print("--- CLASS-WISE MEAN ---")

means = (
    df.groupby(TARGET)[FEATURES]
    .mean()
    .T
)

print(
    means.to_string()
)


print()
print("--- CLASS-WISE MEDIAN ---")

medians = (
    df.groupby(TARGET)[FEATURES]
    .median()
    .T
)

print(
    medians.to_string()
)


# ==========================================================
# CLASS-WISE STANDARD DEVIATION
# ==========================================================

print()
print("--- CLASS-WISE STANDARD DEVIATION ---")

stds = (
    df.groupby(TARGET)[FEATURES]
    .std()
    .T
)

print(
    stds.to_string()
)


# ==========================================================
# MEAN DIFFERENCE
# ==========================================================

print()
print("--- CLASS MEAN DIFFERENCE ---")

difference = (
    means[1] - means[0]
)

difference_table = pd.DataFrame({
    "background_mean": means[0],
    "landslide_mean": means[1],
    "difference": difference,
    "absolute_difference": difference.abs(),
})

difference_table = difference_table.sort_values(
    "absolute_difference",
    ascending=False
)

print(
    difference_table.to_string()
)


# ==========================================================
# CORRELATION
# ==========================================================

print()
print("--- FEATURE CORRELATION ---")

corr = df[FEATURES].corr()

print(
    corr.round(3).to_string()
)


# ==========================================================
# HIGH CORRELATION PAIRS
# ==========================================================

print()
print("--- HIGH CORRELATION PAIRS (|r| >= 0.90) ---")

pairs = []

for i in range(len(FEATURES)):

    for j in range(i + 1, len(FEATURES)):

        a = FEATURES[i]
        b = FEATURES[j]

        r = corr.loc[a, b]

        if abs(r) >= 0.90:

            pairs.append(
                (a, b, r)
            )


if pairs:

    for a, b, r in sorted(
        pairs,
        key=lambda x: abs(x[2]),
        reverse=True
    ):

        print(
            f"{a:25s} <-> {b:25s} "
            f"r={r:.4f}"
        )

else:

    print("No feature pairs above |r| >= 0.90")


# ==========================================================
# FEATURE RANGE
# ==========================================================

print()
print("--- FEATURE RANGE ---")

ranges = df[FEATURES].agg(
    ["min", "max", "mean", "std"]
).T

print(
    ranges.to_string()
)


# ==========================================================
# FINISHED
# ==========================================================

print()
print("=" * 70)
print("             FEATURE ANALYSIS COMPLETE")
print("=" * 70)