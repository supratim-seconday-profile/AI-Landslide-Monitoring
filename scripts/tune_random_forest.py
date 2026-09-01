import os
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)

# ============================================================
# SIH RANDOM FOREST HYPERPARAMETER TUNING
# ============================================================

print("=" * 70)
print("             SIH RANDOM FOREST HYPERPARAMETER TUNING")
print("=" * 70)

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

TRAIN_FILE = "data/processed/spatial_train.csv"
VALID_FILE = "data/processed/spatial_validation.csv"

MODEL_DIR = "models/tuned_random_forest"
RESULT_DIR = "data/processed/model_results"

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------

train = pd.read_csv(TRAIN_FILE)
valid = pd.read_csv(VALID_FILE)

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

X_train = train[FEATURES].copy()
y_train = train[TARGET].copy()

X_valid = valid[FEATURES].copy()
y_valid = valid[TARGET].copy()

print()
print("--- DATASET ---")
print("Training rows:", len(train))
print("Validation rows:", len(valid))
print("Features:", len(FEATURES))

print()
print("--- FEATURES ---")

for feature in FEATURES:
    print(" -", feature)

print()
print("--- TARGET ---")
print("Training:")
print(y_train.value_counts())

print()
print("Validation:")
print(y_valid.value_counts())

# ============================================================
# PARAMETER GRID
# ============================================================

parameter_grid = [

    {
        "n_estimators": 300,
        "max_depth": None,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "max_features": "sqrt",
    },

    {
        "n_estimators": 500,
        "max_depth": None,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "max_features": "sqrt",
    },

    {
        "n_estimators": 500,
        "max_depth": 10,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "max_features": "sqrt",
    },

    {
        "n_estimators": 500,
        "max_depth": 15,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "max_features": "sqrt",
    },

    {
        "n_estimators": 500,
        "max_depth": 20,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "max_features": "sqrt",
    },

    {
        "n_estimators": 500,
        "max_depth": None,
        "min_samples_split": 5,
        "min_samples_leaf": 1,
        "max_features": "sqrt",
    },

    {
        "n_estimators": 500,
        "max_depth": None,
        "min_samples_split": 10,
        "min_samples_leaf": 1,
        "max_features": "sqrt",
    },

    {
        "n_estimators": 500,
        "max_depth": None,
        "min_samples_split": 2,
        "min_samples_leaf": 2,
        "max_features": "sqrt",
    },

    {
        "n_estimators": 500,
        "max_depth": None,
        "min_samples_split": 2,
        "min_samples_leaf": 4,
        "max_features": "sqrt",
    },

    {
        "n_estimators": 500,
        "max_depth": None,
        "min_samples_split": 5,
        "min_samples_leaf": 2,
        "max_features": "sqrt",
    },

    {
        "n_estimators": 500,
        "max_depth": None,
        "min_samples_split": 10,
        "min_samples_leaf": 2,
        "max_features": "sqrt",
    },

    {
        "n_estimators": 500,
        "max_depth": None,
        "min_samples_split": 5,
        "min_samples_leaf": 4,
        "max_features": "sqrt",
    },

    {
        "n_estimators": 500,
        "max_depth": None,
        "min_samples_split": 10,
        "min_samples_leaf": 4,
        "max_features": "sqrt",
    },

    {
        "n_estimators": 500,
        "max_depth": 15,
        "min_samples_split": 5,
        "min_samples_leaf": 2,
        "max_features": "sqrt",
    },

    {
        "n_estimators": 500,
        "max_depth": 20,
        "min_samples_split": 5,
        "min_samples_leaf": 2,
        "max_features": "sqrt",
    },

    {
        "n_estimators": 500,
        "max_depth": None,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "max_features": 0.5,
    },

    {
        "n_estimators": 500,
        "max_depth": None,
        "min_samples_split": 5,
        "min_samples_leaf": 2,
        "max_features": 0.5,
    },

    {
        "n_estimators": 500,
        "max_depth": 15,
        "min_samples_split": 5,
        "min_samples_leaf": 2,
        "max_features": 0.5,
    },
]

# ============================================================
# TUNING
# ============================================================

results = []

print()
print("=" * 70)
print("                    TUNING")
print("=" * 70)

