"""
Vulnerable Roads API Routes
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.vulnerable_road_service import (
    get_vulnerable_roads,
)


router = APIRouter(
    prefix="/vulnerable-roads",
    tags=["Vulnerable Roads"],
)


# ============================================================
# GET
# ============================================================

@router.get("")
def vulnerable_roads(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius_km: float = Query(
        5.0,
        gt=0,
        le=25,
    ),
    db: Session = Depends(get_db),
):
    """
    Analyze road vulnerability around a location.
    """

    try:

        return get_vulnerable_roads(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
        )

    except RuntimeError as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Vulnerable road analysis failed: "
                f"{str(exc)}"
            ),
        ) from exc


# ============================================================
# POST
# ============================================================

@router.post("")
def vulnerable_roads_post(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    db: Session = Depends(get_db),
):
    """
    POST version for frontend/API clients.
    """

    try:

        return get_vulnerable_roads(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
        )

    except RuntimeError as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Vulnerable road analysis failed: "
                f"{str(exc)}"
            ),
        ) from exc