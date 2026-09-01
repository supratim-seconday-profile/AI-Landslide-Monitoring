import pandas as pd
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

FILE = "data/processed/sih_ml_dataset_684_raw.csv"

df = pd.read_csv(FILE)


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("          SIH SPATIAL DATASET ANALYSIS")
print("=" * 70)

print()
print("Rows:", len(df))
print("Columns:", len(df.columns))


# ============================================================
# EXTRACT COORDINATES FROM .geo
# ============================================================

def extract_coordinates(value):

    try:
        import json

        obj = json.loads(value)

        lon, lat = obj["coordinates"]

        return pd.Series({
            "longitude": float(lon),
            "latitude": float(lat)
        })

    except Exception:

        return pd.Series({
            "longitude": np.nan,
            "latitude": np.nan
        })


coords = df[".geo"].apply(extract_coordinates)

df["longitude"] = coords["longitude"]
df["latitude"] = coords["latitude"]


# ============================================================
# COORDINATE CHECK
# ============================================================

print()
print("--- COORDINATE CHECK ---")

print(
    "Missing latitude:",
    df["latitude"].isna().sum()
)

print(
    "Missing longitude:",
    df["longitude"].isna().sum()
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


# ============================================================
# TARGET-WISE COORDINATE SUMMARY
# ============================================================

print()
print("--- COORDINATES BY TARGET ---")

summary = df.groupby("landslide_target")[
    ["latitude", "longitude"]
].agg(
    ["min", "max", "mean", "std"]
)

print(summary.to_string())


# ============================================================
# TARGET-WISE SAMPLE COUNTS
# ============================================================

print()
print("--- TARGET COUNTS ---")

print(
    df["landslide_target"].value_counts()
    .sort_index()
)


# ============================================================
# QUADRANT DISTRIBUTION
# ============================================================

df["lat_bin"] = pd.cut(
    df["latitude"],
    bins=5
)

df["lon_bin"] = pd.cut(
    df["longitude"],
    bins=5
)

print()
print("--- LATITUDE BIN × TARGET ---")

print(
    pd.crosstab(
        df["lat_bin"],
        df["landslide_target"]
    )
)


print()
print("--- LONGITUDE BIN × TARGET ---")

print(
    pd.crosstab(
        df["lon_bin"],
        df["landslide_target"]
    )
)


# ============================================================
# DISTANCE FROM CLASS CENTROIDS
# ============================================================

print()
print("--- CLASS CENTROIDS ---")

centroids = df.groupby(
    "landslide_target"
)[["latitude", "longitude"]].mean()

print(centroids.to_string())


# ============================================================
# PAIRWISE DISTANCE APPROXIMATION
# ============================================================

print()
print("--- NEAREST OPPOSITE-CLASS DISTANCE ---")

positive = df[
    df["landslide_target"] == 1
][["latitude", "longitude"]].to_numpy()

negative = df[
    df["landslide_target"] == 0
][["latitude", "longitude"]].to_numpy()


def haversine_km(lat1, lon1, lat2, lon2):

    R = 6371.0

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    return 2 * R * np.arcsin(
        np.sqrt(a)
    )


nearest_distances = []

for lat, lon in positive:

    distances = haversine_km(
        lat,
        lon,
        negative[:, 0],
        negative[:, 1]
    )

    nearest_distances.append(
        np.min(distances)
    )


nearest_distances = np.array(
    nearest_distances
)


print(
    "Positive → nearest background:"
)

print(
    "Minimum:",
    nearest_distances.min(),
    "km"
)

print(
    "25%:",
    np.percentile(
        nearest_distances,
        25
    ),
    "km"
)

print(
    "Median:",
    np.median(
        nearest_distances
    ),
    "km"
)

print(
    "75%:",
    np.percentile(
        nearest_distances,
        75
    ),
    "km"
)

print(
    "Maximum:",
    nearest_distances.max(),
    "km"
)


# ============================================================
# CLOSE POSITIVE-BACKGROUND PAIRS
# ============================================================

print()
print("--- POSITIVE/BACKGROUND PROXIMITY ---")

for threshold in [
    1,
    5,
    10,
    25,
    50,
    100
]:

    count = (
        nearest_distances <= threshold
    ).sum()

    print(
        f"Within {threshold:3d} km:",
        count
    )


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print("          SPATIAL ANALYSIS COMPLETE")
print("=" * 70)