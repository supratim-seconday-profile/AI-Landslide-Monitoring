import os
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

# ============================================================
# SIH FEATURE SET EXPERIMENT
# ============================================================

print("=" * 70)
print("             SIH FEATURE SET EXPERIMENT")
print("=" * 70)

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

TRAIN_FILE = "data/processed/spatial_train.csv"
VALID_FILE = "data/processed/spatial_validation.csv"

OUTPUT_DIR = "data/processed/model_results"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------

train = pd.read_csv(TRAIN_FILE)
valid = pd.read_csv(VALID_FILE)

print()
print("--- DATASET ---")
print("Training rows:", len(train))
print("Validation rows:", len(valid))

# ------------------------------------------------------------
# TARGET
# ------------------------------------------------------------

TARGET = "landslide_target"
ID_COL = "record_id"

y_train = train[TARGET]
y_valid = valid[TARGET]

print()
print("--- TARGET ---")
print("Training:")
print(y_train.value_counts())

print()
print("Validation:")
print(y_valid.value_counts())

# ============================================================
# FEATURE SETS
# ============================================================

feature_sets = {

    # 1. All available features
    "full_16": [
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
    ],

    # 2. Vegetation / moisture / burn indices only
    "indices_only": [
        "NDVI",
        "NDMI",
        "NDWI",
        "NBR",
    ],

    # 3. Reduced spectral bands
    "reduced_spectral": [
        "B2",
        "B4",
        "B8",
        "B11",
        "B12",
    ],

    # 4. Indices + reduced spectral bands
    "indices_reduced_spectral": [
        "B2",
        "B4",
        "B8",
        "B11",
        "B12",
        "NDVI",
        "NDMI",
        "NDWI",
        "NBR",
    ],

    # 5. Practical feature set
    "practical": [
        "B2",
        "B4",
        "B8",
        "B11",
        "B12",
        "NDVI",
        "NDMI",
        "NDWI",
        "NBR",
        "hls_image_count",
        "hls_valid_image_count",
    ],
}

# ============================================================
# MODELS
# ============================================================

models = {

    "logistic_regression": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        (
            "model",
            LogisticRegression(
                max_iter=2000,
                random_state=2026
            )
        ),
    ]),

    "random_forest": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        (
            "model",
            RandomForestClassifier(
                n_estimators=400,
                random_state=2026,
                n_jobs=-1,
                class_weight="balanced"
            )
        ),
    ]),

    "svm_rbf": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        (
            "model",
            SVC(
                kernel="rbf",
                C=1.0,
                gamma="scale",
                probability=True,
                random_state=2026
            )
        ),
    ]),
}

# ============================================================
# EXPERIMENT
# ============================================================

results = []

print()
print("=" * 70)
print("                 FEATURE SET EXPERIMENT")
print("=" * 70)

for feature_set_name, features in feature_sets.items():

    print()
    print("-" * 70)
    print("FEATURE SET:", feature_set_name)
    print("-" * 70)

    print("Number of features:", len(features))
    print("Features:")
    for feature in features:
        print("  -", feature)

    X_train = train[features].copy()
    X_valid = valid[features].copy()

    for model_name, model in models.items():

        print()
        print("Training:", model_name)

        # ----------------------------------------------------
        # TRAIN
        # ----------------------------------------------------

        model.fit(X_train, y_train)

        # ----------------------------------------------------
        # PREDICTION
        # ----------------------------------------------------

        y_pred = model.predict(X_valid)

        if hasattr(model, "predict_proba"):
            y_prob = model.predict_proba(X_valid)[:, 1]
        else:
            y_prob = model.decision_function(X_valid)

        # ----------------------------------------------------
        # METRICS
        # ----------------------------------------------------

        accuracy = accuracy_score(y_valid, y_pred)

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

        # ----------------------------------------------------
        # STORE RESULTS
        # ----------------------------------------------------

        results.append({
            "feature_set": feature_set_name,
            "n_features": len(features),
            "model": model_name,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "roc_auc": roc_auc,
        })


# ============================================================
# RESULTS DATAFRAME
# ============================================================

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    by="roc_auc",
    ascending=False
).reset_index(drop=True)

# ============================================================
# DISPLAY COMPARISON
# ============================================================

print()
print("=" * 70)
print("                 FEATURE SET COMPARISON")
print("=" * 70)

print()

print(
    results_df.to_string(
        index=False,
        formatters={
            "accuracy": "{:.4f}".format,
            "precision": "{:.4f}".format,
            "recall": "{:.4f}".format,
            "f1": "{:.4f}".format,
            "roc_auc": "{:.4f}".format,
        }
    )
)

# ============================================================
# BEST RESULT
# ============================================================

best = results_df.iloc[0]

print()
print("=" * 70)
print("                    BEST CONFIGURATION")
print("=" * 70)

print()
print("Feature set:", best["feature_set"])
print("Number of features:", best["n_features"])
print("Model:", best["model"])
print("Validation ROC-AUC:", f"{best['roc_auc']:.4f}")
print("Validation Accuracy:", f"{best['accuracy']:.4f}")
print("Validation Precision:", f"{best['precision']:.4f}")
print("Validation Recall:", f"{best['recall']:.4f}")
print("Validation F1:", f"{best['f1']:.4f}")

# ============================================================
# SAVE RESULTS
# ============================================================

csv_path = os.path.join(
    OUTPUT_DIR,
    "feature_set_experiment.csv"
)

results_df.to_csv(
    csv_path,
    index=False
)

# ------------------------------------------------------------
# Save best configuration
# ------------------------------------------------------------

best_config = {
    "feature_set": best["feature_set"],
    "n_features": int(best["n_features"]),
    "model": best["model"],
    "validation_accuracy": float(best["accuracy"]),
    "validation_precision": float(best["precision"]),
    "validation_recall": float(best["recall"]),
    "validation_f1": float(best["f1"]),
    "validation_roc_auc": float(best["roc_auc"]),
    "features": feature_sets[best["feature_set"]],
}

json_path = os.path.join(
    OUTPUT_DIR,
    "best_feature_set.json"
)

with open(json_path, "w") as f:
    json.dump(
        best_config,
        f,
        indent=4
    )

# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 70)
print("          FEATURE SET EXPERIMENT COMPLETE")
print("=" * 70)

print()
print("Results saved:")
print(" -", csv_path)
print(" -", json_path)

print()
print("=" * 70)