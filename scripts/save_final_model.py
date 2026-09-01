import os
import json
import joblib
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


# ============================================================
# SIH FINAL MODEL TRAINING
# ============================================================

print("=" * 70)
print("              SIH FINAL MODEL TRAINING")
print("=" * 70)


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

DATA_PATH = "data/processed/sih_ml_dataset_684.csv"

OUTPUT_DIR = "models/final"

MODEL_PATH = os.path.join(
    OUTPUT_DIR,
    "final_svm_rbf.joblib"
)

FEATURE_PATH = os.path.join(
    OUTPUT_DIR,
    "model_features.json"
)

CONFIG_PATH = os.path.join(
    OUTPUT_DIR,
    "model_config.json"
)


# ------------------------------------------------------------
# FINAL MODEL SETTINGS
# ------------------------------------------------------------

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

THRESHOLD = 0.50


# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------

df = pd.read_csv(DATA_PATH)

print()
print("--- DATASET ---")
print("Rows:", len(df))
print("Columns:", len(df.columns))


# ------------------------------------------------------------
# TARGET CHECK
# ------------------------------------------------------------

target = "landslide_target"

print()
print("--- TARGET ---")
print(df[target].value_counts())


if set(df[target].unique()) != {0, 1}:
    raise ValueError(
        "Target must contain both classes 0 and 1."
    )


# ------------------------------------------------------------
# FEATURE CHECK
# ------------------------------------------------------------

missing_features = [
    feature
    for feature in FEATURES
    if feature not in df.columns
]

if missing_features:
    raise ValueError(
        f"Missing features: {missing_features}"
    )


X = df[FEATURES]
y = df[target]


print()
print("--- FEATURES ---")
print("Number of features:", len(FEATURES))

for feature in FEATURES:
    print(" -", feature)


# ------------------------------------------------------------
# DATA QUALITY
# ------------------------------------------------------------

print()
print("--- DATA QUALITY ---")

print(
    "Missing values:",
    int(X.isna().sum().sum())
)

if X.isna().sum().sum() > 0:
    raise ValueError(
        "Feature data contains missing values."
    )

print(
    "Non-finite values:",
    int((~X.apply(
        lambda col: pd.to_numeric(
            col,
            errors="coerce"
        ).map(
            lambda x: pd.notna(x) and abs(x) != float("inf")
        )
    )).sum().sum())
)


# ------------------------------------------------------------
# FINAL MODEL
# ------------------------------------------------------------

print()
print("=" * 70)
print("                    FINAL MODEL")
print("=" * 70)

model = Pipeline([
    (
        "scaler",
        StandardScaler()
    ),
    (
        "svm",
        SVC(
            kernel="rbf",
            C=1.0,
            gamma="scale",
            probability=True,
            random_state=42
        )
    )
])


print()
print("Algorithm: SVM RBF")
print("Kernel: rbf")
print("C: 1.0")
print("Gamma: scale")
print("Probability: True")
print("Decision threshold:", THRESHOLD)


# ------------------------------------------------------------
# TRAIN ON ALL 684 SAMPLES
# ------------------------------------------------------------

print()
print("--- TRAINING ---")
print("Training rows:", len(X))

model.fit(X, y)

print("Training complete.")


# ------------------------------------------------------------
# TRAINING PROBABILITY CHECK
# ------------------------------------------------------------

probabilities = model.predict_proba(X)[:, 1]

print()
print("--- PROBABILITY CHECK ---")
print(
    "Minimum probability:",
    f"{probabilities.min():.6f}"
)

print(
    "Maximum probability:",
    f"{probabilities.max():.6f}"
)

print(
    "Mean probability:",
    f"{probabilities.mean():.6f}"
)


# ------------------------------------------------------------
# CREATE OUTPUT DIRECTORY
# ------------------------------------------------------------

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ------------------------------------------------------------
# SAVE MODEL
# ------------------------------------------------------------

joblib.dump(
    model,
    MODEL_PATH
)

print()
print("Saved model:")
print(MODEL_PATH)


# ------------------------------------------------------------
# SAVE FEATURES
# ------------------------------------------------------------

with open(
    FEATURE_PATH,
    "w"
) as f:

    json.dump(
        FEATURES,
        f,
        indent=4
    )

print()
print("Saved features:")
print(FEATURE_PATH)


# ------------------------------------------------------------
# SAVE MODEL CONFIGURATION
# ------------------------------------------------------------

config = {
    "model_name": "final_svm_rbf",
    "algorithm": "SVM",
    "kernel": "rbf",
    "C": 1.0,
    "gamma": "scale",
    "probability": True,
    "threshold": THRESHOLD,
    "training_samples": int(len(df)),
    "feature_count": len(FEATURES),
    "features": FEATURES,
    "target": target
}

with open(
    CONFIG_PATH,
    "w"
) as f:

    json.dump(
        config,
        f,
        indent=4
    )

print()
print("Saved configuration:")
print(CONFIG_PATH)


# ------------------------------------------------------------
# FINAL SUMMARY
# ------------------------------------------------------------

print()
print("=" * 70)
print("             FINAL MODEL CREATED SUCCESSFULLY")
print("=" * 70)

print()
print("Training samples:", len(df))
print("Features:", len(FEATURES))
print("Target classes:", sorted(y.unique()))

print()
print("Model:")
print(" - SVM RBF")

print()
print("Threshold:")
print(" -", THRESHOLD)

print()
print("Files:")
print(" -", MODEL_PATH)
print(" -", FEATURE_PATH)
print(" -", CONFIG_PATH)

print()
print("=" * 70)