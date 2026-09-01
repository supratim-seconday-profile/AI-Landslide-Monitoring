import json
import os

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


# ============================================================
# CONFIGURATION
# ============================================================

TRAIN_FILE = "data/processed/spatial_train.csv"
VALID_FILE = "data/processed/spatial_validation.csv"

MODEL_DIR = "models/spatial_baseline"
RESULT_DIR = "data/processed/model_results"

RANDOM_STATE = 2026


# ============================================================
# FEATURES
# ============================================================

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
ID_COLUMN = "record_id"


# ============================================================
# CREATE DIRECTORIES
# ============================================================

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)

os.makedirs(
    RESULT_DIR,
    exist_ok=True
)


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("             SIH SPATIAL BASELINE ML TRAINING")
print("=" * 70)


# ============================================================
# LOAD DATA
# ============================================================

train = pd.read_csv(
    TRAIN_FILE
)

validation = pd.read_csv(
    VALID_FILE
)


print()
print("--- DATASET ---")

print(
    "Training rows:",
    len(train)
)

print(
    "Validation rows:",
    len(validation)
)

print(
    "Features:",
    len(FEATURES)
)


# ============================================================
# FEATURE CHECK
# ============================================================

missing_features = [
    f
    for f in FEATURES
    if f not in train.columns
]

if missing_features:

    raise ValueError(
        "Missing features in training dataset: "
        + str(missing_features)
    )


missing_features_valid = [
    f
    for f in FEATURES
    if f not in validation.columns
]

if missing_features_valid:

    raise ValueError(
        "Missing features in validation dataset: "
        + str(missing_features_valid)
    )


# ============================================================
# TARGET CHECK
# ============================================================

print()
print("--- TRAIN TARGET ---")

print(
    train[TARGET]
    .value_counts()
    .sort_index()
)


print()
print("--- VALIDATION TARGET ---")

print(
    validation[TARGET]
    .value_counts()
    .sort_index()
)


# ============================================================
# PREPARE X / y
# ============================================================

X_train = train[
    FEATURES
].copy()

y_train = train[
    TARGET
].astype(int)


X_valid = validation[
    FEATURES
].copy()

y_valid = validation[
    TARGET
].astype(int)


# ============================================================
# FINITE VALUE CHECK
# ============================================================

if not np.isfinite(
    X_train.to_numpy()
).all():

    raise ValueError(
        "Training features contain non-finite values."
    )


if not np.isfinite(
    X_valid.to_numpy()
).all():

    raise ValueError(
        "Validation features contain non-finite values."
    )


# ============================================================
# MODELS
# ============================================================

models = {

    "logistic_regression": Pipeline(
        [
            (
                "scaler",
                StandardScaler()
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2000,
                    random_state=RANDOM_STATE
                )
            ),
        ]
    ),

    "random_forest": RandomForestClassifier(
        n_estimators=500,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        max_features="sqrt",
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    ),

    "svm_rbf": Pipeline(
        [
            (
                "scaler",
                StandardScaler()
            ),
            (
                "classifier",
                SVC(
                    kernel="rbf",
                    C=1.0,
                    gamma="scale",
                    probability=True,
                    class_weight="balanced",
                    random_state=RANDOM_STATE
                )
            ),
        ]
    ),
}


# ============================================================
# TRAINING
# ============================================================

results = []


print()
print("=" * 70)
print("                    MODEL TRAINING")
print("=" * 70)


for name, model in models.items():

    print()
    print("-" * 70)
    print(
        "Training:",
        name
    )
    print("-" * 70)

    model.fit(
        X_train,
        y_train
    )

    # --------------------------------------------------------
    # PREDICTIONS
    # --------------------------------------------------------

    y_pred = model.predict(
        X_valid
    )

    if hasattr(
        model,
        "predict_proba"
    ):

        y_prob = model.predict_proba(
            X_valid
        )[:, 1]

    else:

        scores = model.decision_function(
            X_valid
        )

        y_prob = scores


    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    accuracy = accuracy_score(
        y_valid,
        y_pred
    )

    precision = precision_score(
        y_valid,
        y_pred,
        zero_division=0
    )

    recall = recall_score(
        y_valid,
        y_pred,
        zero_division=0
    )

    f1 = f1_score(
        y_valid,
        y_pred,
        zero_division=0
    )

    roc_auc = roc_auc_score(
        y_valid,
        y_prob
    )

    cm = confusion_matrix(
        y_valid,
        y_pred
    )


    # --------------------------------------------------------
    # PRINT RESULTS
    # --------------------------------------------------------

    print()
    print("SPATIAL VALIDATION RESULTS")

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
    print("Confusion Matrix:")

    print(cm)


    # --------------------------------------------------------
    # SAVE MODEL
    # --------------------------------------------------------

    model_path = os.path.join(
        MODEL_DIR,
        name + ".joblib"
    )

    joblib.dump(
        model,
        model_path
    )

    print()
    print(
        "Saved model:",
        model_path
    )


    # --------------------------------------------------------
    # STORE RESULTS
    # --------------------------------------------------------

    results.append(
        {
            "model": name,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "roc_auc": roc_auc,
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
print("                 SPATIAL MODEL COMPARISON")
print("=" * 70)

print()

print(
    results_df.to_string(
        index=False
    )
)


# ============================================================
# BEST MODEL
# ============================================================

best = results_df.iloc[0]

print()
print("=" * 70)
print("              BEST SPATIAL BASELINE MODEL")
print("=" * 70)

print()

print(
    "Model:",
    best["model"]
)

print(
    f"Spatial Validation ROC-AUC: "
    f"{best['roc_auc']:.4f}"
)


# ============================================================
# SAVE RESULTS
# ============================================================

comparison_file = os.path.join(
    RESULT_DIR,
    "spatial_baseline_model_comparison.csv"
)

results_df.to_csv(
    comparison_file,
    index=False
)


metrics_file = os.path.join(
    RESULT_DIR,
    "spatial_baseline_model_metrics.json"
)

with open(
    metrics_file,
    "w"
) as f:

    json.dump(
        results,
        f,
        indent=4
    )


features_file = os.path.join(
    MODEL_DIR,
    "model_features.json"
)

with open(
    features_file,
    "w"
) as f:

    json.dump(
        FEATURES,
        f,
        indent=4
    )


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print("           SPATIAL BASELINE TRAINING COMPLETE")
print("=" * 70)

print()
print("Models saved in:")

print(
    MODEL_DIR
)

print()
print("Comparison saved:")

print(
    comparison_file
)

print()
print("Metrics saved:")

print(
    metrics_file
)

print()
print("Features saved:")

print(
    features_file
)

print()
print("=" * 70)