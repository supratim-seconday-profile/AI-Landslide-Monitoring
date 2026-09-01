import ee


# ============================================================
# GOOGLE EARTH ENGINE INITIALIZATION
# ============================================================

ee.Initialize(project="landslide-ne")


# ============================================================
# SENTINEL-2 FEATURE EXTRACTION
# ============================================================

def extract_features(latitude, longitude):

    point = ee.Geometry.Point([
        longitude,
        latitude
    ])

    # --------------------------------------------------------
    # SENTINEL-2 COLLECTION
    # --------------------------------------------------------

    collection = (
        ee.ImageCollection(
            "COPERNICUS/S2_SR_HARMONIZED"
        )
        .filterBounds(point)
        .filterDate(
            "2026-01-01",
            "2026-08-31"
        )
        .filter(
            ee.Filter.lt(
                "CLOUDY_PIXEL_PERCENTAGE",
                30
            )
        )
    )

    # --------------------------------------------------------
    # IMAGE COUNT
    # --------------------------------------------------------

    image_count = collection.size()

    # --------------------------------------------------------
    # CHECK THAT IMAGES EXIST
    # --------------------------------------------------------

    count = image_count.getInfo()

    if count == 0:
        raise ValueError(
            "No suitable Sentinel-2 images found "
            "for this location and date range."
        )

    # --------------------------------------------------------
    # MEDIAN COMPOSITE
    # --------------------------------------------------------

    image = collection.median()

    # --------------------------------------------------------
    # SENTINEL-2 REFLECTANCE SCALE
    #
    # Sentinel-2 SR bands are stored approximately
    # on a 0-10000 scale.
    #
    # Training data uses approximately 0-1 reflectance.
    # --------------------------------------------------------

    image = image.select([
        "B2",
        "B3",
        "B4",
        "B5",
        "B6",
        "B7",
        "B8",
        "B8A",
        "B11",
        "B12"
    ]).multiply(0.0001)

    # --------------------------------------------------------
    # SPECTRAL INDICES
    # --------------------------------------------------------

    ndvi = image.normalizedDifference(
        ["B8", "B4"]
    ).rename("NDVI")

    ndmi = image.normalizedDifference(
        ["B8", "B11"]
    ).rename("NDMI")

    ndwi = image.normalizedDifference(
        ["B3", "B8"]
    ).rename("NDWI")

    nbr = image.normalizedDifference(
        ["B8", "B12"]
    ).rename("NBR")

    # --------------------------------------------------------
    # COMBINE FEATURES
    # --------------------------------------------------------

    feature_image = image.addBands([
        ndvi,
        ndmi,
        ndwi,
        nbr
    ])

    # --------------------------------------------------------
    # EXTRACT PIXEL VALUES
    # --------------------------------------------------------

    values = feature_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=point,
        scale=10,
        bestEffort=True
    )

    result = values.getInfo()

    # --------------------------------------------------------
    # HLS QUALITY FEATURES
    #
    # IMPORTANT:
    # These are Sentinel-2 observation counts used as
    # operational proxies for the HLS sampling features
    # expected by the current model.
    # --------------------------------------------------------

    result["hls_image_count"] = count
    result["hls_valid_image_count"] = count

    return result