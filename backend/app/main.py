# ============================================================
# NER LANDSLIDE EARLY WARNING SYSTEM
# FASTAPI BACKEND
# ============================================================

from dotenv import load_dotenv

load_dotenv()

import asyncio
import logging
import os

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    BackgroundTasks,
)

from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import RiskPrediction

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

from .weather_schemas import WeatherRequest

from .services.live_prediction_service import (
    run_live_prediction,
)

from .services.weather_service import (
    get_weather,
)

from .services.risk import (
    get_risk_level,
    is_alert,
    get_alert_message,
    get_recommended_action,
)

from .routes.vulnerable_roads import (
    router as vulnerable_roads_router,
)

from .routes.alerts import (
    router as alerts_router,
)

from .services.alert_service import (
    dispatch_alert,
    get_alert_configuration,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
)

logger = logging.getLogger(
    "ner_landslide"
)


# ============================================================
# CONFIGURATION
# ============================================================

LIVE_PREDICTION_TIMEOUT = int(
    os.getenv(
        "LIVE_PREDICTION_TIMEOUT",
        "120",
    )
)


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

    version="3.0.0",
)


# ============================================================
# CORS
# ============================================================

# The frontend shown in your screenshot is running on:
#
# http://127.0.0.1:3002
#
# Therefore port 3002 must be explicitly allowed.

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://127.0.0.1:3002",
        "http://localhost:3002",

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
# ROUTERS
# ============================================================

app.include_router(
    vulnerable_roads_router
)

app.include_router(
    alerts_router
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
            "3.0.0",

        "features": [
            "SVM RBF landslide prediction",
            "Earth Engine live prediction",
            "PostGIS spatial analysis",
            "Weather monitoring",
            "Vulnerable road monitoring",
            "Automatic alerts",
            "Radius based SMS",
            "Browser push notifications",
            "Offline last-known-risk mode",
            "Alert history",
            "Alert delivery logs",
        ],
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "NER Landslide Early Warning System",
        "version": "3.0.0",
    }


# ============================================================
# ALERT SYSTEM HEALTH
# ============================================================

@app.get("/alert-health")
def alert_health():

    return get_alert_configuration()


# ============================================================
# NORMAL ML PREDICTION
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

        from .ml.live_predictor import (
            predict_landslide,
        )

        result = predict_landslide(
            features
        )

        probability = float(
            result["landslide_probability"]
        )

        prediction_value = int(
            result["prediction"]
        )

        risk_level = get_risk_level(
            probability
        )

        model_name = result.get(
            "model",
            "SVM RBF",
        )

        record = RiskPrediction(

            latitude=request.latitude,

            longitude=request.longitude,

            landslide_probability=probability,

            prediction=prediction_value,

            risk_level=risk_level,

            model=model_name,
        )

        db.add(record)

        db.commit()

        db.refresh(record)

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

        logger.exception(
            "Prediction failed"
        )

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
            detail="radius_km must be greater than 0.",
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

    highest_probability = max(
        float(row.landslide_probability)
        for row in rows
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
            detail="radius_km must be greater than 0.",
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
                    float(row.distance_km),
                    3,
                ),

            "created_at":
                row.created_at.isoformat(),

            "model":
                row.model,
        })

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

    highest_probability = max(
        risk["landslide_probability"]
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
            detail="radius_km must be greater than 0.",
        )

    limit = max(
        1,
        min(limit, 100),
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
                    float(row.distance_km),
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
            detail="radius_km must be greater than 0.",
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
            created_at

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
# LIVE SATELLITE PREDICTION + AUTOMATIC ALERT
# ============================================================

@app.post("/live-predict")
async def live_predict(
    request: LocalRiskRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):

    logger.info(
        "LIVE PREDICTION %.6f, %.6f",
        request.latitude,
        request.longitude,
    )

    try:

        result = await asyncio.wait_for(

            asyncio.to_thread(
                run_live_prediction,

                request.latitude,

                request.longitude,

                db,
            ),

            timeout=LIVE_PREDICTION_TIMEOUT,
        )

        if not result:

            raise RuntimeError(
                "Live prediction returned no result."
            )

        probability = float(
            result["landslide_probability"]
        )

        prediction_value = int(
            result["prediction"]
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

        alert_required = is_alert(
            probability
        )

        message = get_alert_message(
            risk_level
        )

        action = get_recommended_action(
            risk_level
        )

        response = {

            "id":
                result.get("id"),

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
                alert_required,

            "message":
                message,

            "recommended_action":
                action,

            "created_at":
                result.get("created_at"),

            "alert_status":
                "QUEUED"
                if alert_required
                else "NOT_REQUIRED",
        }

        # ====================================================
        # AUTOMATIC ALERT DISPATCH
        # ====================================================

        if alert_required:

            background_tasks.add_task(

                dispatch_alert,

                alert_type="LOCATION",

                level=risk_level,

                title=(
                    f"{risk_level} Landslide Warning"
                ),

                message=message,

                latitude=request.latitude,

                longitude=request.longitude,

                probability=probability,

                prediction_id=result.get(
                    "id"
                ),

                road_name=None,
            )

        logger.info(
            "LIVE PREDICTION SUCCESS | probability=%.4f | risk=%s",
            probability,
            risk_level,
        )

        return response

    except asyncio.TimeoutError:

        try:
            db.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=504,
            detail=(
                "Live satellite prediction "
                f"timed out after {LIVE_PREDICTION_TIMEOUT} seconds."
            ),
        )

    except Exception as exc:

        try:
            db.rollback()
        except Exception:
            pass

        logger.exception(
            "Live prediction failed"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Live satellite prediction failed: "
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

        return get_weather(
            request.latitude,
            request.longitude,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )


# ============================================================
# STARTUP LOGGING
# ============================================================

logger.info(
    "============================================================"
)

logger.info(
    "SIH LANDSLIDE RISK MONITORING API"
)

logger.info(
    "API INITIALIZED SUCCESSFULLY"
)

logger.info(
    "VULNERABLE ROADS ENABLED"
)

logger.info(
    "LIVE SATELLITE PREDICTION ENABLED"
)

logger.info(
    "WEATHER ENABLED"
)

logger.info(
    "AUTOMATIC ALERT SYSTEM ENABLED"
)

logger.info(
    "============================================================"
)