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
    roc_auc_score,
    confusion_matrix,
    classification_report,
    balanced_accuracy_score
)

# ============================================================
# SIH TUNED RANDOM FOREST - FINAL SPATIAL TEST
# ============================================================

print("=" * 70)
print("       SIH TUNED RANDOM FOREST FINAL SPATIAL TEST")
print("=" * 70)

TEST_FILE = "data/processed/spatial_test.csv"

MODEL_FILE = (
    "models/tuned_random_forest/"
    "random_forest_tuned.joblib"
)

RESULT_DIR = "data/processed/model_results"

os.makedirs(RESULT_DIR, exist_ok=True)

TARGET = "landslide_target"

FEATURES = [
    "B2",
    "B4",
    "B8",
    "B11",
    "B12",
    "NDVI",
    "NDMI",
    "NDWI",
    "NBR",
]

# ------------------------------------------------------------
# LOAD
# ------------------------------------------------------------

test = pd.read_csv(TEST_FILE)

model = joblib.load(MODEL_FILE)

X_test = test[FEATURES].copy()
y_test = test[TARGET].copy()

print()
print("--- TEST DATASET ---")
print("Rows:", len(test))
print("Columns:", len(test.columns))
print("Features:", len(FEATURES))

print()
print("--- TEST TARGET ---")
print(y_test.value_counts())

# ------------------------------------------------------------
# PREDICTION
# ------------------------------------------------------------

y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

# ------------------------------------------------------------
# METRICS
# ------------------------------------------------------------

accuracy = accuracy_score(
    y_test,
    y_pred
)

precision = precision_score(
    y_test,
    y_pred,
    zero_division=0
)

recall = recall_score(
    y_test,
    y_pred,
    zero_division=0
)

f1 = f1_score(
    y_test,
    y_pred,
    zero_division=0
)

roc_auc = roc_auc_score(
    y_test,
    y_prob
)

balanced_acc = balanced_accuracy_score(
    y_test,
    y_pred
)

tn, fp, fn, tp = confusion_matrix(
    y_test,
    y_pred
).ravel()

# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

print()
print("=" * 70)
print("                  FINAL TEST RESULTS")
print("=" * 70)

print()
print("Accuracy :", f"{accuracy:.4f}")
print("Precision:", f"{precision:.4f}")
print("Recall   :", f"{recall:.4f}")
print("F1-score :", f"{f1:.4f}")
print("ROC-AUC  :", f"{roc_auc:.4f}")
print("Balanced Accuracy:", f"{balanced_acc:.4f}")

print()
print("Confusion Matrix:")
print(
    f"[[{tn} {fp}]"
)
print(
    f" [{fn} {tp}]]"
)

print()
print("Classification Report:")
print(
    classification_report(
        y_test,
        y_pred,
        digits=4,
        zero_division=0
    )
)

# ------------------------------------------------------------
# ERROR COUNTS
# ------------------------------------------------------------

print()
print("--- PREDICTION COUNTS ---")

print(
    "Actual positives:",
    int((y_test == 1).sum())
)

print(
    "Actual negatives:",
    int((y_test == 0).sum())
)

print(
    "Predicted positives:",
    int((y_pred == 1).sum())
)

print(
    "Predicted negatives:",
    int((y_pred == 0).sum())
)

print()
print("--- ERROR COUNTS ---")
print("True positives :", tp)
print("True negatives :", tn)
print("False positives:", fp)
print("False negatives:", fn)

# ------------------------------------------------------------
# SAVE PREDICTIONS
# ------------------------------------------------------------

predictions = test.copy()

predictions["predicted_probability"] = y_prob
predictions["predicted_class"] = y_pred

prediction_file = os.path.join(
    RESULT_DIR,
    "tuned_rf_spatial_test_predictions.csv"
)

predictions.to_csv(
    prediction_file,
    index=False
)

# ------------------------------------------------------------
# SAVE METRICS
# ------------------------------------------------------------

metrics = {
    "model": "tuned_random_forest",
    "feature_set": "indices_reduced_spectral",
    "n_features": len(FEATURES),
    "features": FEATURES,

    "test_rows": len(test),

    "accuracy": float(accuracy),
    "precision": float(precision),
    "recall": float(recall),
    "f1": float(f1),
    "roc_auc": float(roc_auc),
    "balanced_accuracy": float(balanced_acc),

    "tn": int(tn),
    "fp": int(fp),
    "fn": int(fn),
    "tp": int(tp),
}

metrics_file = os.path.join(
    RESULT_DIR,
    "tuned_rf_spatial_test_metrics.json"
)

with open(metrics_file, "w") as f:
    json.dump(
        metrics,
        f,
        indent=4
    )

# ------------------------------------------------------------
# COMPLETE
# ------------------------------------------------------------

print()
print("=" * 70)
print("       FINAL SPATIAL TEST EVALUATION COMPLETE")
print("=" * 70)

print()
print("Saved:")
print(" -", prediction_file)
print(" -", metrics_file)

print()
print("=" * 70)