import os
import joblib
import numpy as np
import pandas as pd

from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_FILE = "models/random_forest.joblib"
VAL_FILE = "data/processed/ml_validation.csv"

OUTPUT_DIR = "data/processed/model_results"

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "random_forest_permutation_importance.csv"
)

os.makedirs(
    OUTPUT_DIR,
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


RANDOM_STATE = 2026


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("          SIH RANDOM FOREST PERMUTATION IMPORTANCE")
print("=" * 70)


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(VAL_FILE)

model = joblib.load(MODEL_FILE)


X = df[FEATURES].copy()
y = df[TARGET].copy()


print()
print("Validation rows:", len(df))
print("Features:", len(FEATURES))


# ============================================================
# BASELINE ROC-AUC
# ============================================================

baseline_probability = model.predict_proba(X)[:, 1]

baseline_auc = roc_auc_score(
    y,
    baseline_probability
)


print()
print("--- BASELINE ---")

print(
    f"Validation ROC-AUC: {baseline_auc:.4f}"
)


# ============================================================
# PERMUTATION IMPORTANCE
# ============================================================

print()
print("--- CALCULATING PERMUTATION IMPORTANCE ---")
print("Repeats: 30")


result = permutation_importance(
    model,
    X,
    y,
    scoring="roc_auc",
    n_repeats=30,
    random_state=RANDOM_STATE,
    n_jobs=-1
)


# ============================================================
# CREATE RESULT TABLE
# ============================================================

importance_df = pd.DataFrame({

    "feature": FEATURES,

    "importance_mean":
        result.importances_mean,

    "importance_std":
        result.importances_std,

})


importance_df = importance_df.sort_values(
    "importance_mean",
    ascending=False
).reset_index(drop=True)


# ============================================================
# PRINT RESULTS
# ============================================================

print()
print("=" * 70)
print("             PERMUTATION IMPORTANCE")
print("=" * 70)

print()

for _, row in importance_df.iterrows():

    print(
        f"{row['feature']:25s}"
        f" mean={row['importance_mean']:+.6f}"
        f" std={row['importance_std']:.6f}"
    )


# ============================================================
# TOP FEATURES
# ============================================================

print()
print("--- TOP 10 FEATURES ---")

for i, row in importance_df.head(10).iterrows():

    print(
        f"{i + 1:2d}. "
        f"{row['feature']:25s}"
        f"{row['importance_mean']:+.6f}"
    )


# ============================================================
# NEGATIVE IMPORTANCE
# ============================================================

negative = importance_df[
    importance_df["importance_mean"] < 0
]

print()
print("--- NEGATIVE PERMUTATION IMPORTANCE ---")

if len(negative) == 0:

    print("None")

else:

    for _, row in negative.iterrows():

        print(
            f"{row['feature']:25s}"
            f"{row['importance_mean']:+.6f}"
        )


# ============================================================
# SAVE
# ============================================================

importance_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print("       PERMUTATION IMPORTANCE COMPLETE")
print("=" * 70)

print()
print("Baseline ROC-AUC:")
print(f"{baseline_auc:.4f}")

print()
print("Saved:")
print(OUTPUT_FILE)

print("=" * 70)