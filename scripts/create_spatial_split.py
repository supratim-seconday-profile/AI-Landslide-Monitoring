import pandas as pd
import numpy as np
from sklearn.model_selection import GroupShuffleSplit


# ============================================================
# CONFIGURATION
# ============================================================

ML_FILE = "data/processed/sih_ml_dataset_684.csv"

POSITIVE_FILE = (
    "data/processed/positive_landslide_samples.csv"
)

BACKGROUND_FILE = (
    "data/processed/background_hls_samples_342.csv"
)

TRAIN_FILE = "data/processed/spatial_train.csv"
VALID_FILE = "data/processed/spatial_validation.csv"
TEST_FILE = "data/processed/spatial_test.csv"

RANDOM_STATE = 2026

# 0.5 degree ≈ 50–55 km north-south
GRID_SIZE = 0.5


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("             SIH SPATIAL DATASET SPLITTING")
print("=" * 70)


# ============================================================
# LOAD ML DATASET
# ============================================================

ml = pd.read_csv(ML_FILE)

print()
print("--- ML DATASET ---")

print("Rows:", len(ml))
print("Columns:", len(ml.columns))


# ============================================================
# LOAD POSITIVE DATA
# ============================================================

positive = pd.read_csv(
    POSITIVE_FILE
)

print()
print("--- POSITIVE DATASET ---")

print(
    "Rows:",
    len(positive)
)

print(
    "Columns:",
    len(positive.columns)
)


# ============================================================
# LOAD BACKGROUND DATA
# ============================================================

background = pd.read_csv(
    BACKGROUND_FILE
)

print()
print("--- BACKGROUND DATASET ---")

print(
    "Rows:",
    len(background)
)

print(
    "Columns:",
    len(background.columns)
)


# ============================================================
# EXTRACT POSITIVE COORDINATES
# ============================================================

def extract_coordinates(value):

    import json

    try:

        obj = json.loads(value)

        lon = float(
            obj["coordinates"][0]
        )

        lat = float(
            obj["coordinates"][1]
        )

        return pd.Series({
            "longitude": lon,
            "latitude": lat
        })

    except Exception:

        return pd.Series({
            "longitude": np.nan,
            "latitude": np.nan
        })


positive_coords = positive[
    [
        "record_id",
        ".geo"
    ]
].copy()

positive_coords[
    ["longitude", "latitude"]
] = positive_coords[
    ".geo"
].apply(
    extract_coordinates
)


# ============================================================
# EXTRACT BACKGROUND COORDINATES
# ============================================================

background_coords = background[
    [
        "record_id",
        ".geo"
    ]
].copy()

background_coords[
    ["longitude", "latitude"]
] = background_coords[
    ".geo"
].apply(
    extract_coordinates
)


# ============================================================
# COMBINE COORDINATES
# ============================================================

positive_geo = positive_coords[
    [
        "record_id",
        "latitude",
        "longitude"
    ]
].copy()

background_geo = background_coords[
    [
        "record_id",
        "latitude",
        "longitude"
    ]
].copy()


geo = pd.concat(
    [
        positive_geo,
        background_geo
    ],
    ignore_index=True
)


# ============================================================
# GEO ID CHECK
# ============================================================

print()
print("--- GEO DATASET ---")

print(
    "Rows:",
    len(geo)
)

print(
    "Duplicate record IDs:",
    geo["record_id"].duplicated().sum()
)

print(
    "Missing latitude:",
    geo["latitude"].isna().sum()
)

print(
    "Missing longitude:",
    geo["longitude"].isna().sum()
)


if geo["record_id"].duplicated().any():

    raise ValueError(
        "Duplicate record IDs found in coordinate dataset."
    )


if geo[
    ["latitude", "longitude"]
].isna().any().any():

    raise ValueError(
        "Missing or invalid coordinates found."
    )


# ============================================================
# MERGE COORDINATES INTO ML DATASET
# ============================================================

df = ml.merge(
    geo,
    on="record_id",
    how="left",
    validate="one_to_one"
)


