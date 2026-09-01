from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FIND CSV FILES
# ============================================================

csv_files = list(RAW_DIR.glob("*.csv"))

if not csv_files:
    raise FileNotFoundError(
        f"No CSV files found in {RAW_DIR}"
    )

print("CSV files found:")

for file in csv_files:
    print(" -", file.name)


# ============================================================
# LOAD ALL CSV FILES
# ============================================================

dataframes = []

for file in csv_files:

    print(f"\nLoading: {file.name}")

    try:
        df = pd.read_csv(file)

        print("Rows:", len(df))
        print("Columns:", len(df.columns))

        dataframes.append(df)

    except Exception as e:
        print(f"Could not read {file.name}: {e}")


if not dataframes:
    raise ValueError("No valid CSV files could be loaded.")


# ============================================================
# COMBINE DATA
# ============================================================

df = pd.concat(
    dataframes,
    ignore_index=True,
    sort=False
)


# ============================================================
# CLEAN COLUMN NAMES
# ============================================================

df.columns = (
    df.columns
    .astype(str)
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
    .str.replace("-", "_")
)


# ============================================================
# REMOVE DUPLICATES
# ============================================================

before = len(df)

df = df.drop_duplicates()

after = len(df)

print(
    f"\nRemoved {before - after} duplicate rows."
)


# ============================================================
# CLEAN STRING VALUES
# ============================================================

for column in df.select_dtypes(include="object").columns:

    df[column] = (
        df[column]
        .astype(str)
        .str.strip()
    )


# ============================================================
# CONVERT NUMERIC-LIKE COLUMNS
# ============================================================

for column in df.columns:

    if df[column].dtype == "object":

        converted = pd.to_numeric(
            df[column],
            errors="coerce"
        )

        valid_ratio = converted.notna().mean()

        if valid_ratio >= 0.8:
            df[column] = converted


# ============================================================
# REMOVE COMPLETELY EMPTY COLUMNS
# ============================================================

df = df.dropna(
    axis=1,
    how="all"
)


# ============================================================
# SAVE
# ============================================================

output_file = (
    PROCESSED_DIR /
    "base_landslide_dataset.csv"
)

df.to_csv(
    output_file,
    index=False
)


# ============================================================
# INFORMATION
# ============================================================

print("\n====================================")
print("Dataset prepared successfully")
print("====================================")

print("Rows:", len(df))
print("Columns:", len(df.columns))

print("\nColumns:")

for column in df.columns:
    print(" -", column)

print("\nSaved:")
print(output_file)