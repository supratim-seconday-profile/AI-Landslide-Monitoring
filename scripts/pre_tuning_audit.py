import os
import numpy as np
import pandas as pd


# ============================================================
# CONFIG
# ============================================================

DATASET = "data/processed/sih_ml_dataset_684.csv"

RESULT_DIR = "data/processed/model_results"

os.makedirs(
    RESULT_DIR,
    exist_ok=True
)


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


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("              SIH PRE-TUNING DATA AUDIT")
print("=" * 70)


# ============================================================
# LOAD
# ============================================================

df = pd.read_csv(
    DATASET
)


print()
print("--- DATASET ---")

print(
    "Rows:",
    len(df)
)

print(
    "Columns:",
    len(df.columns)
)


# ============================================================
# TARGET
# ============================================================

print()
print("--- TARGET ---")

print(
    df[TARGET]
    .value_counts()
    .sort_index()
)


# ============================================================
# FEATURE SUMMARY
# ============================================================

print()
print("--- FEATURE SUMMARY ---")

summary = df[
    FEATURES
].describe().T

summary[
    "missing"
] = df[
    FEATURES
].isna().sum()

summary[
    "unique"
] = df[
    FEATURES
].nunique()

print(
    summary[
        [
            "count",
            "unique",
            "missing",
            "mean",
            "std",
            "min",
            "25%",
            "50%",
            "75%",
            "max",
        ]
    ].to_string()
)


# ============================================================
# CLASS-WISE MEANS
# ============================================================

print()
print("--- CLASS-WISE MEANS ---")

class_means = (
    df.groupby(TARGET)[FEATURES]
    .mean()
    .T
)

print(
    class_means.to_string()
)

class_means.to_csv(
    os.path.join(
        RESULT_DIR,
        "classwise_feature_means.csv"
    )
)


# ============================================================
# CLASS-WISE MEDIANS
# ============================================================

print()
print("--- CLASS-WISE MEDIANS ---")

class_medians = (
    df.groupby(TARGET)[FEATURES]
    .median()
    .T
)

print(
    class_medians.to_string()
)

class_medians.to_csv(
    os.path.join(
        RESULT_DIR,
        "classwise_feature_medians.csv"
    )
)


# ============================================================
# SPECTRAL RANGE CHECK
# ============================================================

bands = [
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


print()
print("--- SPECTRAL BAND QUALITY ---")

band_quality = []

for band in bands:

    values = df[band]

    below_zero = (
        values < 0
    ).sum()

    above_one = (
        values > 1
    ).sum()

    band_quality.append(
        {
            "feature": band,
            "below_0": int(below_zero),
            "above_1": int(above_one),
            "total_out_of_range":
                int(
                    below_zero +
                    above_one
                ),
        }
    )

band_quality_df = pd.DataFrame(
    band_quality
)

print(
    band_quality_df.to_string(
        index=False
    )
)

band_quality_df.to_csv(
    os.path.join(
        RESULT_DIR,
        "spectral_band_quality.csv"
    ),
    index=False
)


# ============================================================
# INDEX RANGE CHECK
# ============================================================

indices = [
    "NDVI",
    "NDMI",
    "NDWI",
    "NBR",
]


print()
print("--- INDEX QUALITY ---")

for feature in indices:

    values = df[feature]

    bad = (
        (values < -1) |
        (values > 1)
    )

    print(
        feature,
        "violations:",
        int(bad.sum()),
        "min:",
        values.min(),
        "max:",
        values.max()
    )


# ============================================================
# CORRELATION MATRIX
# ============================================================

print()
print("--- FEATURE CORRELATION ---")

corr = df[
    FEATURES
].corr()

corr.to_csv(
    os.path.join(
        RESULT_DIR,
        "feature_correlation_matrix.csv"
    )
)

print(
    "Correlation matrix saved."
)


# ============================================================
# HIGH CORRELATION PAIRS
# ============================================================

print()
print("--- HIGH CORRELATION PAIRS ---")

pairs = []

for i in range(
    len(FEATURES)
):

    for j in range(
        i + 1,
        len(FEATURES)
    ):

        a = FEATURES[i]
        b = FEATURES[j]

        value = corr.loc[
            a,
            b
        ]

        if abs(value) >= 0.90:

            pairs.append(
                {
                    "feature_1": a,
                    "feature_2": b,
                    "correlation": value,
                }
            )


pairs_df = pd.DataFrame(
    pairs
)

if len(pairs_df) > 0:

    pairs_df = pairs_df.sort_values(
        "correlation",
        key=lambda x: abs(x),
        ascending=False
    )

    print(
        pairs_df.to_string(
            index=False
        )
    )

else:

    print(
        "No feature pairs with |correlation| >= 0.90"
    )


pairs_df.to_csv(
    os.path.join(
        RESULT_DIR,
        "high_correlation_pairs.csv"
    ),
    index=False
)


# ============================================================
# HLS SAMPLING FEATURES
# ============================================================

print()
print("--- HLS SAMPLING FEATURES BY CLASS ---")

sampling_features = [
    "hls_image_count",
    "hls_valid_image_count",
]


sampling_summary = (
    df.groupby(TARGET)[sampling_features]
    .agg(
        [
            "mean",
            "median",
            "std",
            "min",
            "max",
        ]
    )
)

print(
    sampling_summary.to_string()
)


# ============================================================
# HLS SAMPLING DIFFERENCE
# ============================================================

print()
print("--- HLS SAMPLING CLASS DIFFERENCE ---")

for feature in sampling_features:

    means = df.groupby(
        TARGET
    )[feature].mean()

    difference = (
        means.loc[1] -
        means.loc[0]
    )

    print(
        feature,
        "class1 - class0 =",
        difference
    )


# ============================================================
# UNIQUE VALUE CHECK
# ============================================================

print()
print("--- UNIQUE VALUE COUNTS ---")

for feature in FEATURES:

    print(
        feature,
        "unique =",
        df[feature].nunique()
    )


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print("              PRE-TUNING AUDIT COMPLETE")
print("=" * 70)

print()
print(
    "Results saved in:"
)

print(
    RESULT_DIR
)

print()
print("=" * 70)