print()
print("--- COORDINATE MERGE ---")

print(
    "Rows after merge:",
    len(df)
)

print(
    "Missing latitude:",
    df["latitude"].isna().sum()
)

print(
    "Missing longitude:",
    df["longitude"].isna().sum()
)


if df[
    ["latitude", "longitude"]
].isna().any().any():

    missing = df[
        df[
            ["latitude", "longitude"]
        ].isna().any(axis=1)
    ]["record_id"].tolist()

    print()
    print("Missing IDs:")

    for record_id in missing:

        print(record_id)

    raise ValueError(
        "Some ML records do not have coordinates."
    )


# ============================================================
# COORDINATE RANGE
# ============================================================

print()
print("--- COORDINATE RANGE ---")

print(
    "Latitude:",
    df["latitude"].min(),
    "to",
    df["latitude"].max()
)

print(
    "Longitude:",
    df["longitude"].min(),
    "to",
    df["longitude"].max()
)


# ============================================================
# TARGET CHECK
# ============================================================

print()
print("--- TARGET DISTRIBUTION ---")

print(
    df[
        "landslide_target"
    ].value_counts()
    .sort_index()
)


# ============================================================
# CREATE SPATIAL GRID
# ============================================================

df["grid_lat"] = np.floor(
    df["latitude"] / GRID_SIZE
).astype(int)

df["grid_lon"] = np.floor(
    df["longitude"] / GRID_SIZE
).astype(int)


df["spatial_group"] = (
    df["grid_lat"].astype(str)
    + "_"
    + df["grid_lon"].astype(str)
)


print()
print("--- SPATIAL GRID ---")

print(
    "Grid size:",
    GRID_SIZE,
    "degrees"
)

print(
    "Unique spatial cells:",
    df["spatial_group"].nunique()
)


# ============================================================
# SPATIAL GROUP SUMMARY
# ============================================================

group_summary = (
    df.groupby(
        "spatial_group"
    )[
        "landslide_target"
    ]
    .agg(
        samples="count",
        positives="sum"
    )
)

group_summary[
    "negatives"
] = (
    group_summary["samples"]
    - group_summary["positives"]
)


print()
print("--- SPATIAL GROUP SUMMARY ---")

print(
    "Groups containing positives:",
    (
        group_summary["positives"] > 0
    ).sum()
)

print(
    "Groups containing negatives:",
    (
        group_summary["negatives"] > 0
    ).sum()
)

print(
    "Groups containing both classes:",
    (
        (
            group_summary["positives"] > 0
        )
        &
        (
            group_summary["negatives"] > 0
        )
    ).sum()
)


# ============================================================
# FIRST GROUP SPLIT
# TRAIN = 70%
# TEMP = 30%
# ============================================================

gss1 = GroupShuffleSplit(
    n_splits=1,
    test_size=0.30,
    random_state=RANDOM_STATE
)


train_idx, temp_idx = next(
    gss1.split(
        df,
        y=df["landslide_target"],
        groups=df["spatial_group"]
    )
)


train = df.iloc[
    train_idx
].copy()

temp = df.iloc[
    temp_idx
].copy()


# ============================================================
# SECOND GROUP SPLIT
# VALIDATION = 15%
# TEST = 15%
# ============================================================

gss2 = GroupShuffleSplit(
    n_splits=1,
    test_size=0.50,
    random_state=RANDOM_STATE
)


valid_idx, test_idx = next(
    gss2.split(
        temp,
        y=temp["landslide_target"],
        groups=temp["spatial_group"]
    )
)


validation = temp.iloc[
    valid_idx
].copy()

test = temp.iloc[
    test_idx
].copy()


# ============================================================
# SPLIT SIZE CHECK
# ============================================================

print()
print("--- SPATIAL SPLIT SIZES ---")

print(
    "Training:",
    len(train)
)

print(
    "Validation:",
    len(validation)
)

print(
    "Test:",
    len(test)
)

