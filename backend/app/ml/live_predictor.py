import json
from pathlib import Path

import joblib
import pandas as pd

from .earth_engine.extractor import extract_features


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

MODEL_PATH = (
    BASE_DIR
    / "models"
    / "final"
    / "final_svm_rbf.joblib"
)

FEATURES_PATH = (
    BASE_DIR
    / "models"
    / "final"
    / "model_features.json"
)


# ============================================================
# LOAD MODEL
# ============================================================

model = joblib.load(MODEL_PATH)


with open(FEATURES_PATH, "r") as f:
    MODEL_FEATURES = json.load(f)


# ============================================================
# LIVE PREDICTION
# ============================================================

def predict_live(
    latitude: float,
    longitude: float
):

    # --------------------------------------------------------
    # Extract satellite features
    # --------------------------------------------------------

    features = extract_features(
        latitude,
        longitude
    )


    # --------------------------------------------------------
    # Check required features
    # --------------------------------------------------------

    missing = [
        feature
        for feature in MODEL_FEATURES
        if feature not in features
    ]

    if missing:

        raise ValueError(
            f"Missing model features: {missing}"
        )


    # --------------------------------------------------------
    # Create model input
    # --------------------------------------------------------

    X = pd.DataFrame(
        [
            {
                feature: features[feature]
                for feature in MODEL_FEATURES
            }
        ]
    )


    # --------------------------------------------------------
    # Prediction
    # --------------------------------------------------------

    probability = float(
        model.predict_proba(X)[0][1]
    )


    prediction = int(
        probability >= 0.50
    )


    # --------------------------------------------------------
    # Risk level
    # --------------------------------------------------------

    if probability >= 0.70:

        risk_level = "HIGH"

    elif probability >= 0.50:

        risk_level = "MEDIUM"

    else:

        risk_level = "LOW"


    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    return {

        "latitude": latitude,

        "longitude": longitude,

        "landslide_probability": round(
            probability,
            4
        ),

        "prediction": prediction,

        "risk_level": risk_level,

        "model": "SVM RBF",

        "features": features

    }