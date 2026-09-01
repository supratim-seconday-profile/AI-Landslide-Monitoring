# ============================================================
# NER LANDSLIDE EARLY WARNING SYSTEM
# LIVE PREDICTION SERVICE
# ============================================================

from typing import Any, Dict

from sqlalchemy.orm import Session

from ..models import RiskPrediction
from ..ml.live_predictor import predict_live


# ============================================================
# RUN LIVE PREDICTION
# ============================================================

def run_live_prediction(
    latitude: float,
    longitude: float,
    db: Session
) -> Dict[str, Any]:

    print()
    print("=" * 60)
    print("LIVE PREDICTION SERVICE")
    print("=" * 60)

    print(
        f"Latitude: {latitude}"
    )

    print(
        f"Longitude: {longitude}"
    )

    print(
        "Starting Earth Engine + ML prediction..."
    )


    # ========================================================
    # LIVE SATELLITE PREDICTION
    # ========================================================

    result = predict_live(
        latitude,
        longitude
    )


    if not result:

        raise RuntimeError(
            "Live predictor returned no result."
        )


    print(
        "Satellite prediction completed."
    )


    # ========================================================
    # EXTRACT RESULT
    # ========================================================

    probability = float(
        result["landslide_probability"]
    )

    prediction = int(
        result["prediction"]
    )

    risk_level = str(
        result["risk_level"]
    )

    model = str(
        result["model"]
    )


    # ========================================================
    # SAVE PREDICTION
    # ========================================================

    record = RiskPrediction(

        latitude=latitude,

        longitude=longitude,

        landslide_probability=probability,

        prediction=prediction,

        risk_level=risk_level,

        model=model

    )


    db.add(record)

    db.commit()

    db.refresh(record)


    # ========================================================
    # ADD DATABASE ID
    # ========================================================

    result["id"] = record.id


    # ========================================================
    # ADD CREATED TIME
    # ========================================================

    if getattr(
        record,
        "created_at",
        None
    ) is not None:

        result["created_at"] = (
            record.created_at.isoformat()
        )


    # ========================================================
    # LOG
    # ========================================================

    print()
    print("Prediction saved successfully.")

    print(
        "Database ID:",
        record.id
    )

    print(
        "Probability:",
        probability
    )

    print(
        "Prediction:",
        prediction
    )

    print(
        "Risk:",
        risk_level
    )

    print(
        "Model:",
        model
    )

    print("=" * 60)
    print("LIVE PREDICTION SERVICE SUCCESS")
    print("=" * 60)


    return result