from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "base_landslide_dataset.csv"
)

MODEL_PATH = (
    BASE_DIR
    / "ml"
    / "landslide_model.pkl"
)


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading dataset...")

df = pd.read_csv(DATA_PATH)

print("Dataset shape:", df.shape)


# ============================================================
# CLEAN COLUMN NAMES
# ============================================================

df.columns = (
    df.columns
    .astype(str)
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
    .str.replace("-", "_")
)


# ============================================================
# DISPLAY COLUMNS
# ============================================================

print("\nAvailable columns:")

for column in df.columns:
    print(" -", column)


# ============================================================
# FEATURES
# ============================================================
#
# We intentionally DON'T use:
#
# record_id
# event_date
# event_time_raw
# source
# source_code
# slide_id
# slide_no
# landslide_name
# location
# landslide_target
#
# These are identifiers/descriptions rather than useful
# numerical environmental predictors.
#
# ============================================================

candidate_features = [

    "latitude",
    "longitude",
    "year",
    "event_month",
    "event_day_of_year",
    "rainfall_24h_mm",
    "casualty",
    "has_casualty",
    "road_affected_flag"
]


# ============================================================
# SELECT FEATURES THAT ACTUALLY EXIST
# ============================================================

features = [
    column
    for column in candidate_features
    if column in df.columns
]


print("\nFeatures used:")

for feature in features:
    print(" -", feature)


if not features:

    raise ValueError(
        "No usable numerical features were found."
    )


# ============================================================
# CREATE X
# ============================================================

X = df[features].copy()


# ============================================================
# CONVERT TO NUMERIC
# ============================================================

for column in X.columns:

    X[column] = pd.to_numeric(
        X[column],
        errors="coerce"
    )


# ============================================================
# REMOVE COMPLETELY EMPTY FEATURES
# ============================================================

empty_columns = [
    column
    for column in X.columns
    if X[column].isna().all()
]


if empty_columns:

    print(
        "\nRemoving empty features:",
        empty_columns
    )

    X = X.drop(
        columns=empty_columns
    )

    features = [
        column
        for column in features
        if column not in empty_columns
    ]


# ============================================================
# PIPELINE
# ============================================================

pipeline = Pipeline(
    steps=[

        (
            "imputer",
            SimpleImputer(
                strategy="median"
            )
        ),

        (
            "scaler",
            StandardScaler()
        ),

        (
            "model",
            IsolationForest(

                n_estimators=300,

                contamination=0.10,

                random_state=42,

                n_jobs=-1
            )
        )
    ]
)


# ============================================================
# TRAIN
# ============================================================

print("\n====================================")
print("Training anomaly-based risk model")
print("====================================")

pipeline.fit(X)


# ============================================================
# SAVE MODEL
# ============================================================

model_data = {

    "model": pipeline,

    "features": features,

    "model_type": "isolation_forest",

    "description": (
        "Landslide event anomaly/risk model. "
        "Current dataset contains only positive "
        "landslide events and therefore cannot "
        "train a binary occurrence classifier."
    )
}


joblib.dump(
    model_data,
    MODEL_PATH
)


# ============================================================
# MODEL SCORE
# ============================================================

predictions = pipeline.predict(X)

anomaly_scores = pipeline.decision_function(X)


print("\nModel training completed.")

print(
    "Records analysed:",
    len(X)
)

print(
    "Features:",
    len(features)
)

print(
    "Anomalous records:",
    sum(predictions == -1)
)

print(
    "Normal records:",
    sum(predictions == 1)
)


print("\nModel saved to:")

print(MODEL_PATH)


print("\n====================================")
print("IMPORTANT")
print("====================================")

print(
    "This is NOT a supervised probability "
    "of landslide occurrence."
)

print(
    "It identifies unusual/high-risk patterns "
    "within the available landslide-event dataset."
)