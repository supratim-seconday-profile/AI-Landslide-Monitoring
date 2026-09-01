import json
from pathlib import Path

import joblib
import pandas as pd


# ============================================================
# SIH LANDSLIDE ML PREDICTOR
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    BASE_DIR
    / "models"
    / "final"
    / "final_svm_rbf.joblib"
)

FEATURE_PATH = (
    BASE_DIR
    / "models"
    / "final"
    / "model_features.json"
)

CONFIG_PATH = (
    BASE_DIR
    / "models"
    / "final"
    / "model_config.json"
)


# ============================================================
# LOAD MODEL
# ============================================================

model = joblib.load(MODEL_PATH)


# ============================================================
# LOAD FEATURES
# ============================================================

with open(FEATURE_PATH, "r") as f:
    FEATURES = json.load(f)


# ============================================================
# LOAD CONFIG
# ============================================================

with open(CONFIG_PATH, "r") as f:
    CONFIG = json.load(f)

THRESHOLD = float(CONFIG["threshold"])


# ============================================================
# PREDICTION FUNCTION
# ============================================================

def predict_landslide(data: dict) -> dict:

    # Check required features
    missing_features = [
        feature
        for feature in FEATURES
        if feature not in data
    ]

    if missing_features:
        raise ValueError(
            f"Missing features: {missing_features}"
        )

    # Create dataframe in exact training order
    X = pd.DataFrame(
        [[data[feature] for feature in FEATURES]],
        columns=FEATURES
    )

    # Validate numeric values
    if X.isna().any().any():
        raise ValueError(
            "Input contains missing values."
        )

    # Probability of class 1
    probability = float(
        model.predict_proba(X)[0][1]
    )

    # Final prediction
    prediction = int(
        probability >= THRESHOLD
    )

    return {
        "landslide_probability": round(
            probability,
            4
        ),
        "prediction": prediction,
        "threshold": THRESHOLD,
        "model": "SVM RBF"
    }