import ee

try:
    ee.Initialize(project="landslide-ne")

    print("=" * 60)
    print("GOOGLE EARTH ENGINE CONNECTION SUCCESS")
    print("=" * 60)

    image = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(
            ee.Geometry.Point([88.606, 27.338])
        )
        .filterDate(
            "2026-01-01",
            "2026-08-31"
        )
        .size()
        .getInfo()
    )

    print(f"Sentinel-2 images found: {image}")

except Exception as e:

    print("=" * 60)
    print("GOOGLE EARTH ENGINE CONNECTION FAILED")
    print("=" * 60)

    print(e)