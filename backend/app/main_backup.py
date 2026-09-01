from .risk_schemas import (
    NearbyRiskResponse,
    RiskHistoryResponse,
    LatestRiskResponse
)
from .risk_schemas import NearbyRiskResponse
from sqlalchemy import text
from .alert_schemas import LocalRiskRequest, LocalRiskResponse
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .services.live_prediction_service import run_live_prediction
from .database import SessionLocal
from .models import RiskPrediction
from .schemas import PredictionRequest, PredictionResponse

from app.ml.predictor import predict_landslide


app = FastAPI(
    title="SIH Landslide Risk Monitoring API",
    description="Local landslide risk prediction and monitoring system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "message": "SIH Landslide Risk Monitoring API",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(
    request: PredictionRequest,
    db: Session = Depends(get_db)
):

    features = {
        "B2": request.B2,
        "B3": request.B3,
        "B4": request.B4,
        "B5": request.B5,
        "B6": request.B6,
        "B7": request.B7,
        "B8": request.B8,
        "B8A": request.B8A,
        "B11": request.B11,
        "B12": request.B12,
        "NDVI": request.NDVI,
        "NDMI": request.NDMI,
        "NDWI": request.NDWI,
        "NBR": request.NBR,
        "hls_image_count": request.hls_image_count,
        "hls_valid_image_count": request.hls_valid_image_count,
    }

    result = predict_landslide(features)

    probability = result["landslide_probability"]
    prediction = result["prediction"]

    if probability >= 0.70:
        risk_level = "HIGH"
    elif probability >= 0.50:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    record = RiskPrediction(
        latitude=request.latitude,
        longitude=request.longitude,
        landslide_probability=probability,
        prediction=prediction,
        risk_level=risk_level,
        model=result["model"]
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "latitude": request.latitude,
        "longitude": request.longitude,
        "landslide_probability": probability,
        "prediction": prediction,
        "risk_level": risk_level,
        "model": result["model"]
    }


@app.post("/local-risk", response_model=LocalRiskResponse)
def local_risk(
    request: LocalRiskRequest,
    db: Session = Depends(get_db)
):

    query = text("""
        SELECT
            risk_level,
            landslide_probability,
            ST_Distance(
                location,
                ST_SetSRID(
                    ST_MakePoint(:longitude, :latitude),
                    4326
                )::geography
            ) / 1000 AS distance_km
        FROM risk_predictions
        WHERE ST_DWithin(
            location,
            ST_SetSRID(
                ST_MakePoint(:longitude, :latitude),
                4326
            )::geography,
            :radius_m
        )
        ORDER BY landslide_probability DESC
    """)

    result = db.execute(
        query,
        {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "radius_m": request.radius_km * 1000
        }
    )

    rows = result.fetchall()

    nearby_risks = len(rows)

    if nearby_risks == 0:
        return {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "radius_km": request.radius_km,
            "nearby_risks": 0,
            "highest_risk": "NONE",
            "alert": False,
            "message": "No nearby landslide risk detected."
        }

    highest_probability = max(
        row.landslide_probability for row in rows
    )

    if highest_probability >= 0.70:
        highest_risk = "HIGH"
        alert = True
        message = "HIGH landslide risk detected nearby."

    elif highest_probability >= 0.50:
        highest_risk = "MEDIUM"
        alert = True
        message = "MEDIUM landslide risk detected nearby."

    else:
        highest_risk = "LOW"
        alert = False
        message = "Nearby landslide risk is currently LOW."

    return {
        "latitude": request.latitude,
        "longitude": request.longitude,
        "radius_km": request.radius_km,
        "nearby_risks": nearby_risks,
        "highest_risk": highest_risk,
        "alert": alert,
        "message": message
    }

