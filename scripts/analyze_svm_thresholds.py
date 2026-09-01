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
)


# ============================================================
# SIH SVM THRESHOLD ANALYSIS
# ============================================================

print("=" * 70)
print("             SIH SVM THRESHOLD ANALYSIS")
print("=" * 70)


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

DATA_PATH = "data/processed/spatial_validation.csv"
MODEL_PATH = "models/spatial_baseline/svm_rbf.joblib"
FEATURE_PATH = "models/spatial_baseline/model_features.json"

OUTPUT_DIR = "data/processed/model_results"
OUTPUT_CSV = os.path.join(
    OUTPUT_DIR,
    "spatial_svm_threshold_analysis.csv"
)


# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------

df = pd.read_csv(DATA_PATH)

print()
print("--- DATASET ---")
print("Validation rows:", len(df))


# ------------------------------------------------------------
# LOAD FEATURES
# ------------------------------------------------------------

with open(FEATURE_PATH, "r") as f:
    feature_data = json.load(f)


# Handle either a list or a dictionary containing features
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
    raise ValueError("Unexpected model_features.json format")


target = "landslide_target"

print("Features:", len(features))

print()
print("--- FEATURES ---")
for feature in features:
    print(" -", feature)


# ------------------------------------------------------------
# TARGET
# ------------------------------------------------------------

X = df[features]
y = df[target]

print()
print("--- TARGET ---")
print(y.value_counts())


# ------------------------------------------------------------
# LOAD MODEL
# ------------------------------------------------------------

print()
print("--- MODEL ---")
print("Loading:", MODEL_PATH)

model = joblib.load(MODEL_PATH)

print("Model loaded successfully.")


# ------------------------------------------------------------
# PROBABILITY PREDICTIONS
# ------------------------------------------------------------

if not hasattr(model, "predict_proba"):
    raise ValueError(
        "The loaded SVM does not support predict_proba()."
    )

probabilities = model.predict_proba(X)[:, 1]

auc = roc_auc_score(y, probabilities)

print()
print("--- BASELINE PROBABILITY PERFORMANCE ---")
print(f"ROC-AUC: {auc:.4f}")

print()
print(
    "Probability range:",
    f"min={probabilities.min():.4f}",
    f"max={probabilities.max():.4f}"
)


# ------------------------------------------------------------
# THRESHOLDS
# ------------------------------------------------------------

thresholds = [
    0.20,
    0.25,
    0.30,
    0.35,
    0.40,
    0.45,
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
]


# ------------------------------------------------------------
# ANALYSIS
# ------------------------------------------------------------

results = []

print()
print("=" * 70)
print("                    THRESHOLD RESULTS")
print("=" * 70)

for threshold in thresholds:

    predictions = (
        probabilities >= threshold
    ).astype(int)

    accuracy = accuracy_score(y, predictions)

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

    balanced_acc = balanced_accuracy_score(
        y,
        predictions
    )

    tn, fp, fn, tp = confusion_matrix(
        y,
        predictions,
        labels=[0, 1]
    ).ravel()

    predicted_positive_rate = predictions.mean()

    results.append({
        "threshold": threshold,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "balanced_accuracy": balanced_acc,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "predicted_positive": int(predictions.sum()),
        "predicted_negative": int((predictions == 0).sum()),
        "predicted_positive_rate": predicted_positive_rate,
    })

    print()
    print(f"Threshold: {threshold:.2f}")
    print(f"Accuracy          : {accuracy:.4f}")
    print(f"Precision         : {precision:.4f}")
    print(f"Recall            : {recall:.4f}")
    print(f"F1                : {f1:.4f}")
    print(f"Balanced Accuracy : {balanced_acc:.4f}")
    print(f"TP={tp}  TN={tn}  FP={fp}  FN={fn}")
    print(
        f"Predicted positives: "
        f"{predictions.sum()} / {len(predictions)}"
    )


# ------------------------------------------------------------
# RESULTS DATAFRAME
# ------------------------------------------------------------

results_df = pd.DataFrame(results)

print()
print("=" * 70)
print("                 THRESHOLD COMPARISON")
print("=" * 70)

display_columns = [
    "threshold",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "balanced_accuracy",
    "tp",
    "fp",
    "fn",
    "tn",
]

print(
    results_df[display_columns].to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# ------------------------------------------------------------
# BEST THRESHOLDS
# ------------------------------------------------------------

best_f1 = results_df.loc[
    results_df["f1"].idxmax()
]

best_balanced = results_df.loc[
    results_df["balanced_accuracy"].idxmax()
]

best_recall = results_df.loc[
    results_df["recall"].idxmax()
]


print()
print("=" * 70)
print("                    BEST THRESHOLDS")
print("=" * 70)

print()
print("--- BEST F1 ---")
print(f"Threshold: {best_f1['threshold']:.2f}")
print(f"F1: {best_f1['f1']:.4f}")
print(f"Recall: {best_f1['recall']:.4f}")
print(f"Precision: {best_f1['precision']:.4f}")

print()
print("--- BEST BALANCED ACCURACY ---")
print(f"Threshold: {best_balanced['threshold']:.2f}")
print(
    f"Balanced Accuracy: "
    f"{best_balanced['balanced_accuracy']:.4f}"
)
print(f"Recall: {best_balanced['recall']:.4f}")
print(f"Precision: {best_balanced['precision']:.4f}")

print()
print("--- BEST RECALL ---")
print(f"Threshold: {best_recall['threshold']:.2f}")
print(f"Recall: {best_recall['recall']:.4f}")
print(f"Precision: {best_recall['precision']:.4f}")
print(f"F1: {best_recall['f1']:.4f}")


# ------------------------------------------------------------
# EARLY WARNING CANDIDATES
# ------------------------------------------------------------

print()
print("=" * 70)
print("              EARLY WARNING CANDIDATES")
print("=" * 70)

# For a landslide early-warning system, we care about
# relatively high recall without completely destroying precision.

warning_candidates = results_df[
    results_df["recall"] >= 0.70
].copy()

if len(warning_candidates) > 0:

    warning_candidates = warning_candidates.sort_values(
        by=["f1", "precision"],
        ascending=False
    )

    print(
        warning_candidates[
            [
                "threshold",
                "precision",
                "recall",
                "f1",
                "balanced_accuracy",
                "fp",
                "fn",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

else:
    print("No threshold reached recall >= 0.70.")


# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

os.makedirs(OUTPUT_DIR, exist_ok=True)

results_df.to_csv(
    OUTPUT_CSV,
    index=False
)

print()
print("=" * 70)
print("          SVM THRESHOLD ANALYSIS COMPLETE")
print("=" * 70)

print()
print("ROC-AUC:", f"{auc:.4f}")

print()
print("Saved:")
print(f" - {OUTPUT_CSV}")

print()
print("=" * 70)