import json
import os

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
)


# ============================================================
# CONFIGURATION
# ============================================================

TEST_FILE = "data/processed/spatial_test.csv"

MODEL_DIR = "models/spatial_baseline"

RESULT_DIR = "data/processed/model_results"

FEATURES_FILE = os.path.join(
    MODEL_DIR,
    "model_features.json"
)


# ============================================================
# DIRECTORIES
# ============================================================

os.makedirs(
    RESULT_DIR,
    exist_ok=True
)


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("             SIH SPATIAL TEST EVALUATION")
print("=" * 70)


# ============================================================
# LOAD TEST DATA
# ============================================================

test = pd.read_csv(
    TEST_FILE
)

print()
print("--- TEST DATASET ---")

print(
    "Rows:",
    len(test)
)

print(
    "Columns:",
    len(test.columns)
)


# ============================================================
# LOAD FEATURES
# ============================================================

with open(
    FEATURES_FILE,
    "r"
) as f:

    FEATURES = json.load(f)


TARGET = "landslide_target"


print(
    "Features:",
    len(FEATURES)
)


# ============================================================
# TARGET CHECK
# ============================================================

print()
print("--- TEST TARGET ---")

print(
    test[TARGET]
    .value_counts()
    .sort_index()
)


# ============================================================
# FEATURE CHECK
# ============================================================

missing_features = [
    f
    for f in FEATURES
    if f not in test.columns
]

if missing_features:

    raise ValueError(
        "Missing test features: "
        + str(missing_features)
    )


# ============================================================
# PREPARE DATA
# ============================================================

X_test = test[
    FEATURES
].copy()

y_test = test[
    TARGET
].astype(int)


# ============================================================
# FINITE CHECK
# ============================================================

if not np.isfinite(
    X_test.to_numpy()
).all():

    raise ValueError(
        "Test dataset contains non-finite values."
    )


# ============================================================
# MODELS
# ============================================================

model_names = [
    "logistic_regression",
    "random_forest",
    "svm_rbf",
]


results = []


# ============================================================
# EVALUATION
# ============================================================

print()
print("=" * 70)
print("                    MODEL EVALUATION")
print("=" * 70)


for name in model_names:

    print()
    print("-" * 70)
    print(
        "Evaluating:",
        name
    )
    print("-" * 70)


    # --------------------------------------------------------
    # LOAD MODEL
    # --------------------------------------------------------

    model_path = os.path.join(
        MODEL_DIR,
        name + ".joblib"
    )

    model = joblib.load(
        model_path
    )


    # --------------------------------------------------------
    # PREDICTION
    # --------------------------------------------------------

    y_pred = model.predict(
        X_test
    )


    # --------------------------------------------------------
    # PROBABILITY / SCORE
    # --------------------------------------------------------

    if hasattr(
        model,
        "predict_proba"
    ):

        y_prob = model.predict_proba(
            X_test
        )[:, 1]

    elif hasattr(
        model,
        "decision_function"
    ):

        y_prob = model.decision_function(
            X_test
        )

    else:

        raise ValueError(
            f"{name} has no probability or decision score."
        )


    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

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

    cm = confusion_matrix(
        y_test,
        y_pred
    )


    # --------------------------------------------------------
    # PRINT
    # --------------------------------------------------------

    print()

    print(
        "TEST RESULTS"
    )

    print(
        f"Accuracy : {accuracy:.4f}"
    )

    print(
        f"Precision: {precision:.4f}"
    )

    print(
        f"Recall   : {recall:.4f}"
    )

    print(
        f"F1-score : {f1:.4f}"
    )

    print(
        f"ROC-AUC  : {roc_auc:.4f}"
    )

    print()

    print(
        "Confusion Matrix:"
    )

    print(
        cm
    )

    print()

    print(
        "Classification Report:"
    )

    print(
        classification_report(
            y_test,
            y_pred,
            digits=4,
            zero_division=0
        )
    )


    # --------------------------------------------------------
    # SAVE RESULTS
    # --------------------------------------------------------

    results.append(
        {
            "model": name,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "roc_auc": roc_auc,
            "tn": int(cm[0, 0]),
            "fp": int(cm[0, 1]),
            "fn": int(cm[1, 0]),
            "tp": int(cm[1, 1]),
        }
    )


# ============================================================
# COMPARISON
# ============================================================

results_df = pd.DataFrame(
    results
)

results_df = results_df.sort_values(
    "roc_auc",
    ascending=False
).reset_index(
    drop=True
)


print()
print("=" * 70)
print("                 SPATIAL TEST COMPARISON")
print("=" * 70)

print()

print(
    results_df.to_string(
        index=False
    )
)


# ============================================================
# BEST TEST MODEL
# ============================================================

best = results_df.iloc[0]


print()
print("=" * 70)
print("                  TEST RESULT")
print("=" * 70)

print()

print(
    "Best model:",
    best["model"]
)

print(
    f"Test ROC-AUC: {best['roc_auc']:.4f}"
)

print(
    f"Test Accuracy: {best['accuracy']:.4f}"
)

print(
    f"Test Precision: {best['precision']:.4f}"
)

print(
    f"Test Recall: {best['recall']:.4f}"
)

print(
    f"Test F1: {best['f1']:.4f}"
)


# ============================================================
# SAVE
# ============================================================

output_file = os.path.join(
    RESULT_DIR,
    "spatial_test_model_comparison.csv"
)

results_df.to_csv(
    output_file,
    index=False
)


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print("             SPATIAL TEST EVALUATION COMPLETE")
print("=" * 70)

print()

print(
    "Saved:",
    output_file
)

print()
print("=" * 70)