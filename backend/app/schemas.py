from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

    B2: float
    B3: float
    B4: float
    B5: float
    B6: float
    B7: float
    B8: float
    B8A: float
    B11: float
    B12: float

    NDVI: float = Field(..., ge=-1, le=1)
    NDMI: float = Field(..., ge=-1, le=1)
    NDWI: float = Field(..., ge=-1, le=1)
    NBR: float = Field(..., ge=-1, le=1)

    hls_image_count: int
    hls_valid_image_count: int


class PredictionResponse(BaseModel):
    latitude: float
    longitude: float
    landslide_probability: float
    prediction: int
    risk_level: str
    model: str