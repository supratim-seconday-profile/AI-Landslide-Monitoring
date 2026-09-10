"""
NER LANDSLIDE EARLY WARNING SYSTEM
VULNERABLE ROAD ANALYSIS SERVICE

Purpose
-------
Determines which roads are exposed to nearby landslide-risk
prediction locations.

Flow
----
Database SVM predictions
        ↓
Filter elevated-risk predictions
        ↓
Query OpenStreetMap / Overpass
        ↓
Calculate road-to-risk distance
        ↓
Calculate exposure score
        ↓
Classify road vulnerability
        ↓
Return frontend-friendly JSON

IMPORTANT
---------
This service does NOT create a new ML prediction.

The existing SVM / Earth Engine prediction supplies:
    - landslide probability
    - landslide risk level
    - prediction location

This service converts that hazard information into
road vulnerability / exposure information.
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy.orm import Session

from ..models import RiskPrediction


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_RADIUS_KM = 5.0
MAX_RADIUS_KM = 25.0

# Only predictions above this probability are considered
# for road exposure.
MIN_RISK_PROBABILITY = 0.40

# Risk-zone radius around each landslide prediction.
RISK_ZONE_RADIUS_KM = {
    "LOW": 0.5,
    "MEDIUM": 1.0,
    "HIGH": 1.5,
    "CRITICAL": 2.0,
}

# Exposure thresholds.
HIGH_EXPOSURE = 70.0
MEDIUM_EXPOSURE = 40.0

# Overpass query timeout.
OVERPASS_QUERY_TIMEOUT = 20

# HTTP timeout.
REQUEST_TIMEOUT = 25

# Maximum number of roads returned to frontend.
MAX_ROADS = 100

# Multiple public Overpass instances.
#
# If one server gives 504/429/5xx/timeout,
# the next server is attempted.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

USER_AGENT = (
    "NER-Landslide-Early-Warning-System/1.0 "
    "(academic/SIH-project)"
)


# ============================================================
# ROAD IMPORTANCE
# ============================================================

ROAD_IMPORTANCE = {
    "motorway": 1.00,
    "trunk": 0.98,
    "primary": 0.95,
    "secondary": 0.85,
    "tertiary": 0.75,
    "unclassified": 0.55,
    "residential": 0.45,
    "service": 0.30,
    "living_street": 0.25,
    "track": 0.20,
    "path": 0.10,
    "footway": 0.05,
}

ROAD_LABELS = {
    "motorway": "Motorway",
    "trunk": "Trunk Road",
    "primary": "Primary Road",
    "secondary": "Secondary Road",
    "tertiary": "Tertiary Road",
    "unclassified": "Road",
    "residential": "Residential Road",
    "service": "Service Road",
    "living_street": "Living Street",
    "track": "Track",
    "path": "Path",
    "footway": "Footway",
}


# ============================================================
# HAVERSINE DISTANCE
# ============================================================

def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate great-circle distance between two coordinates.
    """

    earth_radius_km = 6371.0088

    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))

    delta_lat = math.radians(float(lat2) - float(lat1))
    delta_lon = math.radians(float(lon2) - float(lon1))

    a = (
        math.sin(delta_lat / 2.0) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2.0) ** 2
    )

    # Floating-point protection.
    a = max(0.0, min(1.0, a))

    c = 2.0 * math.atan2(
        math.sqrt(a),
        math.sqrt(1.0 - a),
    )

    return earth_radius_km * c


# ============================================================
# NORMALIZE PROBABILITY
# ============================================================

def normalize_probability(value: Any) -> float:
    """
    Accept probability in either form:

        0.585
        58.5

    and return:

        0.585
    """

    try:
        probability = float(value)
    except (TypeError, ValueError):
        return 0.0

    if probability > 1.0:
        probability /= 100.0

    return max(
        0.0,
        min(1.0, probability),
    )


# ============================================================
# NORMALIZE RISK LEVEL
# ============================================================

