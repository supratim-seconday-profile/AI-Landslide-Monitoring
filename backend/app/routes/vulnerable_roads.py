"""
NER LANDSLIDE EARLY WARNING SYSTEM
VULNERABLE ROADS API ROUTES

This module exposes the vulnerable-road analysis
to the frontend.

IMPORTANT:
    This file MUST define:

        router

because backend/app/main.py imports:

        from .routes.vulnerable_roads import (
            router as vulnerable_roads_router
        )
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.vulnerable_road_service import (
    get_vulnerable_roads,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/vulnerable-roads",
    tags=["Vulnerable Roads"],
)


# ============================================================
# REQUEST MODEL
# ============================================================

class VulnerableRoadRequest(BaseModel):
    """
    Request body accepted by POST /vulnerable-roads
    """

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Selected latitude",
    )

    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Selected longitude",
    )

    radius_km: float = Field(
        default=5.0,
        gt=0.0,
        le=25.0,
        description="Road analysis radius in km",
    )


# ============================================================
# RESPONSE NORMALIZER
# ============================================================

def normalize_response(
    result: dict,
) -> dict:
    """
    Ensure the response always contains the fields
    expected by the frontend.
    """

    if not isinstance(
        result,
        dict,
    ):
        return {
            "success": False,
            "roads": [],
            "message": (
                "Invalid vulnerable-road "
                "service response."
            ),
        }

    roads = result.get(
        "roads",
        [],
    )

    if not isinstance(
        roads,
        list,
    ):
        roads = []

    return {
        "success": bool(
            result.get(
                "success",
                True,
            )
        ),

        "latitude": result.get(
            "latitude"
        ),

        "longitude": result.get(
            "longitude"
        ),

        "radius_km": result.get(
            "radius_km",
            5.0,
        ),

        "risk_locations": result.get(
            "risk_locations",
            [],
        ),

        "total_roads_analyzed": result.get(
            "total_roads_analyzed",
            len(roads),
        ),

        "vulnerable_roads_count": result.get(
            "vulnerable_roads_count",
            len(roads),
        ),

        "summary": result.get(
            "summary",
            {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "safe": 0,
            },
        ),

        "roads": roads,

        "source": result.get(
            "source",
            "OpenStreetMap / Overpass",
        ),

        "message": result.get(
            "message",
            "Vulnerable road analysis completed.",
        ),

        "analysis_time_seconds": result.get(
            "analysis_time_seconds"
        ),
    }


# ============================================================
# CORE ANALYSIS
# ============================================================

def run_road_analysis(
    latitude: float,
    longitude: float,
    radius_km: float,
    db: Session,
) -> dict:
    """
    Shared function used by GET and POST.
    """

    try:

        result = get_vulnerable_roads(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
        )

        return normalize_response(
            result
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:

        # Overpass / external road-data failure.
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Vulnerable road analysis failed."
            ),
        ) from exc


# ============================================================
# POST
# ============================================================

@router.post("")
def vulnerable_roads(
    request: VulnerableRoadRequest,
    db: Session = Depends(
        get_db
    ),
):
    """
    Analyze vulnerable roads around a selected location.

    POST /vulnerable-roads
    """

    return run_road_analysis(
        latitude=request.latitude,
        longitude=request.longitude,
        radius_km=request.radius_km,
        db=db,
    )


# ============================================================
# GET
# ============================================================

@router.get("")
def vulnerable_roads_get(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    db: Session = Depends(
        get_db
    ),
):
    """
    GET version for browser/API testing.

    Example:

    /vulnerable-roads?latitude=27.338
    &longitude=88.606
    &radius_km=5
    """

    if radius_km <= 0:
        radius_km = 5.0

    if radius_km > 25.0:
        radius_km = 25.0

    return run_road_analysis(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        db=db,
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@router.get("/health")
def vulnerable_roads_health():
    """
    Simple health endpoint.

    GET /vulnerable-roads/health
    """

    return {
        "success": True,
        "service": "vulnerable-roads",
        "status": "operational",
    }


# ============================================================
# END OF ROUTES
# ============================================================