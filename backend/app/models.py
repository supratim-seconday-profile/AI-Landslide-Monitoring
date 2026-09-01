from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.sql import func
from geoalchemy2 import Geography

from .database import Base


class RiskPrediction(Base):
    __tablename__ = "risk_predictions"

    id = Column(Integer, primary_key=True, index=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    location = Column(
        Geography(
            geometry_type="POINT",
            srid=4326
        )
    )

    landslide_probability = Column(Float, nullable=False)
    prediction = Column(Integer, nullable=False)
    risk_level = Column(String(20), nullable=False)
    model = Column(String(50), nullable=False)

    created_at = Column(
        DateTime,
        server_default=func.now()
    )