@app.post("/nearby-risks", response_model=NearbyRiskResponse)
def nearby_risks(
    request: LocalRiskRequest,
    db: Session = Depends(get_db)
):

    query = text("""
        SELECT
            id,
            latitude,
            longitude,
            landslide_probability,
            prediction,
            risk_level,
            created_at,
            ST_Distance(
                location,
                ST_SetSRID(
                    ST_MakePoint(:longitude, :latitude),
                    4326
                )::geography
            ) / 1000 AS distance_km
        FROM risk_predictions
        WHERE ST_DWithin(
            location,
            ST_SetSRID(
                ST_MakePoint(:longitude, :latitude),
                4326
            )::geography,
            :radius_m
        )
        ORDER BY landslide_probability DESC
    """)

    result = db.execute(
        query,
        {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "radius_m": request.radius_km * 1000
        }
    )

    rows = result.fetchall()

    risks = []

    for row in rows:
        risks.append({
            "id": row.id,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "landslide_probability": row.landslide_probability,
            "prediction": row.prediction,
            "risk_level": row.risk_level,
            "distance_km": round(float(row.distance_km), 3),
            "created_at": row.created_at.isoformat()
        })

    if not risks:
        return {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "radius_km": request.radius_km,
            "total_risks": 0,
            "highest_risk": "NONE",
            "alert": False,
            "risks": []
        }

    highest_probability = max(
        risk["landslide_probability"]
        for risk in risks
    )

    if highest_probability >= 0.70:
        highest_risk = "HIGH"
        alert = True

    elif highest_probability >= 0.50:
        highest_risk = "MEDIUM"
        alert = True

    else:
        highest_risk = "LOW"
        alert = False

    return {
        "latitude": request.latitude,
        "longitude": request.longitude,
        "radius_km": request.radius_km,
        "total_risks": len(risks),
        "highest_risk": highest_risk,
        "alert": alert,
        "risks": risks
    }

@app.get("/risk-history", response_model=RiskHistoryResponse)
def risk_history(
    latitude: float,
    longitude: float,
    limit: int = 20,
    db: Session = Depends(get_db)
):

    query = text("""
        SELECT
            id,
            latitude,
            longitude,
            landslide_probability,
            prediction,
            risk_level,
            created_at,
            ST_Distance(
                location,
                ST_SetSRID(
                    ST_MakePoint(:longitude, :latitude),
                    4326
                )::geography
            ) / 1000 AS distance_km
        FROM risk_predictions
        WHERE latitude = :latitude
          AND longitude = :longitude
        ORDER BY created_at DESC
        LIMIT :limit
    """)

    result = db.execute(
        query,
        {
            "latitude": latitude,
            "longitude": longitude,
            "limit": limit
        }
    )

    rows = result.fetchall()

    predictions = []

    for row in rows:
        predictions.append({
            "id": row.id,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "landslide_probability": row.landslide_probability,
            "prediction": row.prediction,
            "risk_level": row.risk_level,
            "distance_km": 0.0,
            "created_at": row.created_at.isoformat()
        })

    return {
        "latitude": latitude,
        "longitude": longitude,
        "total_predictions": len(predictions),
        "predictions": predictions
    }


@app.get("/risk-points")
def risk_points(
    db: Session = Depends(get_db)
):
    rows = db.query(RiskPrediction).order_by(
        RiskPrediction.created_at.desc()
    ).limit(100).all()

    return [
        {
            "id": row.id,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "landslide_probability": row.landslide_probability,
            "prediction": row.prediction,
            "risk_level": row.risk_level,
            "model": row.model,
            "created_at": row.created_at.isoformat()
        }
        for row in rows
    ]
@app.get("/latest-risk", response_model=LatestRiskResponse)
def latest_risk(
    latitude: float,
    longitude: float,
    db: Session = Depends(get_db)
):

    query = text("""
        SELECT
            latitude,
            longitude,
            landslide_probability,
            prediction,
            risk_level,
            model,
            created_at
        FROM risk_predictions
        WHERE latitude = :latitude
          AND longitude = :longitude
        ORDER BY created_at DESC
        LIMIT 1
    """)

    result = db.execute(
        query,
        {
            "latitude": latitude,
            "longitude": longitude
        }
    )

    row = result.fetchone()

    if row is None:
        return {
            "latitude": latitude,
            "longitude": longitude,
            "landslide_probability": 0.0,
            "prediction": 0,
            "risk_level": "NONE",
            "model": "N/A",
            "created_at": ""
        }

    return {
        "latitude": row.latitude,
        "longitude": row.longitude,
        "landslide_probability": row.landslide_probability,
        "prediction": row.prediction,
        "risk_level": row.risk_level,
        "model": row.model,
        "created_at": row.created_at.isoformat()
    }



@app.post("/live-predict")
def live_predict(
    request: LocalRiskRequest,
    db: Session = Depends(get_db)
):

    result = run_live_prediction(
        latitude=request.latitude,
        longitude=request.longitude,
        db=db
    )

    return {
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "landslide_probability": result[
            "landslide_probability"
        ],
        "prediction": result["prediction"],
        "risk_level": result["risk_level"],
        "model": result["model"]
    }