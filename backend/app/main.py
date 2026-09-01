# ============================================================
# NER LANDSLIDE EARLY WARNING SYSTEM
# FASTAPI BACKEND
# ============================================================

import asyncio

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text
from sqlalchemy.orm import Session


# ============================================================
# WEATHER
# ============================================================

from .weather_schemas import WeatherRequest
from .services.weather_service import get_weather


# ============================================================
# DATABASE
# ============================================================

from .database import SessionLocal
from .models import RiskPrediction


# ============================================================
# SCHEMAS
# ============================================================

from .schemas import (
    PredictionRequest,
    PredictionResponse,
)

from .alert_schemas import (
    LocalRiskRequest,
    LocalRiskResponse,
)

from .risk_schemas import (
    NearbyRiskResponse,
    RiskHistoryResponse,
    LatestRiskResponse,
)


# ============================================================
# SERVICES
# ============================================================

from .services.live_prediction_service import (
    run_live_prediction,
)

from .services.risk import (
    get_risk_level,
    is_alert,
    get_alert_message,
    get_recommended_action,
)


# ============================================================
# VULNERABLE ROAD ROUTE
# ============================================================

from .routes.vulnerable_roads import (
    router as vulnerable_roads_router,
)


# ============================================================
# CONFIGURATION
# ============================================================

LIVE_PREDICTION_TIMEOUT = 120


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="SIH Landslide Risk Monitoring API",

    description=(
        "AI-based landslide risk monitoring and "
        "early warning system for the "
        "North Eastern Region of India."
    ),

    version="2.2.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",

        "http://127.0.0.1:5500",
        "http://localhost:5500",

        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# ROUTER REGISTRATION
# ============================================================

app.include_router(
    vulnerable_roads_router
)


# ============================================================
# DATABASE DEPENDENCY
# ============================================================

def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "message":
            "SIH Landslide Risk Monitoring API",

        "status":
            "running",

        "version":
            "2.2.0",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status":
            "healthy",
    }


# ============================================================
# NORMAL ML PREDICTION
#
# Receives already-extracted satellite features.
# ============================================================

@app.post(
    "/predict",
    response_model=PredictionResponse,
)
def predict(
    request: PredictionRequest,
    db: Session = Depends(get_db),
):

    try:

        # ----------------------------------------------------
        # BUILD FEATURE DICTIONARY
        # ----------------------------------------------------

        features = {

            "B2":
                request.B2,

            "B3":
                request.B3,

            "B4":
                request.B4,

            "B5":
                request.B5,

            "B6":
                request.B6,

            "B7":
                request.B7,

            "B8":
                request.B8,

            "B8A":
                request.B8A,

            "B11":
                request.B11,

            "B12":
                request.B12,

            "NDVI":
                request.NDVI,

            "NDMI":
                request.NDMI,

            "NDWI":
                request.NDWI,

            "NBR":
                request.NBR,

            "hls_image_count":
                request.hls_image_count,

            "hls_valid_image_count":
                request.hls_valid_image_count,
        }


        # ----------------------------------------------------
        # REAL PREDICTOR
        #
        # backend/app/ml/live_predictor.py
        #
        # There is NO predictor.py dependency.
        # ----------------------------------------------------

        from .ml.live_predictor import (
            predict_landslide,
        )


        result = predict_landslide(
            features
        )


        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        probability = float(
            result[
                "landslide_probability"
            ]
        )

        prediction_value = int(
            result[
                "prediction"
            ]
        )

        risk_level = get_risk_level(
            probability
        )

        model_name = result.get(
            "model",
            "SVM RBF",
        )


        # ----------------------------------------------------
        # SAVE DATABASE RECORD
        # ----------------------------------------------------

        record = RiskPrediction(

            latitude=
                request.latitude,

            longitude=
                request.longitude,

            landslide_probability=
                probability,

            prediction=
                prediction_value,

            risk_level=
                risk_level,

            model=
                model_name,
        )


        db.add(record)

        db.commit()

        db.refresh(record)


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {

            "latitude":
                request.latitude,

            "longitude":
                request.longitude,

            "landslide_probability":
                probability,

            "prediction":
                prediction_value,

            "risk_level":
                risk_level,

            "model":
                model_name,
        }


    except Exception as exc:

        db.rollback()

        raise HTTPException(

            status_code=500,

            detail=(
                "Prediction failed: "
                + str(exc)
            ),
        )


# ============================================================
# LOCAL RISK
# ============================================================