def normalize_risk_level(
    value: Optional[str],
) -> str:
    """
    Normalize risk-level strings.
    """

    if not value:
        return "LOW"

    level = str(value).strip().upper()

    if level in {
        "CRITICAL",
        "VERY HIGH",
    }:
        return "CRITICAL"

    if level == "HIGH":
        return "HIGH"

    if level == "MEDIUM":
        return "MEDIUM"

    return "LOW"


# ============================================================
# RISK ZONE RADIUS
# ============================================================

def risk_zone_radius(
    risk_level: str,
) -> float:
    """
    Return effective exposure radius for a risk level.
    """

    level = normalize_risk_level(risk_level)

    return RISK_ZONE_RADIUS_KM.get(
        level,
        0.5,
    )


# ============================================================
# RISK LEVEL WEIGHT
# ============================================================

def risk_weight(
    risk_level: str,
) -> float:
    """
    Convert landslide risk level into a weighting factor.
    """

    level = normalize_risk_level(risk_level)

    return {
        "LOW": 0.25,
        "MEDIUM": 0.50,
        "HIGH": 0.80,
        "CRITICAL": 1.00,
    }.get(
        level,
        0.25,
    )


# ============================================================
# ROAD IMPORTANCE FACTOR
# ============================================================

def road_importance_factor(
    highway_type: str,
) -> float:
    """
    Return importance factor for a road hierarchy.
    """

    highway_type = str(
        highway_type or "unclassified"
    ).strip().lower()

    return ROAD_IMPORTANCE.get(
        highway_type,
        0.40,
    )


# ============================================================
# DATABASE RISK PREDICTIONS
# ============================================================

