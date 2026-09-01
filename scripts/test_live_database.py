import sys

sys.path.insert(
    0,
    r"E:\sih_landslide_system\backend"
)

from app.database import SessionLocal
from app.services.live_prediction_service import (
    run_live_prediction
)


latitude = 27.338
longitude = 88.606


print("=" * 60)
print("LIVE PREDICTION → POSTGRESQL TEST")
print("=" * 60)


db = SessionLocal()


try:

    result = run_live_prediction(
        latitude,
        longitude,
        db
    )

    print("\nLIVE RESULT")
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
        "Risk:",
        result["risk_level"]
    )

    print(
        "Model:",
        result["model"]
    )

    print("\n" + "=" * 60)
    print("DATABASE INSERTION SUCCESS")
    print("=" * 60)


except Exception as e:

    db.rollback()

    print("\n" + "=" * 60)
    print("DATABASE INSERTION FAILED")
    print("=" * 60)

    print(type(e).__name__)
    print(e)


finally:

    db.close()