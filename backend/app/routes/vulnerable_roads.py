"""
Vulnerable Roads API Routes
============================================================

Responsibilities
----------------
1. Find road segments around the selected location.
2. Accept live landslide probability/risk from the frontend.
3. Calculate a road vulnerability score.
4. Assign CRITICAL / HIGH / MEDIUM / LOW.
5. Return data in a frontend-friendly format.
6. Support both GET and JSON POST.
7. Avoid the previous POST 422 problem.

Important
---------
The road vulnerability score is an exposure estimate, NOT a
separate ML prediction.

It combines:
    - current landslide probability
    - distance from the selected risk location
    - road hierarchy / importance

The SVM remains responsible for landslide probability.
This endpoint translates that hazard into road exposure.
"""

from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from pydantic import BaseModel, Field

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
# REQUEST MODEL
# ============================================================

class VulnerableRoadRequest(BaseModel):
    """
    JSON body accepted by POST /vulnerable-roads.
    """

    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
    )

    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
    )

    radius_km: float = Field(
        default=5.0,
        gt=0,
        le=25,
    )

    probability: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
    )

    risk_level: Optional[str] = None


# ============================================================
# CONSTANTS
# ============================================================

ROAD_CLASS_WEIGHTS = {
    # National / major highways
    "motorway": 1.00,
    "trunk": 1.00,

    # Major roads
    "primary": 0.90,
    "secondary": 0.78,

    # Smaller roads
    "tertiary": 0.65,
    "unclassified": 0.55,

    # Local roads
    "residential": 0.45,
    "service": 0.35,

    # Rural / minor access
    "track": 0.30,
    "path": 0.20,
    "footway": 0.15,

    # Generic values returned by some OSM queries
    "road": 0.50,
    "street": 0.50,
}


# ============================================================
# BASIC HELPERS
# ============================================================

def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:

    return max(
        minimum,
        min(
            maximum,
            float(value),
        ),
    )


def normalize_probability(
    probability: Optional[float],
) -> Optional[float]:

    if probability is None:
        return None

    try:

        value = float(probability)

    except (
        TypeError,
        ValueError,
    ):

        return None

    # Defensive handling in case a caller sends
    # 57.2 instead of 0.572.
    if value > 1:

        value = value / 100.0

    return clamp(
        value,
        0.0,
        1.0,
    ) / 100.0


def normalize_risk_level(
    level: Optional[str],
) -> str:

    if not level:

        return "LOW"

    value = str(
        level
    ).strip().upper()

    aliases = {
        "MODERATE": "MEDIUM",
        "MED": "MEDIUM",
        "SEVERE": "HIGH",
        "EXTREME": "CRITICAL",
    }

    value = aliases.get(
        value,
        value,
    )

    if value not in {
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    }:

        return "LOW"

    return value


def probability_to_risk(
    probability: float,
) -> str:
    """
    Convert the SVM probability into the same
    broad risk categories used by the application.
    """

    p = float(
        probability
    )

    if p >= 0.85:
        return "CRITICAL"

    if p >= 0.70:
        return "HIGH"

    if p >= 0.50:
        return "MEDIUM"

    return "LOW"


# ============================================================
# ROAD TYPE
# ============================================================

def get_road_type(
    road: Dict[str, Any],
) -> str:

    value = (
        road.get("road_type")
        or road.get("highway")
        or road.get("type")
        or road.get("class")
        or "Road"
    )

    return str(
        value
    ).strip()


def road_importance(
    road: Dict[str, Any],
) -> float:

    road_type = get_road_type(
        road
    ).lower()

    # Handle values such as:
    # "Primary Road", "NH", etc.
    for key, weight in ROAD_CLASS_WEIGHTS.items():

        if key in road_type:

            return weight

    # Generic road
    return ROAD_CLASS_WEIGHTS[
        "road"
    ]


# ============================================================
# GEOMETRY HELPERS
# ============================================================

def extract_coordinates(
    geometry: Any,
) -> List[List[float]]:

    if not geometry:
        return []

    if isinstance(
        geometry,
        dict,
    ):

        geometry_type = geometry.get(
            "type"
        )

        coordinates = geometry.get(
            "coordinates"
        )

    else:

        return []

    if not coordinates:
        return []

    result = []

    def walk(
        value: Any,
    ):

        if (
            isinstance(value, list)
            and len(value) >= 2
            and isinstance(value[0], (int, float))
            and isinstance(value[1], (int, float))
        ):

            result.append(
                [
                    float(value[0]),
                    float(value[1]),
                ]
            )

            return

        if isinstance(
            value,
            list,
        ):

            for item in value:

                walk(
                    item
                )

    walk(
        coordinates
    )

    return result


