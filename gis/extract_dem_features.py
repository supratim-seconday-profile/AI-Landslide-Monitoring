import pandas as pd
import numpy as np
import rasterio

from pathlib import Path


# ============================================================
# FILES
# ============================================================

CSV_FILE = Path(
    "data/raw/landslide_inventory.csv"
)

DEM_FILES = [
    Path(
        "data/external/dem/"
        "rasters_COP30/output_hh.tif"
    ),

    Path(
        "data/external/dem/"
        "rasters_COP30 (1)/output_hh.tif"
    )
]

OUTPUT_FILE = Path(
    "data/processed/landslide_dem_features.csv"
)


# ============================================================
# LOAD LANDSLIDE DATA
# ============================================================

print("Loading landslide dataset...")

df = pd.read_csv(
    CSV_FILE
)

print(
    f"Loaded {len(df)} landslide records."
)


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "latitude",
    "longitude"
]

for column in required_columns:

    if column not in df.columns:

        raise ValueError(
            f"Required column '{column}' "
            "not found in CSV."
        )


# ============================================================
# OPEN BOTH DEMs
# ============================================================

dem_sources = []

for dem_file in DEM_FILES:

    print(
        f"\nOpening DEM: {dem_file}"
    )

    src = rasterio.open(
        dem_file
    )

    print(
        "Bounds:",
        src.bounds
    )

    print(
        "Resolution:",
        src.res
    )

    dem_sources.append(src)


# ============================================================
# FIND WHICH DEM CONTAINS A POINT
# ============================================================

def find_dem(
    latitude,
    longitude
):

    for src in dem_sources:

        bounds = src.bounds

        if (
            bounds.left <= longitude <= bounds.right
            and
            bounds.bottom <= latitude <= bounds.top
        ):

            return src

    return None


# ============================================================
# CALCULATE TERRAIN FEATURES
# ============================================================

def extract_features(
    src,
    latitude,
    longitude,
    window_size=5
):

    # --------------------------------------------------------
    # Convert geographic coordinate to raster row/column
    # --------------------------------------------------------

    row, col = src.index(
        longitude,
        latitude
    )


    half = window_size // 2


    # --------------------------------------------------------
    # Make sure window stays inside raster
    # --------------------------------------------------------

    row_start = max(
        0,
        row - half
    )

    row_stop = min(
        src.height,
        row + half + 1
    )

    col_start = max(
        0,
        col - half
    )

    col_stop = min(
        src.width,
        col + half + 1
    )


    # --------------------------------------------------------
    # Read only small local window
    # --------------------------------------------------------

    window = rasterio.windows.Window(
        col_start,
        row_start,
        col_stop - col_start,
        row_stop - row_start
    )


    elevation_data = src.read(
        1,
        window=window
    ).astype(
        "float64"
    )


    # --------------------------------------------------------
    # Convert nodata
    # --------------------------------------------------------

    if src.nodata is not None:

        elevation_data[
            elevation_data == src.nodata
        ] = np.nan


    # --------------------------------------------------------
    # Check center pixel
    # --------------------------------------------------------

    center_row = row - row_start
    center_col = col - col_start


    if not (
        0 <= center_row < elevation_data.shape[0]
        and
        0 <= center_col < elevation_data.shape[1]
    ):

        return (
            np.nan,
            np.nan,
            np.nan
        )


    elevation = elevation_data[
        center_row,
        center_col
    ]


    if np.isnan(elevation):

        return (
            np.nan,
            np.nan,
            np.nan
        )


    # --------------------------------------------------------
    # Need enough pixels for gradient
    # --------------------------------------------------------

    if (
        elevation_data.shape[0] < 3
        or
        elevation_data.shape[1] < 3
    ):

        return (
            float(elevation),
            np.nan,
            np.nan
        )


    # --------------------------------------------------------
    # Fill isolated missing values locally
    # --------------------------------------------------------

    if np.isnan(
        elevation_data
    ).any():

        local_mean = np.nanmean(
            elevation_data
        )

        elevation_data[
            np.isnan(elevation_data)
        ] = local_mean


    # --------------------------------------------------------
    # Pixel dimensions
    #
    # DEM is EPSG:4326.
    # Convert degrees approximately to metres.
    # --------------------------------------------------------

    pixel_width_deg = abs(
        src.transform.a
    )

    pixel_height_deg = abs(
        src.transform.e
    )


    # Latitude-dependent east-west distance

    meters_per_degree_lat = 111320.0

    meters_per_degree_lon = (
        111320.0
        *
        np.cos(
            np.radians(latitude)
        )
    )


    dx = (
        pixel_width_deg
        *
        meters_per_degree_lon
    )

    dy = (
        pixel_height_deg
        *
        meters_per_degree_lat
    )


    # --------------------------------------------------------
    # Calculate gradients
    # --------------------------------------------------------

    gradient_y, gradient_x = np.gradient(
        elevation_data,
        dy,
        dx
    )


    dzdx = gradient_x[
        center_row,
        center_col
    ]

    dzdy = gradient_y[
        center_row,
        center_col
    ]


    # --------------------------------------------------------
    # SLOPE
    # --------------------------------------------------------

    slope_radians = np.arctan(
        np.sqrt(
            dzdx ** 2
            +
            dzdy ** 2
        )
    )


    slope_degrees = np.degrees(
        slope_radians
    )


    # --------------------------------------------------------
    # ASPECT
    #
    # 0°   = North
    # 90°  = East
    # 180° = South
    # 270° = West
    # --------------------------------------------------------

    if (
        abs(dzdx) < 1e-12
        and
        abs(dzdy) < 1e-12
    ):

        aspect_degrees = np.nan

    else:

        aspect_degrees = np.degrees(
            np.arctan2(
                -dzdx,
                -dzdy
            )
        )

        aspect_degrees = (
            aspect_degrees + 360
        ) % 360


    return (
        float(elevation),
        float(slope_degrees),
        float(aspect_degrees)
    )


