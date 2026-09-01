from typing import List
from pydantic import BaseModel


# ============================================================
# NEARBY RISK
# ============================================================

class NearbyRisk(BaseModel):

    id: int

    latitude: float

    longitude: float

    landslide_probability: float

    prediction: int

    risk_level: str

    distance_km: float

    created_at: str

    model: str


# ============================================================
# NEARBY RISK RESPONSE
# ============================================================

class NearbyRiskResponse(BaseModel):

    latitude: float

    longitude: float

    radius_km: float

    total_risks: int

    highest_risk: str

    alert: bool

    risks: List[NearbyRisk]


# ============================================================
# HISTORY ITEM
# ============================================================

class RiskHistoryItem(BaseModel):

    id: int

    latitude: float

    longitude: float

    landslide_probability: float

    prediction: int

    risk_level: str

    distance_km: float

    created_at: str

    model: str


# ============================================================
# HISTORY RESPONSE
# ============================================================

class RiskHistoryResponse(BaseModel):

    latitude: float

    longitude: float

    total_predictions: int

    predictions: List[RiskHistoryItem]


# ============================================================
# LATEST RISK
# ============================================================

class LatestRiskResponse(BaseModel):

    latitude: float

    longitude: float

    landslide_probability: float

    prediction: int

    risk_level: str

    model: str

    created_at: str