def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:

    import math

    earth_radius_km = 6371.0088

    phi1 = math.radians(
        lat1
    )

    phi2 = math.radians(
        lat2
    )

    d_phi = math.radians(
        lat2 - lat1
    )

    d_lambda = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(
            d_phi / 2
        ) ** 2
        +
        math.cos(phi1)
        *
        math.cos(phi2)
        *
        math.sin(
            d_lambda / 2
        ) ** 2
    )

    return (
        2
        *
        earth_radius_km
        *
        math.asin(
            math.sqrt(a)
        )
    )


def calculate_road_distance(
    road: Dict[str, Any],
    latitude: float,
    longitude: float,
) -> Optional[float]:
    """
    Prefer distance already supplied by the road service.

    Otherwise calculate the minimum distance between the
    selected point and coordinates contained in the road
    geometry.
    """

    for key in (
        "nearest_risk_distance_km",
        "distance_km",
        "distance",
    ):

        value = road.get(
            key
        )

        if value is not None:

            try:

                return round(
                    float(value),
                    3,
                )

            except (
                TypeError,
                ValueError,
            ):

                pass

    geometry = road.get(
        "geometry"
    )

    coordinates = extract_coordinates(
        geometry
    )

    if not coordinates:

        return None

    distances = []

    for coordinate in coordinates:

        if len(coordinate) < 2:
            continue

        lon = coordinate[0]
        lat = coordinate[1]

        try:

            distances.append(
                haversine_km(
                    latitude,
                    longitude,
                    lat,
                    lon,
                )
            )

        except Exception:

            continue

    if not distances:

        return None

    return round(
        min(distances),
        3,
    )


# ============================================================
# VULNERABILITY CALCULATION
# ============================================================

def calculate_vulnerability_score(
    probability: float,
    distance_km: Optional[float],
    radius_km: float,
    importance: float,
) -> float:
    """
    Calculate road exposure score.

    Formula:

        hazard_component
        + proximity_component
        + importance_component

    Hazard:
        0 - 70 points

    Proximity:
        0 - 20 points

    Road importance:
        0 - 10 points
    """

    probability = clamp(
        probability,
        0,
        1,
    )

    radius_km = max(
        0.1,
        float(radius_km),
    )

    # --------------------------------------------------------
    # HAZARD
    # --------------------------------------------------------

    hazard_component = (
        probability
        * 70.0
    )

    # --------------------------------------------------------
    # PROXIMITY
    # --------------------------------------------------------

    if distance_km is None:

        # If geometry/distance isn't available,
        # don't pretend that the road is right beside
        # the hazard.

        proximity_factor = 0.50

    else:

        distance = max(
            0.0,
            float(distance_km),
        )

        proximity_factor = max(
            0.0,
            min(
                1.0,
                1.0
                -
                (
                    distance
                    /
                    radius_km
                ),
            ),
        )

    proximity_component = (
        proximity_factor
        * 20.0
    )

    # --------------------------------------------------------
    # ROAD IMPORTANCE
    # --------------------------------------------------------

    importance_component = (
        max(
            0.0,
            min(
                1.0,
                float(importance),
            ),
        )
        * 10.0
    )

    score = (
        hazard_component
        +
        proximity_component
        +
        importance_component
    )

    return round(
        clamp(
            score,
            0,
            100,
        ),
        1,
    )


def score_to_level(
    score: float,
) -> str:

    score = float(
        score
    )

    if score >= 75:
        return "CRITICAL"

    if score >= 50:
        return "HIGH"

    if score >= 25:
        return "MEDIUM"

    return "LOW"


# ============================================================
# ROAD REASON
# ============================================================

