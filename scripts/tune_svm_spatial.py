import os
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)

# ============================================================
# SIH SPATIAL SVM HYPERPARAMETER TUNING
# ============================================================

print("=" * 70)
print("             SIH SPATIAL SVM HYPERPARAMETER TUNING")
print("=" * 70)

TRAIN_FILE = "data/processed/spatial_train.csv"
VAL_FILE = "data/processed/spatial_validation.csv"

RESULT_DIR = "data/processed/model_results"
MODEL_DIR = "models/tuned_spatial_svm"

os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

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
# LOAD DATA
# ------------------------------------------------------------

train = pd.read_csv(TRAIN_FILE)
val = pd.read_csv(VAL_FILE)

X_train = train[FEATURES]
y_train = train[TARGET]

X_val = val[FEATURES]
y_val = val[TARGET]

print()
print("--- DATASET ---")
print("Training rows:", len(train))
print("Validation rows:", len(val))
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
print(y_val.value_counts())

# ------------------------------------------------------------
# CONFIGURATIONS
# ------------------------------------------------------------

configs = []

C_VALUES = [
    0.1,
    0.5,
    1,
    2,
    5,
    10,
    20,
]

GAMMA_VALUES = [
    "scale",
    0.01,
    0.03,
    0.1,
]

for C in C_VALUES:
    for gamma in GAMMA_VALUES:

        configs.append({
            "C": C,
            "gamma": gamma,
            "kernel": "rbf",
            "class_weight": None
        })

# Also test balanced weighting because early-warning recall matters.
for C in [0.5, 1, 2, 5, 10]:
    for gamma in ["scale", 0.03, 0.1]:

        configs.append({
            "C": C,
            "gamma": gamma,
            "kernel": "rbf",
            "class_weight": "balanced"
        })

print()
print("=" * 70)
print("                       TUNING")
print("=" * 70)

results = []

best_score = -np.inf
best_config = None
best_model = None

# ------------------------------------------------------------
# TRAIN CONFIGURATIONS
# ------------------------------------------------------------

for i, config in enumerate(configs, start=1):

    print()
    print("-" * 70)
    print(f"Configuration {i}/{len(configs)}")
    print("-" * 70)

    print("Parameters:")

    for key, value in config.items():
        print(f"  {key}: {value}")

    model = Pipeline([
        (
            "scaler",
            StandardScaler()
        ),
        (
            "svm",
            SVC(
                C=config["C"],
                gamma=config["gamma"],
                kernel=config["kernel"],
                class_weight=config["class_weight"],
                probability=True,
                random_state=42
            )
        )
    ])

    model.fit(
        X_train,
        y_train
    )

    y_pred = model.predict(X_val)
    y_prob = model.predict_proba(X_val)[:, 1]

    accuracy = accuracy_score(
        y_val,
        y_pred
    )

    precision = precision_score(
        y_val,
        y_pred,
        zero_division=0
    )

    recall = recall_score(
        y_val,
        y_pred,
        zero_division=0
    )

    f1 = f1_score(
        y_val,
        y_pred,
        zero_division=0
    )

    roc_auc = roc_auc_score(
        y_val,
        y_prob
    )

    print()
    print("Accuracy :", f"{accuracy:.4f}")
    print("Precision:", f"{precision:.4f}")
    print("Recall   :", f"{recall:.4f}")
    print("F1-score :", f"{f1:.4f}")
    print("ROC-AUC  :", f"{roc_auc:.4f}")

    results.append({
        "configuration": i,
        **config,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc
    })

    # Primary selection metric = ROC-AUC
    if roc_auc > best_score:

        best_score = roc_auc
        best_config = config.copy()
        best_model = model

# ------------------------------------------------------------
# RESULTS
# ------------------------------------------------------------

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    "roc_auc",
    ascending=False
)

print()
print("=" * 70)
print("                 SVM TUNING RESULTS")
print("=" * 70)

print(
    results_df.to_string(
        index=False
    )
)

# ------------------------------------------------------------
# BEST CONFIGURATION
# ------------------------------------------------------------

y_best_pred = best_model.predict(X_val)
y_best_prob = best_model.predict_proba(X_val)[:, 1]

best_accuracy = accuracy_score(
    y_val,
    y_best_pred
)

best_precision = precision_score(
    y_val,
    y_best_pred,
    zero_division=0
)

best_recall = recall_score(
    y_val,
    y_best_pred,
    zero_division=0
)

best_f1 = f1_score(
    y_val,
    y_best_pred,
    zero_division=0
)

best_roc_auc = roc_auc_score(
    y_val,
    y_best_prob
)

tn, fp, fn, tp = confusion_matrix(
    y_val,
    y_best_pred
).ravel()

print()
print("=" * 70)
print("                  BEST SVM CONFIGURATION")
print("=" * 70)

for key, value in best_config.items():
    print(f"{key}: {value}")

print()
print("Validation ROC-AUC :", f"{best_roc_auc:.4f}")
print("Validation Accuracy:", f"{best_accuracy:.4f}")
print("Validation Precision:", f"{best_precision:.4f}")
print("Validation Recall   :", f"{best_recall:.4f}")
print("Validation F1       :", f"{best_f1:.4f}")

print()
print("Confusion Matrix:")
print(
    f"[[{tn} {fp}]"
)
print(
    f" [{fn} {tp}]]"
)

# ------------------------------------------------------------
# SAVE MODEL
# ------------------------------------------------------------

model_file = os.path.join(
    MODEL_DIR,
    "svm_tuned.joblib"
)

joblib.dump(
    best_model,
    model_file
)

# ------------------------------------------------------------
# SAVE RESULTS
# ------------------------------------------------------------

results_file = os.path.join(
    RESULT_DIR,
    "spatial_svm_tuning.csv"
)

results_df.to_csv(
    results_file,
    index=False
)

config_file = os.path.join(
    MODEL_DIR,
    "config.json"
)

with open(config_file, "w") as f:

    json.dump(
        {
            "model": "svm_rbf",
            "features": FEATURES,
            "n_features": len(FEATURES),
            "best_config": best_config,
            "validation_accuracy": best_accuracy,
            "validation_precision": best_precision,
            "validation_recall": best_recall,
            "validation_f1": best_f1,
            "validation_roc_auc": best_roc_auc
        },
        f,
        indent=4
    )

print()
print("=" * 70)
print("             SPATIAL SVM TUNING COMPLETE")
print("=" * 70)

print()
print("Saved:")
print(" -", results_file)
print(" -", model_file)
print(" -", config_file)

print()
print("=" * 70)