for i, params in enumerate(parameter_grid, start=1):

    print()
    print("-" * 70)
    print(f"Configuration {i}/{len(parameter_grid)}")
    print("-" * 70)

    print("Parameters:")
    for key, value in params.items():
        print(f"  {key}: {value}")

    model = Pipeline([
        (
            "imputer",
            SimpleImputer(strategy="median")
        ),
        (
            "model",
            RandomForestClassifier(
                random_state=2026,
                n_jobs=-1,
                class_weight="balanced",
                **params
            )
        )
    ])

    model.fit(X_train, y_train)

    y_pred = model.predict(X_valid)
    y_prob = model.predict_proba(X_valid)[:, 1]

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

    tn, fp, fn, tp = confusion_matrix(
        y_valid,
        y_pred
    ).ravel()

    print()
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

    results.append({
        "configuration": i,
        **params,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
    })

# ============================================================
# RESULTS
# ============================================================

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    "roc_auc",
    ascending=False
).reset_index(drop=True)

print()
print("=" * 70)
print("                 TUNING RESULTS")
print("=" * 70)

display_columns = [
    "configuration",
    "n_estimators",
    "max_depth",
    "min_samples_split",
    "min_samples_leaf",
    "max_features",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "roc_auc",
]

print()

print(
    results_df[display_columns].to_string(
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
# BEST MODEL
# ============================================================

best = results_df.iloc[0]

best_params = {
    "n_estimators": int(best["n_estimators"]),
    "max_depth": (
        None
        if pd.isna(best["max_depth"])
        else int(best["max_depth"])
    ),
    "min_samples_split": int(
        best["min_samples_split"]
    ),
    "min_samples_leaf": int(
        best["min_samples_leaf"]
    ),
    "max_features": best["max_features"],
}

print()
print("=" * 70)
print("                  BEST CONFIGURATION")
print("=" * 70)

print()
print("Configuration:", int(best["configuration"]))

for key, value in best_params.items():
    print(f"{key}: {value}")

print()
print("Validation ROC-AUC:", f"{best['roc_auc']:.4f}")
print("Validation Accuracy:", f"{best['accuracy']:.4f}")
print("Validation Precision:", f"{best['precision']:.4f}")
print("Validation Recall:", f"{best['recall']:.4f}")
print("Validation F1:", f"{best['f1']:.4f}")

print()
print("Confusion Matrix:")
print(
    f"[[{int(best['tn'])} {int(best['fp'])}]"
)
print(
    f" [{int(best['fn'])} {int(best['tp'])}]]"
)

# ============================================================
# SAVE ALL RESULTS
# ============================================================

results_file = os.path.join(
    RESULT_DIR,
    "random_forest_tuning.csv"
)

results_df.to_csv(
    results_file,
    index=False
)

# ============================================================
# SAVE BEST MODEL
# ============================================================

best_model = Pipeline([
    (
        "imputer",
        SimpleImputer(strategy="median")
    ),
    (
        "model",
        RandomForestClassifier(
            random_state=2026,
            n_jobs=-1,
            class_weight="balanced",
            **best_params
        )
    )
])

best_model.fit(
    X_train,
    y_train
)

model_file = os.path.join(
    MODEL_DIR,
    "random_forest_tuned.joblib"
)

joblib.dump(
    best_model,
    model_file
)

# ============================================================
# SAVE CONFIGURATION
# ============================================================

config = {
    "model": "random_forest",
    "feature_set": "indices_reduced_spectral",
    "features": FEATURES,
    "parameters": best_params,
    "validation_metrics": {
        "accuracy": float(best["accuracy"]),
        "precision": float(best["precision"]),
        "recall": float(best["recall"]),
        "f1": float(best["f1"]),
        "roc_auc": float(best["roc_auc"]),
    },
}

config_file = os.path.join(
    MODEL_DIR,
    "config.json"
)

with open(config_file, "w") as f:
    json.dump(
        config,
        f,
        indent=4
    )

# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 70)
print("          RANDOM FOREST TUNING COMPLETE")
print("=" * 70)

print()
print("Saved:")
print(" -", results_file)
print(" -", model_file)
print(" -", config_file)

print()
print("=" * 70)