def get_nearby_risk_predictions(
    db: Session,
    latitude: float,
    longitude: float,
    radius_km: float,
) -> List[Dict[str, Any]]:
    """
    Fetch recent SVM risk predictions around the selected point.

    The database remains the source of landslide probability.
    """

    predictions = (
        db.query(RiskPrediction)
        .order_by(
            RiskPrediction.created_at.desc()
        )
        .limit(500)
        .all()
    )

    results: List[Dict[str, Any]] = []

    seen_locations = set()

    for prediction in predictions:

        try:
            prediction_lat = float(
                prediction.latitude
            )

            prediction_lon = float(
                prediction.longitude
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        distance = haversine_km(
            latitude,
            longitude,
            prediction_lat,
            prediction_lon,
        )

        if distance > radius_km:
            continue

        raw_probability = getattr(
            prediction,
            "landslide_probability",
            None,
        )

        probability = normalize_probability(
            raw_probability
        )

        if probability < MIN_RISK_PROBABILITY:
            continue

        probability_percent = (
            probability * 100.0
        )

        risk_level = normalize_risk_level(
            getattr(
                prediction,
                "risk_level",
                None,
            )
        )

        location_key = (
            round(prediction_lat, 5),
            round(prediction_lon, 5),
        )

        if location_key in seen_locations:
            continue

        seen_locations.add(
            location_key
        )

        created_at = getattr(
            prediction,
            "created_at",
            None,
        )

        results.append(
            {
                "id": getattr(
                    prediction,
                    "id",
                    None,
                ),

                "latitude": prediction_lat,

                "longitude": prediction_lon,

                "probability": round(
                    probability_percent,
                    2,
                ),

                "probability_normalized": round(
                    probability,
                    4,
                ),

                "risk_level": risk_level,

                "distance_km": round(
                    distance,
                    3,
                ),

                "created_at": (
                    created_at.isoformat()
                    if created_at
                    else None
                ),
            }
        )

    return results


# ============================================================
# OVERPASS QUERY
# ============================================================

def build_overpass_query(
    latitude: float,
    longitude: float,
    radius_km: float,
) -> str:
    """
    Build a relatively lightweight Overpass query.

    We intentionally focus on useful road classes rather than
    requesting every possible highway object.
    """

    radius_m = int(
        radius_km * 1000.0
    )

    return f"""
[out:json][timeout:{OVERPASS_QUERY_TIMEOUT}];

(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|service)$"]
    (around:{radius_m},{latitude},{longitude});
);

out tags center geom;
""".strip()


# ============================================================
# FETCH ROADS FROM OVERPASS
# ============================================================

def fetch_roads_from_overpass(
    latitude: float,
    longitude: float,
    radius_km: float,
) -> List[Dict[str, Any]]:
    """
    Retrieve roads from OpenStreetMap.

    Multiple Overpass servers are attempted.

    This is important because a public Overpass server can
    independently return 429, 502, 503, 504 or timeout.
    """

    query = build_overpass_query(
        latitude,
        longitude,
        radius_km,
    )

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": (
            "application/x-www-form-urlencoded"
        ),
    }

    last_error: Optional[Exception] = None

    for overpass_url in OVERPASS_URLS:

        try:

            response = requests.post(
                overpass_url,
                data={
                    "data": query,
                },
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            payload = response.json()

            elements = payload.get(
                "elements",
                [],
            )

            if not isinstance(
                elements,
                list,
            ):
                continue

            roads: List[
                Dict[str, Any]
            ] = []

            for element in elements:

                if not isinstance(
                    element,
                    dict,
                ):
                    continue

                if element.get(
                    "type"
                ) != "way":
                    continue

                tags = element.get(
                    "tags",
                    {},
                )

                if not isinstance(
                    tags,
                    dict,
                ):
                    tags = {}

                highway_type = tags.get(
                    "highway"
                )

                if not highway_type:
                    continue

                geometry = element.get(
                    "geometry",
                    [],
                )

                # Some responses may only contain center.
                # Geometry is preferred because it gives a
                # better road-to-risk distance.
                if not isinstance(
                    geometry,
                    list,
                ):
                    geometry = []

                coordinates = []

                for point in geometry:

                    if not isinstance(
                        point,
                        dict,
                    ):
                        continue

                    if (
                        "lat" not in point
                        or "lon" not in point
                    ):
                        continue

                    try:
                        coordinates.append(
                            [
                                float(point["lon"]),
                                float(point["lat"]),
                            ]
                        )
                    except (
                        TypeError,
                        ValueError,
                    ):
                        continue

                center = element.get(
                    "center",
                    {},
                )

                if not isinstance(
                    center,
                    dict,
                ):
                    center = {}

                try:

                    center_lat = float(
                        center.get(
                            "lat"
                        )
                    )

                    center_lon = float(
                        center.get(
                            "lon"
                        )
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    # If center is unavailable, derive it
                    # from geometry.
                    if not coordinates:
                        continue

                    center_lon = sum(
                        point[0]
                        for point in coordinates
                    ) / len(coordinates)

                    center_lat = sum(
                        point[1]
                        for point in coordinates
                    ) / len(coordinates)

                road_name = (
                    tags.get("name")
                    or tags.get("ref")
                    or ROAD_LABELS.get(
                        highway_type,
                        "Unnamed Road",
                    )
                )

                roads.append(
                    {
                        "osm_id": element.get(
                            "id"
                        ),

                        "name": road_name,

                        "ref": tags.get(
                            "ref"
                        ),

                        "highway": highway_type,

                        "highway_type": highway_type,

                        "road_type": highway_type,

                        "road_type_label": ROAD_LABELS.get(
                            highway_type,
                            "Road",
                        ),

                        "surface": tags.get(
                            "surface"
                        ),

                        "lanes": tags.get(
                            "lanes"
                        ),

                        "latitude": center_lat,

                        "longitude": center_lon,

                        "geometry": coordinates,

                        "road_importance": road_importance_factor(
                            highway_type
                        ),
                    }
                )

            return roads

        except (
            requests.RequestException,
            ValueError,
        ) as exc:

            last_error = exc

            # Try next Overpass server.
            continue

        except Exception as exc:

            last_error = exc

            continue

    if last_error is not None:

        raise RuntimeError(
            "OpenStreetMap / Overpass road data is "
            "temporarily unavailable. "
            "All configured Overpass servers failed."
        ) from last_error

    return []


# ============================================================
# POINT-TO-ROAD DISTANCE
# ============================================================

def point_to_road_distance_km(
    latitude: float,
    longitude: float,
    coordinates: List[List[float]],
) -> float:
    """
    Calculate approximate distance from a point to a road.

    The nearest geometry point is used.

    This is intentionally dependency-light and suitable for
    dashboard-level exposure analysis.
    """

    if not coordinates:
        return float("inf")

    minimum_distance = float(
        "inf"
    )

    for coordinate in coordinates:

        if len(coordinate) < 2:
            continue

        try:

            road_lon = float(
                coordinate[0]
            )

            road_lat = float(
                coordinate[1]
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        distance = haversine_km(
            latitude,
            longitude,
            road_lat,
            road_lon,
        )

        minimum_distance = min(
            minimum_distance,
            distance,
        )

    return minimum_distance


# ============================================================
# FALLBACK ROAD CENTER DISTANCE
# ============================================================

def road_center_distance_km(
    latitude: float,
    longitude: float,
    road: Dict[str, Any],
) -> float:
    """
    Fallback distance calculation when road geometry
    is unavailable.
    """

    try:

        road_lat = float(
            road["latitude"]
        )

        road_lon = float(
            road["longitude"]
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return float("inf")

    return haversine_km(
        latitude,
        longitude,
        road_lat,
        road_lon,
    )


# ============================================================
# ROAD LENGTH
# ============================================================

def road_length_km(
    coordinates: List[List[float]],
) -> float:
    """
    Approximate length of a road geometry.
    """

    if len(coordinates) < 2:
        return 0.0

    total = 0.0

    for index in range(
        len(coordinates) - 1
    ):

        lon1, lat1 = coordinates[
            index
        ]

        lon2, lat2 = coordinates[
            index + 1
        ]

        total += haversine_km(
            lat1,
            lon1,
            lat2,
            lon2,
        )

    return total


# ============================================================
# ROAD EXPOSURE
# ============================================================

def calculate_road_exposure(
    road: Dict[str, Any],
    risk_predictions: List[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:
    """
    Calculate vulnerability of a single road.

    The highest contributing landslide-risk location
    determines the final exposure score.
    """

    coordinates = road.get(
        "geometry",
        [],
    )

    if not isinstance(
        coordinates,
        list,
    ):
        coordinates = []

    road_lat = road.get(
        "latitude"
    )

    road_lon = road.get(
        "longitude"
    )

    road_length = road_length_km(
        coordinates
    )

    nearest_distance = float(
        "inf"
    )

    exposure_score = 0.0

    contributing_risks = []

    for risk in risk_predictions:

        try:

            risk_lat = float(
                risk["latitude"]
            )

            risk_lon = float(
                risk["longitude"]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            continue

        if coordinates:

            distance = (
                point_to_road_distance_km(
                    risk_lat,
                    risk_lon,
                    coordinates,
                )
            )

        else:

            distance = (
                road_center_distance_km(
                    risk_lat,
                    risk_lon,
                    road,
                )
            )

        if distance < nearest_distance:
            nearest_distance = distance

        risk_level = normalize_risk_level(
            risk.get(
                "risk_level"
            )
        )

        zone_radius = risk_zone_radius(
            risk_level
        )

        # Ignore risks outside their effective
        # exposure radius.
        if distance > zone_radius:
            continue

        # 1 at the hazard point,
        # 0 at edge of risk zone.
        distance_factor = max(
            0.0,
            1.0 - (
                distance
                / zone_radius
            ),
        )

        probability_factor = normalize_probability(
            risk.get(
                "probability",
                0,
            )
        )

        level_factor = risk_weight(
            risk_level
        )

        road_factor = road_importance_factor(
            road.get(
                "highway",
                "unclassified",
            )
        )

        contribution = (
            distance_factor
            * probability_factor
            * level_factor
            * road_factor
            * 100.0
        )

        exposure_score = max(
            exposure_score,
            contribution,
        )

        contributing_risks.append(
            {
                "risk_id": risk.get(
                    "id"
                ),

                "risk_level": risk_level,

                "probability": round(
                    probability_factor
                    * 100.0,
                    2,
                ),

                "distance_km": round(
                    distance,
                    3,
                ),

                "zone_radius_km": round(
                    zone_radius,
                    2,
                ),
            }
        )

    # --------------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------------

    if exposure_score >= HIGH_EXPOSURE:

        vulnerability = "HIGH"

    elif exposure_score >= MEDIUM_EXPOSURE:

        vulnerability = "MEDIUM"

    elif exposure_score > 0:

        vulnerability = "LOW"

    else:

        vulnerability = "SAFE"

    # --------------------------------------------------------
    # Frontend-compatible output
    # --------------------------------------------------------

    return {
        "osm_id": road.get(
            "osm_id"
        ),

        "road_name": road.get(
            "name",
            "Unnamed Road",
        ),

        "name": road.get(
            "name",
            "Unnamed Road",
        ),

        "road_ref": road.get(
            "ref"
        ),

        "ref": road.get(
            "ref"
        ),

        "highway_type": road.get(
            "highway"
        ),

        "road_type": road.get(
            "road_type",
            road.get(
                "highway"
            ),
        ),

        "road_type_label": road.get(
            "road_type_label",
            "Road",
        ),

        "surface": road.get(
            "surface"
        ),

        "lanes": road.get(
            "lanes"
        ),

        "latitude": road_lat,

        "longitude": road_lon,

        "road_length_km": round(
            road_length,
            3,
        ),

        "nearest_risk_distance_km": (
            round(
                nearest_distance,
                3,
            )
            if nearest_distance
            != float("inf")
            else None
        ),

        "exposure_percent": round(
            exposure_score,
            2,
        ),

        "vulnerability_score": round(
            exposure_score,
            2,
        ),

        "road_vulnerability_score": round(
            exposure_score,
            2,
        ),

        "risk_score": round(
            exposure_score,
            2,
        ),

        "risk_level": vulnerability,

        "vulnerability_level": vulnerability,

        "risk": vulnerability,

        "road_risk": vulnerability,

        "contributing_risks": (
            contributing_risks
        ),

        "geometry": coordinates,
    }


# ============================================================
# REMOVE DUPLICATE ROADS
# ============================================================

def deduplicate_roads(
    roads: List[
        Dict[str, Any]
    ],
) -> List[
    Dict[str, Any]
]:
    """
    Remove duplicate OSM ways.
    """

    seen = set()

    unique_roads = []

    for road in roads:

        osm_id = road.get(
            "osm_id"
        )

        if osm_id is not None:

            if osm_id in seen:
                continue

            seen.add(
                osm_id
            )

        unique_roads.append(
            road
        )

    return unique_roads


# ============================================================
# MAIN ANALYSIS
# ============================================================

def get_vulnerable_roads(
    db: Session,
    latitude: float,
    longitude: float,
    radius_km: float = DEFAULT_RADIUS_KM,
) -> Dict[str, Any]:
    """
    Complete vulnerable-road analysis.

    Parameters
    ----------
    db:
        SQLAlchemy database session.

    latitude:
        Selected location latitude.

    longitude:
        Selected location longitude.

    radius_km:
        Search radius.

    Returns
    -------
    dict
        Frontend-friendly vulnerable-road response.
    """

    start_time = time.time()

    # --------------------------------------------------------
    # Validate radius
    # --------------------------------------------------------

    try:

        radius_km = float(
            radius_km
        )

    except (
        TypeError,
        ValueError,
    ):

        radius_km = DEFAULT_RADIUS_KM

    radius_km = max(
        0.1,
        min(
            MAX_RADIUS_KM,
            radius_km,
        ),
    )

    # --------------------------------------------------------
    # Validate coordinates
    # --------------------------------------------------------

    latitude = float(
        latitude
    )

    longitude = float(
        longitude
    )

    if not (
        -90.0
        <= latitude
        <= 90.0
    ):
        raise ValueError(
            "Invalid latitude."
        )

    if not (
        -180.0
        <= longitude
        <= 180.0
    ):
        raise ValueError(
            "Invalid longitude."
        )

    # --------------------------------------------------------
    # 1. Get nearby SVM risk predictions
    # --------------------------------------------------------

    risk_predictions = (
        get_nearby_risk_predictions(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
        )
    )

    # --------------------------------------------------------
    # 2. No elevated-risk locations
    # --------------------------------------------------------

    if not risk_predictions:

        return {
            "success": True,

            "latitude": latitude,

            "longitude": longitude,

            "radius_km": radius_km,

            "risk_locations": [],

            "total_roads_analyzed": 0,

            "vulnerable_roads_count": 0,

            "summary": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "safe": 0,
            },

            "roads": [],

            "source": (
                "OpenStreetMap / Overpass"
            ),

            "message": (
                "No elevated landslide-risk "
                "locations were found within "
                "the selected radius."
            ),

            "analysis_time_seconds": round(
                time.time()
                - start_time,
                2,
            ),
        }

    # --------------------------------------------------------
    # 3. Retrieve roads
    # --------------------------------------------------------

    roads = fetch_roads_from_overpass(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
    )

    roads = deduplicate_roads(
        roads
    )

    # --------------------------------------------------------
    # 4. Analyze every road
    # --------------------------------------------------------

    analyzed_roads = []

    for road in roads:

        try:

            result = (
                calculate_road_exposure(
                    road=road,
                    risk_predictions=(
                        risk_predictions
                    ),
                )
            )

        except Exception:
            continue

        # Only return exposed roads.
        if result[
            "risk_level"
        ] != "SAFE":

            analyzed_roads.append(
                result
            )

    # --------------------------------------------------------
    # 5. Sort highest exposure first
    # --------------------------------------------------------

    analyzed_roads.sort(
        key=lambda item: float(
            item.get(
                "exposure_percent",
                0,
            )
            or 0
        ),
        reverse=True,
    )

    analyzed_roads = analyzed_roads[
        :MAX_ROADS
    ]

    # --------------------------------------------------------
    # 6. Summary
    # --------------------------------------------------------

    summary = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "safe": 0,
    }

    for road in analyzed_roads:

        level = str(
            road.get(
                "risk_level",
                "SAFE",
            )
        ).lower()

        if level in summary:

            summary[level] += 1

    # --------------------------------------------------------
    # 7. Final response
    # --------------------------------------------------------

    elapsed = (
        time.time()
        - start_time
    )

    return {
        "success": True,

        "latitude": latitude,

        "longitude": longitude,

        "radius_km": radius_km,

        "risk_locations": (
            risk_predictions
        ),

        "total_roads_analyzed": len(
            roads
        ),

        "vulnerable_roads_count": len(
            analyzed_roads
        ),

        "summary": summary,

        "roads": analyzed_roads,

        "source": (
            "OpenStreetMap / Overpass"
        ),

        "message": (
            f"{len(analyzed_roads)} "
            "potentially vulnerable "
            "road segments identified."
            if analyzed_roads
            else (
                "No vulnerable road "
                "segments identified "
                "within the selected radius."
            )
        ),

        "analysis_time_seconds": round(
            elapsed,
            2,
        ),
    }


# ============================================================
# END OF SERVICE
# ============================================================