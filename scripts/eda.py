import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

INPUT_FILE = Path(
    "data/raw/landslide_inventory.csv"
)

OUTPUT_DIR = Path(
    "data/processed/eda"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading dataset...")

df = pd.read_csv(
    INPUT_FILE
)

print("\nDataset loaded successfully.")

print("Rows:", len(df))
print("Columns:", len(df.columns))


# ============================================================
# BASIC INFORMATION
# ============================================================

print("\n==============================")
print("DATASET INFORMATION")
print("==============================")

print(df.info())


print("\nColumns:")

for column in df.columns:
    print(" -", column)


# ============================================================
# MISSING VALUES
# ============================================================

print("\n==============================")
print("MISSING VALUES")
print("==============================")

missing = (
    df.isnull()
    .sum()
    .sort_values(
        ascending=False
    )
)

print(missing)


# ============================================================
# YEAR
# ============================================================

print("\n==============================")
print("EVENTS BY YEAR")
print("==============================")

year_counts = (
    df["year"]
    .value_counts()
    .sort_index()
)

print(year_counts)


plt.figure(
    figsize=(8, 5)
)

year_counts.plot(
    kind="bar"
)

plt.title(
    "Landslide Events by Year"
)

plt.xlabel(
    "Year"
)

plt.ylabel(
    "Number of Events"
)

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR /
    "events_by_year.png"
)

plt.close()


# ============================================================
# STATE
# ============================================================

print("\n==============================")
print("EVENTS BY STATE")
print("==============================")

state_counts = (
    df["state"]
    .value_counts()
)

print(state_counts)


plt.figure(
    figsize=(10, 6)
)

state_counts.plot(
    kind="bar"
)

plt.title(
    "Landslide Events by State"
)

plt.xlabel(
    "State"
)

plt.ylabel(
    "Number of Events"
)

plt.xticks(
    rotation=45,
    ha="right"
)

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR /
    "events_by_state.png"
)

plt.close()


# ============================================================
# MONTH
# ============================================================

print("\n==============================")
print("EVENTS BY MONTH")
print("==============================")

month_counts = (
    df["event_month"]
    .value_counts()
    .sort_index()
)

print(month_counts)


plt.figure(
    figsize=(9, 5)
)

month_counts.plot(
    kind="bar"
)

plt.title(
    "Landslide Events by Month"
)

plt.xlabel(
    "Month"
)

plt.ylabel(
    "Number of Events"
)

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR /
    "events_by_month.png"
)

plt.close()


# ============================================================
# RAINFALL
# ============================================================

df["rainfall_24h_mm"] = pd.to_numeric(
    df["rainfall_24h_mm"],
    errors="coerce"
)


print("\n==============================")
print("RAINFALL STATISTICS")
print("==============================")

print(
    df[
        "rainfall_24h_mm"
    ].describe()
)


plt.figure(
    figsize=(9, 5)
)

plt.hist(
    df[
        "rainfall_24h_mm"
    ].dropna(),
    bins=30
)

plt.title(
    "24-Hour Rainfall Distribution"
)

plt.xlabel(
    "Rainfall (mm)"
)

plt.ylabel(
    "Number of Landslides"
)

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR /
    "rainfall_distribution.png"
)

plt.close()


# ============================================================
# GEOGRAPHICAL DISTRIBUTION
# ============================================================

plt.figure(
    figsize=(10, 8)
)

plt.scatter(
    df["longitude"],
    df["latitude"],
    s=15,
    alpha=0.7
)

plt.title(
    "Historical Landslide Locations in NER"
)

plt.xlabel(
    "Longitude"
)

plt.ylabel(
    "Latitude"
)

plt.grid(
    True
)

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR /
    "landslide_locations.png"
)

plt.close()


# ============================================================
# ROAD IMPACT
# ============================================================

print("\n==============================")
print("ROAD IMPACT")
print("==============================")

print(
    df[
        "road_affected_flag"
    ].value_counts()
)


# ============================================================
# CASUALTIES
# ============================================================

print("\n==============================")
print("CASUALTIES")
print("==============================")

print(
    df["casualty"]
    .describe()
)


print(
    "\nTotal casualties:",
    df["casualty"]
    .fillna(0)
    .sum()
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n==============================")
print("FINAL SUMMARY")
print("==============================")

print(
    "Total records:",
    len(df)
)

print(
    "Latitude range:",
    df["latitude"].min(),
    "to",
    df["latitude"].max()
)

print(
    "Longitude range:",
    df["longitude"].min(),
    "to",
    df["longitude"].max()
)

print(
    "\nEDA completed."
)

print(
    "Graphs saved in:",
    OUTPUT_DIR
)