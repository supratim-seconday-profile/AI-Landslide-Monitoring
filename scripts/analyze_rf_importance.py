import os
import joblib
import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_FILE = "models/random_forest.joblib"
TRAIN_FILE = "data/processed/ml_train.csv"

OUTPUT_DIR = "data/processed/model_results"
OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "random_forest_feature_importance.csv"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


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


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("             SIH RANDOM FOREST FEATURE IMPORTANCE")
print("=" * 70)


# ============================================================
# LOAD MODEL
# ============================================================

model = joblib.load(MODEL_FILE)

print()
print("Model loaded:")
print(MODEL_FILE)


# ============================================================
# CHECK MODEL
# ============================================================

if not hasattr(model, "feature_importances_"):
    raise ValueError(
        "Loaded model does not provide feature_importances_."
    )


importance = model.feature_importances_


if len(importance) != len(FEATURES):
    raise ValueError(
        "Number of feature importances does not match feature list."
    )


# ============================================================
# CREATE TABLE
# ============================================================

result = pd.DataFrame({
    "feature": FEATURES,
    "importance": importance
})


result = result.sort_values(
    "importance",
    ascending=False
).reset_index(drop=True)


result["importance_percent"] = (
    result["importance"] * 100
)


# ============================================================
# PRINT
# ============================================================

print()
print("--- FEATURE IMPORTANCE ---")

print(
    result.to_string(
        index=False,
        formatters={
            "importance":
                lambda x: f"{x:.6f}",

            "importance_percent":
                lambda x: f"{x:.2f}%"
        }
    )
)


# ============================================================
# CUMULATIVE IMPORTANCE
# ============================================================

result["cumulative_importance"] = (
    result["importance"].cumsum()
)

print()
print("--- CUMULATIVE IMPORTANCE ---")

print(
    result[
        [
            "feature",
            "importance",
            "cumulative_importance"
        ]
    ].to_string(
        index=False,
        formatters={
            "importance":
                lambda x: f"{x:.6f}",

            "cumulative_importance":
                lambda x: f"{x:.6f}"
        }
    )
)


# ============================================================
# TOP FEATURES
# ============================================================

print()
print("--- TOP 5 FEATURES ---")

for i, row in result.head(5).iterrows():

    print(
        f"{i + 1}. "
        f"{row['feature']} "
        f"-> "
        f"{row['importance_percent']:.2f}%"
    )


# ============================================================
# SAVE
# ============================================================

result.to_csv(
    OUTPUT_FILE,
    index=False
)


print()
print("=" * 70)
print("FEATURE IMPORTANCE ANALYSIS COMPLETE")
print("=" * 70)

print()
print("Saved:")
print(OUTPUT_FILE)

print("=" * 70)