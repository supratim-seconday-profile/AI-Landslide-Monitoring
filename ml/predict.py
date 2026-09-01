from pathlib import Path

import joblib
import pandas as pd


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    BASE_DIR
    / "ml"
    / "landslide_model.pkl"
)


# ============================================================
# LOAD MODEL
# ============================================================

if not MODEL_PATH.exists():

    raise FileNotFoundError(
        "\nModel not found.\n"
        "Run train.py first."
    )


model_data = joblib.load(
    MODEL_PATH
)


model = model_data["model"]

features = model_data["features"]


# ============================================================
# SAMPLE INPUT
# ============================================================
#
# These MUST correspond to the features used during training.
#
# ============================================================

sample = {

    "latitude": 26.1445,

    "longitude": 91.7362,

    "year": 2026,

    "event_month": 8,

    "event_day_of_year": 242,

    "rainfall_24h_mm": 180,

    "casualty": 0,

    "has_casualty": 0,

    "road_affected_flag": 1
}


# ============================================================
# CREATE INPUT
# ============================================================

input_data = pd.DataFrame(
    [sample]
)


# ============================================================
# MAKE SURE FEATURES MATCH
# ============================================================

for feature in features:

    if feature not in input_data.columns:

        input_data[feature] = 0


input_data = input_data[
    features
]


# ============================================================
# PREDICTION
# ============================================================

prediction = model.predict(
    input_data
)


score = model.decision_function(
    input_data
)[0]


# ============================================================
# CONVERT SCORE TO RISK SCORE
# ============================================================
#
# IsolationForest:
#
# lower score = more anomalous
#
# We convert it into a simple 0-100 risk score.
#
# ============================================================

risk_score = 50 - (score * 100)

risk_score = max(
    0,
    min(
        100,
        risk_score
    )
)


# ============================================================
# RISK LEVEL
# ============================================================

if risk_score >= 70:

    risk_level = "HIGH"

elif risk_score >= 40:

    risk_level = "MEDIUM"

else:

    risk_level = "LOW"


# ============================================================
# OUTPUT
# ============================================================

print("\n====================================")
print("LANDSLIDE RISK PREDICTION")
print("====================================")

print(
    f"Risk Score: {risk_score:.2f}/100"
)

print(
    f"Risk Level: {risk_level}"
)

print(
    f"Anomaly Score: {score:.4f}"
)

print(
    f"Model Prediction: {prediction[0]}"
)

print("\nFeatures:")

for feature in features:

    print(
        f"{feature}: "
        f"{input_data.iloc[0][feature]}"
    )