@app.post(
    "/local-risk",
    response_model=LocalRiskResponse,
)
def local_risk(
    request: LocalRiskRequest,
    db: Session = Depends(get_db),
):

    if request.radius_km <= 0:

        raise HTTPException(

            status_code=400,

            detail=(
                "radius_km must be "
                "greater than 0."
            ),
        )


    query = text(
        """
        SELECT
            id,
            latitude,
            longitude,
            landslide_probability,
            prediction,
            risk_level,
            model,
            created_at,

            ST_Distance(
                location,
                ST_SetSRID(
                    ST_MakePoint(
                        :longitude,
                        :latitude
                    ),
                    4326
                )::geography
            ) / 1000 AS distance_km

        FROM risk_predictions

        WHERE ST_DWithin(
            location,
            ST_SetSRID(
                ST_MakePoint(
                    :longitude,
                    :latitude
                ),
                4326
            )::geography,
            :radius_m
        )

        ORDER BY
            landslide_probability DESC
        """
    )


    result = db.execute(

        query,

        {
            "latitude":
                request.latitude,

            "longitude":
                request.longitude,

            "radius_m":
                request.radius_km * 1000,
        },
    )


    rows = result.fetchall()


    # --------------------------------------------------------
    # NO DATA
    # --------------------------------------------------------

    if not rows:

        return {

            "latitude":
                request.latitude,

            "longitude":
                request.longitude,

            "radius_km":
                request.radius_km,

            "nearby_risks":
                0,

            "highest_risk":
                "NONE",

            "alert":
                False,

            "message":
                "No nearby predictions available.",
        }


    # --------------------------------------------------------
    # HIGHEST PROBABILITY
    # --------------------------------------------------------

    probabilities = [

        float(
            row.landslide_probability
        )

        for row in rows

    ]


    highest_probability = max(
        probabilities
    )


    highest_risk = get_risk_level(
        highest_probability
    )


    return {

        "latitude":
            request.latitude,

        "longitude":
            request.longitude,

        "radius_km":
            request.radius_km,

        "nearby_risks":
            len(rows),

        "highest_risk":
            highest_risk,

        "alert":
            is_alert(
                highest_probability
            ),

        "message":
            get_alert_message(
                highest_risk
            ),
    }


# ============================================================
# NEARBY RISKS
# ============================================================

@app.post(
    "/nearby-risks",
    response_model=NearbyRiskResponse,
)
def nearby_risks(
    request: LocalRiskRequest,
    db: Session = Depends(get_db),
):

    if request.radius_km <= 0:

        raise HTTPException(

            status_code=400,

            detail=(
                "radius_km must be "
                "greater than 0."
            ),
        )


    query = text(
        """
        SELECT
            id,
            latitude,
            longitude,
            landslide_probability,
            prediction,
            risk_level,
            model,
            created_at,

            ST_Distance(
                location,
                ST_SetSRID(
                    ST_MakePoint(
                        :longitude,
                        :latitude
                    ),
                    4326
                )::geography
            ) / 1000 AS distance_km

        FROM risk_predictions

        WHERE ST_DWithin(
            location,
            ST_SetSRID(
                ST_MakePoint(
                    :longitude,
                    :latitude
                ),
                4326
            )::geography,
            :radius_m
        )

        ORDER BY
            landslide_probability DESC
        """
    )


    result = db.execute(

        query,

        {
            "latitude":
                request.latitude,

            "longitude":
                request.longitude,

            "radius_m":
                request.radius_km * 1000,
        },
    )


    rows = result.fetchall()


    risks = []


    for row in rows:

        risks.append({

            "id":
                row.id,

            "latitude":
                row.latitude,

            "longitude":
                row.longitude,

            "landslide_probability":
                float(
                    row.landslide_probability
                ),

            "prediction":
                row.prediction,

            "risk_level":
                row.risk_level,

            "distance_km":
                round(
                    float(
                        row.distance_km
                    ),
                    3,
                ),

            "created_at":
                row.created_at.isoformat(),

            "model":
                row.model,
        })


    # --------------------------------------------------------
    # NO RISKS
    # --------------------------------------------------------

    if not risks:

        return {

            "latitude":
                request.latitude,

            "longitude":
                request.longitude,

            "radius_km":
                request.radius_km,

            "total_risks":
                0,

            "highest_risk":
                "NONE",

            "alert":
                False,

            "risks":
                [],
        }


    # --------------------------------------------------------
    # HIGHEST RISK
    # --------------------------------------------------------

    highest_probability = max(

        risk[
            "landslide_probability"
        ]

        for risk in risks

    )


    highest_risk = get_risk_level(
        highest_probability
    )


    return {

        "latitude":
            request.latitude,

        "longitude":
            request.longitude,

        "radius_km":
            request.radius_km,

        "total_risks":
            len(risks),

        "highest_risk":
            highest_risk,

        "alert":
            is_alert(
                highest_probability
            ),

        "risks":
            risks,
    }