print(
    "Total:",
    len(train)
    + len(validation)
    + len(test)
)


# ============================================================
# TARGET DISTRIBUTION
# ============================================================

print()
print("--- TRAIN TARGET ---")

print(
    train[
        "landslide_target"
    ].value_counts()
    .sort_index()
)


print()
print("--- VALIDATION TARGET ---")

print(
    validation[
        "landslide_target"
    ].value_counts()
    .sort_index()
)


print()
print("--- TEST TARGET ---")

print(
    test[
        "landslide_target"
    ].value_counts()
    .sort_index()
)


# ============================================================
# CLASS PERCENTAGES
# ============================================================

def show_distribution(
    name,
    data
):

    print()
    print(name)

    counts = (
        data[
            "landslide_target"
        ]
        .value_counts()
        .sort_index()
    )

    total = len(data)

    for cls in [0, 1]:

        count = counts.get(
            cls,
            0
        )

        percentage = (
            count / total * 100
            if total > 0
            else 0
        )

        print(
            f"Class {cls}: "
            f"{count} "
            f"({percentage:.2f}%)"
        )


show_distribution(
    "TRAIN DISTRIBUTION",
    train
)

show_distribution(
    "VALIDATION DISTRIBUTION",
    validation
)

show_distribution(
    "TEST DISTRIBUTION",
    test
)


# ============================================================
# SPATIAL GROUP OVERLAP
# ============================================================

train_groups = set(
    train["spatial_group"]
)

valid_groups = set(
    validation["spatial_group"]
)

test_groups = set(
    test["spatial_group"]
)


print()
print("--- SPATIAL GROUP OVERLAP ---")

print(
    "Train ∩ Validation:",
    len(
        train_groups
        & valid_groups
    )
)

print(
    "Train ∩ Test:",
    len(
        train_groups
        & test_groups
    )
)

print(
    "Validation ∩ Test:",
    len(
        valid_groups
        & test_groups
    )
)


# ============================================================
# RECORD ID OVERLAP
# ============================================================

train_ids = set(
    train["record_id"]
)

valid_ids = set(
    validation["record_id"]
)

test_ids = set(
    test["record_id"]
)


print()
print("--- RECORD ID OVERLAP ---")

print(
    "Train ∩ Validation:",
    len(
        train_ids
        & valid_ids
    )
)

print(
    "Train ∩ Test:",
    len(
        train_ids
        & test_ids
    )
)

print(
    "Validation ∩ Test:",
    len(
        valid_ids
        & test_ids
    )
)


# ============================================================
# REMOVE HELPER COLUMNS
# ============================================================

remove_columns = [
    "latitude",
    "longitude",
    "grid_lat",
    "grid_lon",
    "spatial_group"
]


train = train.drop(
    columns=remove_columns
)

validation = validation.drop(
    columns=remove_columns
)

test = test.drop(
    columns=remove_columns
)


# ============================================================
# SAVE DATASETS
# ============================================================

train.to_csv(
    TRAIN_FILE,
    index=False
)

validation.to_csv(
    VALID_FILE,
    index=False
)

test.to_csv(
    TEST_FILE,
    index=False
)


# ============================================================
# FINAL FILE CHECK
# ============================================================

print()
print("--- FINAL FILE CHECK ---")

train_check = pd.read_csv(
    TRAIN_FILE
)

valid_check = pd.read_csv(
    VALID_FILE
)

test_check = pd.read_csv(
    TEST_FILE
)


print(
    "Train rows:",
    len(train_check)
)

print(
    "Validation rows:",
    len(valid_check)
)

print(
    "Test rows:",
    len(test_check)
)

print(
    "Total rows:",
    len(train_check)
    + len(valid_check)
    + len(test_check)
)


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print("             SPATIAL SPLIT COMPLETE")
print("=" * 70)

print()
print("Saved files:")

print(
    " -",
    TRAIN_FILE
)

print(
    " -",
    VALID_FILE
)

print(
    " -",
    TEST_FILE
)

print()
print("=" * 70)