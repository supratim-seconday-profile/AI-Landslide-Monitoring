import os
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

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

TRAIN_FILE = "data/processed/ml_train.csv"
VAL_FILE = "data/processed/ml_validation.csv"

MODEL_DIR = "models"
RESULT_DIR = "data/processed/model_results"

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)


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


RANDOM_STATE = 2026


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("              SIH BASELINE ML TRAINING")
print("=" * 70)


# ============================================================
# LOAD DATA
# ============================================================

train_df = pd.read_csv(TRAIN_FILE)
val_df = pd.read_csv(VAL_FILE)

print()
print("Training rows:", len(train_df))
print("Validation rows:", len(val_df))
print("Features:", len(FEATURES))


# ============================================================
# REQUIRED COLUMN CHECK
# ============================================================

required_columns = FEATURES + [TARGET, ID_COLUMN]

for name, df in [
    ("training", train_df),
    ("validation", val_df),
]:

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns in {name} dataset: {missing}"
        )


# ============================================================
# PREPARE X AND Y
# ============================================================

X_train = train_df[FEATURES].copy()
y_train = train_df[TARGET].copy()

X_val = val_df[FEATURES].copy()
y_val = val_df[TARGET].copy()


# ============================================================
# FINITE VALUE CHECK
# ============================================================

if not np.isfinite(X_train.to_numpy()).all():
    raise ValueError(
        "Non-finite values found in training features."
    )

if not np.isfinite(X_val.to_numpy()).all():
    raise ValueError(
        "Non-finite values found in validation features."
    )


# ============================================================
# TARGET CHECK
# ============================================================

print()
print("--- TRAIN TARGET ---")
print(y_train.value_counts().sort_index())

print()
print("--- VALIDATION TARGET ---")
print(y_val.value_counts().sort_index())


# ============================================================
# DEFINE MODELS
# ============================================================

models = {

    "logistic_regression": Pipeline([
        (
            "scaler",
            StandardScaler()
        ),
        (
            "model",
            LogisticRegression(
                max_iter=2000,
                random_state=RANDOM_STATE
            )
        )
    ]),

    "random_forest": RandomForestClassifier(
        n_estimators=500,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1
    ),

    "svm_rbf": Pipeline([
        (
            "scaler",
            StandardScaler()
        ),
        (
            "model",
            SVC(
                kernel="rbf",
                probability=True,
                class_weight="balanced",
                random_state=RANDOM_STATE
            )
        )
    ]),
}


# ============================================================
# METRIC FUNCTION
# ============================================================

def evaluate_model(model, X, y):

    predictions = model.predict(X)

    probabilities = model.predict_proba(X)[:, 1]

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

    roc_auc = roc_auc_score(
        y,
        probabilities
    )

    cm = confusion_matrix(
        y,
        predictions
    )

    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "roc_auc": float(roc_auc),
        "confusion_matrix": cm.tolist(),
    }


# ============================================================
# TRAIN MODELS
# ============================================================

results = {}

print()
print("=" * 70)
print("                    MODEL TRAINING")
print("=" * 70)


for model_name, model in models.items():

    print()
    print("-" * 70)
    print("Training:", model_name)
    print("-" * 70)

    model.fit(
        X_train,
        y_train
    )

    # --------------------------------------------------------
    # Training performance
    # --------------------------------------------------------

    train_metrics = evaluate_model(
        model,
        X_train,
        y_train
    )

    # --------------------------------------------------------
    # Validation performance
    # --------------------------------------------------------

    val_metrics = evaluate_model(
        model,
        X_val,
        y_val
    )

    results[model_name] = {
        "train": train_metrics,
        "validation": val_metrics,
    }

    # --------------------------------------------------------
    # Print validation results
    # --------------------------------------------------------

    print()
    print("VALIDATION RESULTS")

    print(
        f"Accuracy : {val_metrics['accuracy']:.4f}"
    )

    print(
        f"Precision: {val_metrics['precision']:.4f}"
    )

    print(
        f"Recall   : {val_metrics['recall']:.4f}"
    )

    print(
        f"F1-score : {val_metrics['f1']:.4f}"
    )

    print(
        f"ROC-AUC  : {val_metrics['roc_auc']:.4f}"
    )

    print()
    print("Confusion Matrix:")

    print(
        np.array(
            val_metrics["confusion_matrix"]
        )
    )

    # --------------------------------------------------------
    # Save model
    # --------------------------------------------------------

    model_path = os.path.join(
        MODEL_DIR,
        f"{model_name}.joblib"
    )

    joblib.dump(
        model,
        model_path
    )

    print()
    print("Saved model:", model_path)


# ============================================================
# CREATE COMPARISON TABLE
# ============================================================

comparison_rows = []

for model_name, result in results.items():

    m = result["validation"]

    comparison_rows.append({

        "model": model_name,

        "accuracy": m["accuracy"],

        "precision": m["precision"],

        "recall": m["recall"],

        "f1": m["f1"],

        "roc_auc": m["roc_auc"],

    })


comparison = pd.DataFrame(
    comparison_rows
)

comparison = comparison.sort_values(
    "roc_auc",
    ascending=False
).reset_index(drop=True)


# ============================================================
# PRINT COMPARISON
# ============================================================

print()
print("=" * 70)
print("                 MODEL COMPARISON")
print("=" * 70)

print()

print(
    comparison.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# ============================================================
# SELECT BEST MODEL
# ============================================================

best_model_name = comparison.iloc[0]["model"]

best_roc_auc = comparison.iloc[0]["roc_auc"]


print()
print("=" * 70)
print("                 BEST BASELINE MODEL")
print("=" * 70)

print()
print("Model:", best_model_name)
print(f"Validation ROC-AUC: {best_roc_auc:.4f}")


# ============================================================
# SAVE COMPARISON
# ============================================================

comparison_file = os.path.join(
    RESULT_DIR,
    "baseline_model_comparison.csv"
)

comparison.to_csv(
    comparison_file,
    index=False
)


# ============================================================
# SAVE COMPLETE METRICS
# ============================================================

metrics_file = os.path.join(
    RESULT_DIR,
    "baseline_model_metrics.json"
)

with open(
    metrics_file,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        results,
        f,
        indent=4
    )


# ============================================================
# SAVE FEATURE LIST
# ============================================================

feature_file = os.path.join(
    MODEL_DIR,
    "model_features.json"
)

with open(
    feature_file,
    "w",
    encoding="utf-8"
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
print("             BASELINE TRAINING COMPLETE")
print("=" * 70)

print()
print("Models saved in:")
print(f"  {MODEL_DIR}")

print()
print("Results saved in:")
print(f"  {RESULT_DIR}")

print()
print("Comparison:")
print(f"  {comparison_file}")

print()
print("Metrics:")
print(f"  {metrics_file}")

print()
print("Features:")
print(f"  {feature_file}")

print()
print("=" * 70)