# ============================================================
# RISK HISTORY
# ============================================================

@app.get(
    "/risk-history",
    response_model=RiskHistoryResponse,
)
def risk_history(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    limit: int = 20,
    db: Session = Depends(get_db),
):

    if radius_km <= 0:

        raise HTTPException(

            status_code=400,

            detail=(
                "radius_km must be "
                "greater than 0."
            ),
        )


    limit = max(

        1,

        min(
            limit,
            100,
        ),
    )


    query = text(
        """
        SELECT
            id,
            latitude,
            longitude,
            landslide_probability,
            prediction,
            risk_level,
            model,
            created_at,

            ST_Distance(
                location,
                ST_SetSRID(
                    ST_MakePoint(
                        :longitude,
                        :latitude
                    ),
                    4326
                )::geography
            ) / 1000 AS distance_km

        FROM risk_predictions

        WHERE ST_DWithin(
            location,
            ST_SetSRID(
                ST_MakePoint(
                    :longitude,
                    :latitude
                ),
                4326
            )::geography,
            :radius_m
        )

        ORDER BY
            created_at DESC

        LIMIT :limit
        """
    )


    result = db.execute(

        query,

        {
            "latitude":
                latitude,

            "longitude":
                longitude,

            "radius_m":
                radius_km * 1000,

            "limit":
                limit,
        },
    )


    rows = result.fetchall()


    predictions = []


    for row in rows:

        predictions.append({

            "id":
                row.id,

            "latitude":
                row.latitude,

            "longitude":
                row.longitude,

            "landslide_probability":
                float(
                    row.landslide_probability
                ),

            "prediction":
                row.prediction,

            "risk_level":
                row.risk_level,

            "distance_km":
                round(
                    float(
                        row.distance_km
                    ),
                    3,
                ),

            "created_at":
                row.created_at.isoformat(),

            "model":
                row.model,
        })


    return {

        "latitude":
            latitude,

        "longitude":
            longitude,

        "total_predictions":
            len(predictions),

        "predictions":
            predictions,
    }


# ============================================================
# ALL RISK POINTS
# ============================================================

@app.get("/risk-points")
def risk_points(
    db: Session = Depends(get_db),
):

    rows = (

        db.query(
            RiskPrediction
        )

        .order_by(
            RiskPrediction.created_at.desc()
        )

        .limit(500)

        .all()

    )


    return [

        {

            "id":
                row.id,

            "latitude":
                row.latitude,

            "longitude":
                row.longitude,

            "landslide_probability":
                float(
                    row.landslide_probability
                ),

            "prediction":
                row.prediction,

            "risk_level":
                row.risk_level,

            "model":
                row.model,

            "created_at":
                row.created_at.isoformat(),
        }

        for row in rows

    ]


# ============================================================
# LATEST RISK
# ============================================================

@app.get(
    "/latest-risk",
    response_model=LatestRiskResponse,
)
def latest_risk(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    db: Session = Depends(get_db),
):

    if radius_km <= 0:

        raise HTTPException(

            status_code=400,

            detail=(
                "radius_km must be "
                "greater than 0."
            ),
        )


    query = text(
        """
        SELECT
            latitude,
            longitude,
            landslide_probability,
            prediction,
            risk_level,
            model,
            created_at,

            ST_Distance(
                location,
                ST_SetSRID(
                    ST_MakePoint(
                        :longitude,
                        :latitude
                    ),
                    4326
                )::geography
            ) / 1000 AS distance_km

        FROM risk_predictions

        WHERE ST_DWithin(
            location,
            ST_SetSRID(
                ST_MakePoint(
                    :longitude,
                    :latitude
                ),
                4326
            )::geography,
            :radius_m
        )

        ORDER BY
            created_at DESC

        LIMIT 1
        """
    )


    result = db.execute(

        query,

        {
            "latitude":
                latitude,

            "longitude":
                longitude,

            "radius_m":
                radius_km * 1000,
        },
    )


    row = result.fetchone()


    # --------------------------------------------------------
    # NO PREDICTION
    # --------------------------------------------------------

    if row is None:

        return {

            "latitude":
                latitude,

            "longitude":
                longitude,

            "landslide_probability":
                0.0,

            "prediction":
                0,

            "risk_level":
                "NONE",

            "model":
                "N/A",

            "created_at":
                "",
        }


    return {

        "latitude":
            row.latitude,

        "longitude":
            row.longitude,

        "landslide_probability":
            float(
                row.landslide_probability
            ),

        "prediction":
            row.prediction,

        "risk_level":
            row.risk_level,

        "model":
            row.model,

        "created_at":
            row.created_at.isoformat(),
    }


