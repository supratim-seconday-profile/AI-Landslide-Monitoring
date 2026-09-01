import sys

sys.path.insert(
    0,
    r"E:\sih_landslide_system\backend"
)

from app.ml.live_predictor import predict_live


latitude = 27.338
longitude = 88.606


print("=" * 60)
print("LIVE SATELLITE → SVM PREDICTION TEST")
print("=" * 60)


try:

    result = predict_live(
        latitude,
        longitude
    )


    print("\nLIVE PREDICTION RESULT")
    print("-" * 60)

    print(
        "Latitude:",
        result["latitude"]
    )

    print(
        "Longitude:",
        result["longitude"]
    )

    print(
        "Probability:",
        result["landslide_probability"]
    )

    print(
        "Prediction:",
        result["prediction"]
    )

    print(
        "Risk Level:",
        result["risk_level"]
    )

    print(
        "Model:",
        result["model"]
    )


    print("\nSATELLITE FEATURES")
    print("-" * 60)

    for key, value in result["features"].items():

        print(
            f"{key:25} : {value}"
        )


    print("\n" + "=" * 60)
    print("LIVE PREDICTION SUCCESS")
    print("=" * 60)


except Exception as e:

    print("\n" + "=" * 60)
    print("LIVE PREDICTION FAILED")
    print("=" * 60)

    print(type(e).__name__)
    print(e)