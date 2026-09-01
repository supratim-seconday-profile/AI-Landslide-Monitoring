import rasterio
from pathlib import Path


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


for i, dem_file in enumerate(DEM_FILES, start=1):

    print("\n" + "=" * 70)
    print(f"DEM PART {i}")
    print("=" * 70)

    print("File:")
    print(dem_file)

    if not dem_file.exists():
        print("ERROR: File does not exist")
        continue

    with rasterio.open(dem_file) as src:

        print("\nRaster information")

        print("CRS:", src.crs)
        print("Width:", src.width)
        print("Height:", src.height)
        print("Bands:", src.count)
        print("Resolution:", src.res)

        print("\nGeographic bounds:")

        print("Left   :", src.bounds.left)
        print("Bottom :", src.bounds.bottom)
        print("Right  :", src.bounds.right)
        print("Top    :", src.bounds.top)

        print("\nNoData:", src.nodata)
        print("Data type:", src.dtypes[0])

        print("\nFile size:")

        print(
            f"{dem_file.stat().st_size / (1024**3):.2f} GB"
        )

        # Read only a tiny sample
        sample_window = rasterio.windows.Window(
            0,
            0,
            min(100, src.width),
            min(100, src.height)
        )

        sample = src.read(
            1,
            window=sample_window,
            masked=True
        )

        print("\nSmall sample statistics:")

        if sample.count() > 0:

            print(
                "Minimum sample elevation:",
                float(sample.min())
            )

            print(
                "Maximum sample elevation:",
                float(sample.max())
            )