# ============================================================
# LIVE SATELLITE PREDICTION
# ============================================================

@app.post("/live-predict")
async def live_predict(
    request: LocalRiskRequest,
    db: Session = Depends(get_db),
):

    print()
    print("=" * 60)
    print("LIVE PREDICTION REQUEST")
    print("=" * 60)

    print(
        "Latitude:",
        request.latitude,
    )

    print(
        "Longitude:",
        request.longitude,
    )

    print(
        "Radius:",
        request.radius_km,
        "km",
    )


    try:

        # ----------------------------------------------------
        # LIVE PIPELINE
        #
        # Earth Engine
        #       ↓
        # live_predictor
        #       ↓
        # SVM
        #       ↓
        # PostgreSQL
        #
        # run_live_prediction() already saves the
        # RiskPrediction record.
        # ----------------------------------------------------

        result = await asyncio.wait_for(

            asyncio.to_thread(

                run_live_prediction,

                request.latitude,

                request.longitude,

                db,
            ),

            timeout=
                LIVE_PREDICTION_TIMEOUT,
        )


        if not result:

            raise RuntimeError(
                "Live prediction returned no result."
            )


        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        probability = float(

            result[
                "landslide_probability"
            ]

        )


        prediction_value = int(

            result[
                "prediction"
            ]

        )


        risk_level = str(

            result.get(

                "risk_level",

                get_risk_level(
                    probability
                ),
            )

        )


        model_name = str(

            result.get(

                "model",

                "SVM RBF",
            )

        )


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        response = {

            "id":
                result.get(
                    "id"
                ),

            "latitude":
                request.latitude,

            "longitude":
                request.longitude,

            "landslide_probability":
                probability,

            "prediction":
                prediction_value,

            "risk_level":
                risk_level,

            "model":
                model_name,

            "alert":
                is_alert(
                    probability
                ),

            "message":
                get_alert_message(
                    risk_level
                ),

            "recommended_action":
                get_recommended_action(
                    risk_level
                ),

            "created_at":
                result.get(
                    "created_at"
                ),
        }


        print()
        print(
            "LIVE PREDICTION SUCCESS"
        )

        print(
            "Probability:",
            probability,
        )

        print(
            "Prediction:",
            prediction_value,
        )

        print(
            "Risk:",
            risk_level,
        )

        print(
            "Model:",
            model_name,
        )

        print("=" * 60)


        return response


    except asyncio.TimeoutError:

        try:

            db.rollback()

        except Exception:

            pass


        print(
            "LIVE PREDICTION TIMEOUT"
        )


        raise HTTPException(

            status_code=504,

            detail=(
                "Live satellite prediction "
                "timed out after "
                f"{LIVE_PREDICTION_TIMEOUT} seconds."
            ),
        )


    except Exception as exc:

        try:

            db.rollback()

        except Exception:

            pass


        print()
        print("=" * 60)
        print("LIVE PREDICTION ERROR")
        print("=" * 60)

        print(
            repr(exc)
        )

        print("=" * 60)


        raise HTTPException(

            status_code=500,

            detail=(
                "Live satellite prediction "
                "failed: "
                + str(exc)
            ),
        )


# ============================================================
# WEATHER
# ============================================================

@app.post("/weather")
def weather(
    request: WeatherRequest,
):

    try:

        result = get_weather(

            request.latitude,

            request.longitude,
        )

        return result


    except Exception as exc:

        raise HTTPException(

            status_code=502,

            detail=str(exc),
        )


# ============================================================
# STARTUP MESSAGE
# ============================================================

print(
    "=" * 60
)

print(
    "SIH LANDSLIDE RISK MONITORING API"
)

print(
    "API INITIALIZED SUCCESSFULLY"
)

print(
    "VULNERABLE ROADS ROUTE ENABLED"
)

print(
    "LIVE SATELLITE PREDICTION ENABLED"
)

print(
    "WEATHER ROUTE ENABLED"
)

print(
    "=" * 60
)