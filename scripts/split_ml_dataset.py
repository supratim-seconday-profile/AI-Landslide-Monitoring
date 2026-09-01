import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split


# ==========================================================
# CONFIGURATION
# ==========================================================

INPUT = "data/processed/sih_ml_dataset_684.csv"

OUTPUT_TRAIN = "data/processed/ml_train.csv"
OUTPUT_VAL = "data/processed/ml_validation.csv"
OUTPUT_TEST = "data/processed/ml_test.csv"


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
ID = "record_id"


RANDOM_STATE = 2026


# ==========================================================
# HEADER
# ==========================================================

print("=" * 70)
print("             SIH ML DATASET SPLITTING")
print("=" * 70)


# ==========================================================
# LOAD DATA
# ==========================================================

df = pd.read_csv(INPUT)

print()
print("Input rows:", len(df))
print("Input columns:", len(df.columns))


# ==========================================================
# BASIC CHECK
# ==========================================================

required = FEATURES + [TARGET, ID]

missing_columns = [
    c for c in required
    if c not in df.columns
]

if missing_columns:

    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )


if df[ID].duplicated().any():

    raise ValueError(
        "Duplicate record IDs detected."
    )


if df[TARGET].isna().any():

    raise ValueError(
        "Missing target values detected."
    )


# ==========================================================
# TARGET CHECK
# ==========================================================

print()
print("--- ORIGINAL TARGET ---")

print(
    df[TARGET]
    .value_counts()
    .sort_index()
)


# ==========================================================
# FIRST SPLIT
#
# 70% TRAIN
# 30% TEMP
# ==========================================================

train_df, temp_df = train_test_split(
    df,
    test_size=0.30,
    stratify=df[TARGET],
    random_state=RANDOM_STATE,
)


# ==========================================================
# SECOND SPLIT
#
# TEMP = 30%
#
# Half of TEMP = 15% total
#
# 15% VALIDATION
# 15% TEST
# ==========================================================

val_df, test_df = train_test_split(
    temp_df,
    test_size=0.50,
    stratify=temp_df[TARGET],
    random_state=RANDOM_STATE,
)


# ==========================================================
# SORT BY RECORD ID
# ==========================================================

train_df = train_df.sort_values(ID).reset_index(drop=True)
val_df = val_df.sort_values(ID).reset_index(drop=True)
test_df = test_df.sort_values(ID).reset_index(drop=True)


# ==========================================================
# CHECK OVERLAP
# ==========================================================

train_ids = set(train_df[ID])
val_ids = set(val_df[ID])
test_ids = set(test_df[ID])


train_val_overlap = train_ids & val_ids
train_test_overlap = train_ids & test_ids
val_test_overlap = val_ids & test_ids


print()
print("--- ID OVERLAP CHECK ---")

print(
    "Train ∩ Validation:",
    len(train_val_overlap)
)

print(
    "Train ∩ Test:",
    len(train_test_overlap)
)

print(
    "Validation ∩ Test:",
    len(val_test_overlap)
)


if (
    train_val_overlap
    or train_test_overlap
    or val_test_overlap
):

    raise ValueError(
        "Dataset split contains ID leakage."
    )


# ==========================================================
# SAVE ONLY REQUIRED COLUMNS
# ==========================================================

SAVE_COLUMNS = FEATURES + [TARGET, ID]


train_df[SAVE_COLUMNS].to_csv(
    OUTPUT_TRAIN,
    index=False
)

val_df[SAVE_COLUMNS].to_csv(
    OUTPUT_VAL,
    index=False
)

test_df[SAVE_COLUMNS].to_csv(
    OUTPUT_TEST,
    index=False
)


# ==========================================================
# DATASET SUMMARY
# ==========================================================

print()
print("--- SPLIT SIZES ---")

print(
    "Training:",
    len(train_df)
)

print(
    "Validation:",
    len(val_df)
)

print(
    "Test:",
    len(test_df)
)

print(
    "Total:",
    len(train_df)
    + len(val_df)
    + len(test_df)
)


# ==========================================================
# TARGET DISTRIBUTION
# ==========================================================

print()
print("--- TRAIN TARGET ---")

print(
    train_df[TARGET]
    .value_counts()
    .sort_index()
)


print()
print("--- VALIDATION TARGET ---")

print(
    val_df[TARGET]
    .value_counts()
    .sort_index()
)


print()
print("--- TEST TARGET ---")

print(
    test_df[TARGET]
    .value_counts()
    .sort_index()
)


# ==========================================================
# PERCENTAGES
# ==========================================================

print()
print("--- SPLIT PERCENTAGES ---")

total = len(df)

print(
    f"Train:      {len(train_df)/total*100:.2f}%"
)

print(
    f"Validation: {len(val_df)/total*100:.2f}%"
)

print(
    f"Test:       {len(test_df)/total*100:.2f}%"
)


# ==========================================================
# FINAL CHECK
# ==========================================================

if len(train_df) + len(val_df) + len(test_df) != len(df):

    raise ValueError(
        "Split row counts do not match original dataset."
    )


print()
print("=" * 70)
print("             DATASET SPLIT COMPLETE")
print("=" * 70)

print()
print("Saved files:")

print(
    f"  - {OUTPUT_TRAIN}"
)

print(
    f"  - {OUTPUT_VAL}"
)

print(
    f"  - {OUTPUT_TEST}"
)

print()
print("=" * 70)