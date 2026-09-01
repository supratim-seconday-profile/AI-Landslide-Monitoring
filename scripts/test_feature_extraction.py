from app.ml.earth_engine.extractor import extract_features


latitude = 27.338
longitude = 88.606


print("=" * 60)
print("SENTINEL-2 FEATURE EXTRACTION TEST")
print("=" * 60)


try:

    features = extract_features(
        latitude,
        longitude
    )


    print("\nExtracted features:\n")


    for key, value in features.items():

        print(
            f"{key:25} : {value}"
        )


    print("\n" + "=" * 60)
    print("FEATURE EXTRACTION SUCCESS")
    print("=" * 60)


except Exception as e:

    print("\n" + "=" * 60)
    print("FEATURE EXTRACTION FAILED")
    print("=" * 60)

    print(e)