def build_reason(
    level: str,
    probability: float,
    distance_km: Optional[float],
    road_type: str,
) -> str:

    probability_percent = (
        probability
        * 100
    )

    if distance_km is None:

        distance_text = (
            "within the selected analysis area"
        )

    else:

        distance_text = (
            f"approximately "
            f"{distance_km:.2f} km from "
            f"the selected location"
        )

    if level == "CRITICAL":

        return (
            f"Critical road exposure: "
            f"landslide probability is "
            f"{probability_percent:.1f}% "
            f"and the {road_type} is "
            f"{distance_text}."
        )

    if level == "HIGH":

        return (
            f"High road exposure: "
            f"landslide probability is "
            f"{probability_percent:.1f}% "
            f"and the {road_type} is "
            f"{distance_text}."
        )

    if level == "MEDIUM":

        return (
            f"Moderate road exposure: "
            f"landslide probability is "
            f"{probability_percent:.1f}% "
            f"and the {road_type} is "
            f"{distance_text}."
        )

    return (
        f"Low estimated road exposure: "
        f"current landslide probability is "
        f"{probability_percent:.1f}%."
    )


def build_recommendation(
    level: str,
) -> str:

    if level == "CRITICAL":

        return (
            "Immediate field inspection, "
            "traffic preparedness and coordination "
            "with local authorities recommended."
        )

    if level == "HIGH":

        return (
            "Prioritise inspection and prepare "
            "traffic-control or diversion measures."
        )

    if level == "MEDIUM":

        return (
            "Increase monitoring and inspect "
            "drainage, slopes and road edges."
        )

    return (
        "Continue routine monitoring."
    )


# ============================================================
# EXTRACT ROAD LIST
# ============================================================

def extract_roads(
    result: Any,
) -> List[Dict[str, Any]]:

    if result is None:

        return []

    if isinstance(
        result,
        list,
    ):

        return [
            item
            for item in result
            if isinstance(
                item,
                dict,
            )
        ]

    if not isinstance(
        result,
        dict,
    ):

        return []

    # Most common backend responses
    for key in (
        "roads",
        "road_segments",
        "features",
        "data",
        "results",
    ):

        value = result.get(
            key
        )

        if isinstance(
            value,
            list,
        ):

            return [
                item
                for item in value
                if isinstance(
                    item,
                    dict,
                )
            ]

    return []


def rebuild_response(
    original: Any,
    roads: List[Dict[str, Any]],
) -> Any:

    if isinstance(
        original,
        dict,
    ):

        response = dict(
            original
        )

        if "roads" in response:

            response["roads"] = roads

        elif "road_segments" in response:

            response["road_segments"] = roads

        elif "features" in response:

            response["features"] = roads

        else:

            response["roads"] = roads

        response[
            "road_count"
        ] = len(
            roads
        )

        return response

    return {
        "roads": roads,
        "road_count": len(
            roads
        ),
    }


# ============================================================
# ENRICH ROAD DATA
# ============================================================