# ============================================================
# PROCESS ALL LANDSLIDES
# ============================================================

elevations = []
slopes = []
aspects = []

dem_used = []


print("\n")
print("=" * 70)
print("EXTRACTING TERRAIN FEATURES")
print("=" * 70)


for index, row in df.iterrows():

    latitude = float(
        row["latitude"]
    )

    longitude = float(
        row["longitude"]
    )


    src = find_dem(
        latitude,
        longitude
    )


    if src is None:

        print(
            f"[{index + 1}/{len(df)}] "
            f"NO DEM FOUND at "
            f"{latitude}, {longitude}"
        )

        elevations.append(
            np.nan
        )

        slopes.append(
            np.nan
        )

        aspects.append(
            np.nan
        )

        dem_used.append(
            "NONE"
        )

        continue


    elevation, slope, aspect = extract_features(
        src,
        latitude,
        longitude
    )


    elevations.append(
        elevation
    )

    slopes.append(
        slope
    )

    aspects.append(
        aspect
    )


    if src == dem_sources[0]:

        dem_used.append(
            "PART1"
        )

    else:

        dem_used.append(
            "PART2"
        )


    print(
        f"[{index + 1}/{len(df)}] "
        f"Lat={latitude:.5f} "
        f"Lon={longitude:.5f} "
        f"Elevation={elevation:.1f} m "
        f"Slope={slope:.2f}° "
        f"Aspect={aspect:.2f}°"
    )


# ============================================================
# ADD FEATURES TO DATAFRAME
# ============================================================

df["elevation"] = elevations

df["slope"] = slopes

df["aspect"] = aspects

df["dem_source"] = dem_used


# ============================================================
# SAVE
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)


df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# CLOSE DEM FILES
# ============================================================

for src in dem_sources:

    src.close()


# ============================================================
# SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("DEM FEATURE EXTRACTION COMPLETE")
print("=" * 70)

print(
    "Total records:",
    len(df)
)

print(
    "Elevation missing:",
    df["elevation"].isna().sum()
)

print(
    "Slope missing:",
    df["slope"].isna().sum()
)

print(
    "Aspect missing:",
    df["aspect"].isna().sum()
)

print(
    "\nDEM usage:"
)

print(
    df["dem_source"]
    .value_counts()
)

print(
    "\nElevation statistics:"
)

print(
    df["elevation"].describe()
)

print(
    "\nSlope statistics:"
)

print(
    df["slope"].describe()
)

print(
    "\nOutput:"
)

print(
    OUTPUT_FILE
)