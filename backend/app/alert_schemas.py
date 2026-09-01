from pydantic import BaseModel, Field


class LocalRiskRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(5.0, gt=0, le=100)


class LocalRiskResponse(BaseModel):
    latitude: float
    longitude: float
    radius_km: float
    nearby_risks: int
    highest_risk: str
    alert: bool
    message: str