def enrich_roads(
    result: Any,
    latitude: float,
    longitude: float,
    radius_km: float,
    probability: Optional[float],
    risk_level: Optional[str],
) -> Any:
    """
    Attach the current live landslide prediction to every
    nearby road and calculate road vulnerability.
    """

    roads = extract_roads(
        result
    )

    # --------------------------------------------------------
    # Determine probability
    # --------------------------------------------------------

    normalized_probability = (
        normalize_probability(
            probability
        )
    )

    # If no live probability was supplied, don't invent one.
    #
    # We can still preserve existing road data.
    if normalized_probability is None:

        return result

    # --------------------------------------------------------
    # Calculate each road
    # --------------------------------------------------------

    enriched = []

    for index, original_road in enumerate(
        roads
    ):

        road = dict(
            original_road
        )

        road_type = get_road_type(
            road
        )

        importance = road_importance(
            road
        )

        distance_km = calculate_road_distance(
            road,
            latitude,
            longitude,
        )

        score = calculate_vulnerability_score(
            probability=normalized_probability,
            distance_km=distance_km,
            radius_km=radius_km,
            importance=importance,
        )

        level = score_to_level(
            score
        )

        # ----------------------------------------------------
        # Preserve road name
        # ----------------------------------------------------

        road_name = (
            road.get("road_name")
            or road.get("name")
            or road.get("ref")
            or f"Road Segment {index + 1}"
        )

        # ----------------------------------------------------
        # Write canonical fields
        # ----------------------------------------------------

        road["road_name"] = (
            str(
                road_name
            )
        )

        road["road_type"] = (
            road_type
        )

        road["distance_km"] = (
            distance_km
            if distance_km is not None
            else road.get(
                "distance_km"
            )
        )

        road[
            "landslide_probability"
        ] = round(
            normalized_probability,
            4,
        )

        road[
            "probability"
        ] = round(
            normalized_probability,
            4,
        )

        road[
            "vulnerability_score"
        ] = score

        road[
            "road_vulnerability_score"
        ] = score

        road[
            "risk_score"
        ] = score

        road[
            "score"
        ] = score

        road[
            "vulnerability_level"
        ] = level

        road[
            "risk_level"
        ] = level

        road[
            "risk"
        ] = level

        road[
            "road_risk"
        ] = level

        road[
            "reason"
        ] = build_reason(
            level=level,
            probability=normalized_probability,
            distance_km=distance_km,
            road_type=road_type,
        )

        road[
            "recommended_action"
        ] = build_recommendation(
            level
        )

        road[
            "road_importance"
        ] = round(
            importance,
            2,
        )

        enriched.append(
            road
        )

    # --------------------------------------------------------
    # Highest vulnerability first
    # --------------------------------------------------------

    enriched.sort(
        key=lambda item: float(
            item.get(
                "vulnerability_score",
                0,
            )
            or 0
        ),
        reverse=True,
    )

    response = rebuild_response(
        result,
        enriched,
    )

    # --------------------------------------------------------
    # Add summary
    # --------------------------------------------------------

    response[
        "summary"
    ] = {
        "total": len(
            enriched
        ),
        "critical": sum(
            1
            for road in enriched
            if str(
                road.get(
                    "vulnerability_level",
                    "",
                )
            ).upper()
            == "CRITICAL"
        ),
        "high": sum(
            1
            for road in enriched
            if str(
                road.get(
                    "vulnerability_level",
                    "",
                )
            ).upper()
            == "HIGH"
        ),
        "medium": sum(
            1
            for road in enriched
            if str(
                road.get(
                    "vulnerability_level",
                    "",
                )
            ).upper()
            == "MEDIUM"
        ),
        "low": sum(
            1
            for road in enriched
            if str(
                road.get(
                    "vulnerability_level",
                    "",
                )
            ).upper()
            == "LOW"
        ),
        "landslide_probability": round(
            normalized_probability,
            4,
        ),
        "landslide_risk_level": (
            normalize_risk_level(
                risk_level
            )
            if risk_level
            else probability_to_risk(
                normalized_probability
            )
        ),
    }

    return response


# ============================================================
# SERVICE CALL
# ============================================================

def run_road_analysis(
    db: Session,
    latitude: float,
    longitude: float,
    radius_km: float,
    probability: Optional[float],
    risk_level: Optional[str],
):
    """
    Single shared implementation used by GET and POST.
    """

    try:

        result = get_vulnerable_roads(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
        )

        return enrich_roads(
            result=result,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            probability=probability,
            risk_level=risk_level,
        )

    except RuntimeError as exc:

        raise HTTPException(
            status_code=503,
            detail=str(
                exc
            ),
        ) from exc

    except HTTPException:

        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Vulnerable road analysis failed: "
                f"{str(exc)}"
            ),
        ) from exc


# ============================================================
# GET
# ============================================================

@router.get("")
def vulnerable_roads(
    latitude: float = Query(
        ...,
        ge=-90,
        le=90,
    ),

    longitude: float = Query(
        ...,
        ge=-180,
        le=180,
    ),

    radius_km: float = Query(
        5.0,
        gt=0,
        le=25,
    ),

    probability: Optional[float] = Query(
        default=None,
        ge=0,
        le=1,
    ),

    risk_level: Optional[str] = Query(
        default=None,
    ),

    db: Session = Depends(
        get_db
    ),
):
    """
    Analyze road vulnerability around a location.

    Example:

    /vulnerable-roads
        ?latitude=27.5601
        &longitude=87.9437
        &radius_km=5
        &probability=0.7172
        &risk_level=HIGH
    """

    return run_road_analysis(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        probability=probability,
        risk_level=risk_level,
    )


# ============================================================
# POST
# ============================================================

@router.post("")
def vulnerable_roads_post(
    request: VulnerableRoadRequest,
    db: Session = Depends(
        get_db
    ),
):
    """
    JSON POST version.

    This fixes the previous 422 error.

    Expected body:

    {
        "latitude": 27.5601,
        "longitude": 87.9437,
        "radius_km": 5,
        "probability": 0.7172,
        "risk_level": "HIGH"
    }
    """

    return run_road_analysis(
        db=db,
        latitude=request.latitude,
        longitude=request.longitude,
        radius_km=request.radius_km,
        probability=request.probability,
        risk_level=request.risk_level,
    )