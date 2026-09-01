import os
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    balanced_accuracy_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)


print("=" * 70)
print("          SIH FINAL SVM SPATIAL TEST EVALUATION")
print("=" * 70)


# ============================================================
# PATHS
# ============================================================

DATA_PATH = "data/processed/spatial_test.csv"
MODEL_PATH = "models/spatial_baseline/svm_rbf.joblib"
FEATURE_PATH = "models/spatial_baseline/model_features.json"

OUTPUT_DIR = "data/processed/model_results"

PREDICTIONS_PATH = os.path.join(
    OUTPUT_DIR,
    "final_svm_spatial_test_predictions.csv"
)

METRICS_PATH = os.path.join(
    OUTPUT_DIR,
    "final_svm_spatial_test_metrics.json"
)


# ============================================================
# SETTINGS
# ============================================================

THRESHOLD = 0.50


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(DATA_PATH)

print()
print("--- TEST DATASET ---")
print("Rows:", len(df))
print("Columns:", len(df.columns))


# ============================================================
# LOAD FEATURES
# ============================================================

with open(FEATURE_PATH, "r") as f:
    feature_data = json.load(f)

if isinstance(feature_data, list):
    features = feature_data

elif isinstance(feature_data, dict):

    if "features" in feature_data:
        features = feature_data["features"]

    elif "model_features" in feature_data:
        features = feature_data["model_features"]

    else:
        raise ValueError(
            "Could not find feature list in model_features.json"
        )

else:
    raise ValueError(
        "Unexpected model_features.json format"
    )


target = "landslide_target"

print("Features:", len(features))

print()
print("--- FEATURES ---")

for feature in features:
    print(" -", feature)


# ============================================================
# DATA
# ============================================================

X = df[features]
y = df[target]

print()
print("--- TEST TARGET ---")
print(y.value_counts())


# ============================================================
# LOAD MODEL
# ============================================================

print()
print("--- MODEL ---")
print("Loading:", MODEL_PATH)

model = joblib.load(MODEL_PATH)

print("Model loaded successfully.")


# ============================================================
# PREDICTIONS
# ============================================================

if not hasattr(model, "predict_proba"):
    raise ValueError(
        "Model does not support predict_proba()."
    )

probabilities = model.predict_proba(X)[:, 1]

predictions = (
    probabilities >= THRESHOLD
).astype(int)


# ============================================================
# METRICS
# ============================================================

accuracy = accuracy_score(
    y,
    predictions
)

precision = precision_score(
    y,
    predictions,
    zero_division=0
)

recall = recall_score(
    y,
    predictions,
    zero_division=0
)

f1 = f1_score(
    y,
    predictions,
    zero_division=0
)

balanced_accuracy = balanced_accuracy_score(
    y,
    predictions
)

roc_auc = roc_auc_score(
    y,
    probabilities
)

tn, fp, fn, tp = confusion_matrix(
    y,
    predictions,
    labels=[0, 1]
).ravel()


# ============================================================
# RESULTS
# ============================================================

print()
print("=" * 70)
print("                    FINAL TEST RESULTS")
print("=" * 70)

print()
print("Threshold          :", f"{THRESHOLD:.2f}")
print("Accuracy           :", f"{accuracy:.4f}")
print("Precision          :", f"{precision:.4f}")
print("Recall             :", f"{recall:.4f}")
print("F1-score           :", f"{f1:.4f}")
print("ROC-AUC            :", f"{roc_auc:.4f}")
print(
    "Balanced Accuracy  :",
    f"{balanced_accuracy:.4f}"
)

print()
print("Confusion Matrix:")
print(
    np.array([
        [tn, fp],
        [fn, tp]
    ])
)

print()
print("--- ERROR COUNTS ---")
print("True positives :", tp)
print("True negatives :", tn)
print("False positives:", fp)
print("False negatives:", fn)

print()
print("--- PREDICTION COUNTS ---")
print("Actual positives :", int((y == 1).sum()))
print("Actual negatives :", int((y == 0).sum()))
print("Predicted positives:", int((predictions == 1).sum()))
print("Predicted negatives:", int((predictions == 0).sum()))

print()
print("--- CLASSIFICATION REPORT ---")
print(
    classification_report(
        y,
        predictions,
        zero_division=0
    )
)


# ============================================================
# SAVE PREDICTIONS
# ============================================================

output_df = df.copy()

output_df["landslide_probability"] = probabilities
output_df["predicted_landslide"] = predictions
output_df["decision_threshold"] = THRESHOLD

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

output_df.to_csv(
    PREDICTIONS_PATH,
    index=False
)


# ============================================================
# SAVE METRICS
# ============================================================

metrics = {
    "model": "svm_rbf",
    "feature_count": len(features),
    "features": features,
    "threshold": THRESHOLD,
    "test_rows": int(len(df)),
    "accuracy": float(accuracy),
    "precision": float(precision),
    "recall": float(recall),
    "f1": float(f1),
    "roc_auc": float(roc_auc),
    "balanced_accuracy": float(balanced_accuracy),
    "tn": int(tn),
    "fp": int(fp),
    "fn": int(fn),
    "tp": int(tp),
}


with open(
    METRICS_PATH,
    "w"
) as f:
    json.dump(
        metrics,
        f,
        indent=4
    )


# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 70)
print("             FINAL SVM TEST EVALUATION COMPLETE")
print("=" * 70)

print()
print("Saved:")
print(" -", PREDICTIONS_PATH)
print(" -", METRICS_PATH)

print()
print("=" * 70)