"""
Vulnerable Road Analysis Service

Determines road exposure to nearby landslide-risk locations.

Flow:
    Risk predictions
        ↓
    Find elevated-risk predictions
        ↓
    Query OpenStreetMap / Overpass
        ↓
    Calculate road-to-risk distance
        ↓
    Calculate exposure score
        ↓
    Classify road vulnerability
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

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

DEFAULT_RADIUS_KM = 5.0

# Risk-zone radius used for road exposure analysis.
RISK_ZONE_RADIUS_KM = {
    "LOW": 0.5,
    "MEDIUM": 1.0,
    "HIGH": 1.5,
    "CRITICAL": 2.0,
}

# Minimum probability considered for road exposure.
MIN_RISK_PROBABILITY = 0.40

# Road vulnerability thresholds.
HIGH_EXPOSURE = 70.0
MEDIUM_EXPOSURE = 40.0

# Overpass timeout.
OVERPASS_TIMEOUT = 45


# ============================================================
# DISTANCE UTILITIES
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

    earth_radius_km = 6371.0

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )

    return earth_radius_km * c


# ============================================================
# RISK HELPERS
# ============================================================

def normalize_risk_level(value: Optional[str]) -> str:
    """
    Normalize risk-level strings.
    """

    if not value:
        return "LOW"

    value = str(value).strip().upper()

    if value in {"CRITICAL", "VERY HIGH"}:
        return "CRITICAL"

    if value == "HIGH":
        return "HIGH"

    if value == "MEDIUM":
        return "MEDIUM"

    return "LOW"


def risk_zone_radius(risk_level: str) -> float:
    """
    Return the effective landslide-risk-zone radius.
    """

    return RISK_ZONE_RADIUS_KM.get(
        normalize_risk_level(risk_level),
        0.5,
    )


def risk_weight(risk_level: str) -> float:
    """
    Convert risk level into a weighting factor.
    """

    level = normalize_risk_level(risk_level)

    return {
        "LOW": 0.25,
        "MEDIUM": 0.50,
        "HIGH": 0.80,
        "CRITICAL": 1.00,
    }.get(level, 0.25)


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
    Fetch recent risk predictions around a selected location.

    Uses a broad database query followed by haversine filtering.
    """

    predictions = (
        db.query(RiskPrediction)
        .order_by(RiskPrediction.created_at.desc())
        .limit(500)
        .all()
    )

    results: List[Dict[str, Any]] = []

    seen_locations = set()

    for prediction in predictions:

        try:
            p_lat = float(prediction.latitude)
            p_lon = float(prediction.longitude)
        except (TypeError, ValueError):
            continue

        distance = haversine_km(
            latitude,
            longitude,
            p_lat,
            p_lon,
        )

        if distance > radius_km:
            continue

        probability = getattr(
            prediction,
            "landslide_probability",
            None,
        )

        if probability is None:
            continue

        try:
            probability = float(probability)
        except (TypeError, ValueError):
            continue

        # Support either 0-1 or 0-100 storage.
        if probability <= 1:
            probability_percent = probability * 100.0
        else:
            probability_percent = probability

        if probability_percent < MIN_RISK_PROBABILITY * 100:
            continue

        risk_level = normalize_risk_level(
            getattr(
                prediction,
                "risk_level",
                None,
            )
        )

        location_key = (
            round(p_lat, 5),
            round(p_lon, 5),
        )

        if location_key in seen_locations:
            continue

        seen_locations.add(location_key)

        results.append(
            {
                "id": getattr(prediction, "id", None),
                "latitude": p_lat,
                "longitude": p_lon,
                "probability": probability_percent,
                "risk_level": risk_level,
                "distance_km": round(distance, 3),
                "created_at": (
                    prediction.created_at.isoformat()
                    if getattr(prediction, "created_at", None)
                    else None
                ),
            }
        )

    return results


# ============================================================
# OPENSTREETMAP / OVERPASS
# ============================================================

def build_overpass_query(
    latitude: float,
    longitude: float,
    radius_m: float,
) -> str:
    """
    Build an Overpass query for roads around a location.

    Includes major highways and local roads.
    """

    return f"""
[out:json][timeout:{OVERPASS_TIMEOUT}];

(
  way["highway"]
    (around:{radius_m},{latitude},{longitude});
);

out tags center geom;
"""


def fetch_roads_from_overpass(
    latitude: float,
    longitude: float,
    radius_km: float,
) -> List[Dict[str, Any]]:
    """
    Retrieve road geometries from OpenStreetMap through Overpass.
    """

    radius_m = int(radius_km * 1000)

    query = build_overpass_query(
        latitude,
        longitude,
        radius_m,
    )

    headers = {
        "User-Agent": (
            "NER-Landslide-Early-Warning-System/1.0 "
            "(academic/SIH project)"
        )
    }

    try:
        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=headers,
            timeout=OVERPASS_TIMEOUT,
        )

        response.raise_for_status()

        payload = response.json()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Unable to retrieve OpenStreetMap roads: {exc}"
        ) from exc

    except ValueError as exc:
        raise RuntimeError(
            "OpenStreetMap returned invalid JSON."
        ) from exc

    elements = payload.get("elements", [])

    roads: List[Dict[str, Any]] = []

    for element in elements:

        if element.get("type") != "way":
            continue

        tags = element.get("tags", {})

        highway_type = tags.get("highway")

        if not highway_type:
            continue

        geometry = element.get("geometry", [])

        if len(geometry) < 2:
            continue

        coordinates = []

        for point in geometry:

            if (
                "lat" not in point
                or "lon" not in point
            ):
                continue

            coordinates.append(
                [
                    float(point["lon"]),
                    float(point["lat"]),
                ]
            )

        if len(coordinates) < 2:
            continue

        road_name = (
            tags.get("name")
            or tags.get("ref")
            or "Unnamed Road"
        )

        roads.append(
            {
                "osm_id": element.get("id"),
                "name": road_name,
                "ref": tags.get("ref"),
                "highway": highway_type,
                "surface": tags.get("surface"),
                "lanes": tags.get("lanes"),
                "geometry": coordinates,
            }
        )

    return roads


# ============================================================
# ROAD GEOMETRY DISTANCE
# ============================================================

def point_to_road_distance_km(
    latitude: float,
    longitude: float,
    coordinates: List[List[float]],
) -> float:
    """
    Approximate distance from a point to a road.

    Each road geometry point is checked.

    This is deliberately dependency-light and works well
    for the dashboard-level exposure calculation.
    """

    minimum_distance = float("inf")

    for coordinate in coordinates:

        if len(coordinate) < 2:
            continue

        road_lon = float(coordinate[0])
        road_lat = float(coordinate[1])

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


def road_length_km(
    coordinates: List[List[float]],
) -> float:
    """
    Approximate road segment length.
    """

    total = 0.0

    for index in range(len(coordinates) - 1):

        lon1, lat1 = coordinates[index]
        lon2, lat2 = coordinates[index + 1]

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
    risk_predictions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Calculate vulnerability of one road segment.
    """

    coordinates = road["geometry"]

    road_length = road_length_km(
        coordinates
    )

    nearest_distance = float("inf")

    exposure_score = 0.0

    contributing_risks = []

    for risk in risk_predictions:

        risk_lat = risk["latitude"]
        risk_lon = risk["longitude"]

        distance = point_to_road_distance_km(
            risk_lat,
            risk_lon,
            coordinates,
        )

        if distance < nearest_distance:
            nearest_distance = distance

        zone_radius = risk_zone_radius(
            risk["risk_level"]
        )

        if distance > zone_radius:
            continue

        # Distance factor:
        # closer road = greater exposure.
        distance_factor = max(
            0.0,
            1.0 - (distance / zone_radius),
        )

        probability_factor = min(
            risk["probability"] / 100.0,
            1.0,
        )

        level_factor = risk_weight(
            risk["risk_level"]
        )

        contribution = (
            distance_factor
            * probability_factor
            * level_factor
            * 100.0
        )

        exposure_score = max(
            exposure_score,
            contribution,
        )

        contributing_risks.append(
            {
                "risk_level": risk["risk_level"],
                "probability": round(
                    risk["probability"],
                    2,
                ),
                "distance_km": round(
                    distance,
                    3,
                ),
            }
        )

    if exposure_score >= HIGH_EXPOSURE:
        vulnerability = "HIGH"

    elif exposure_score >= MEDIUM_EXPOSURE:
        vulnerability = "MEDIUM"

    elif exposure_score > 0:
        vulnerability = "LOW"

    else:
        vulnerability = "SAFE"

    return {
        "road_name": road["name"],
        "road_ref": road.get("ref"),
        "highway_type": road.get("highway"),
        "surface": road.get("surface"),
        "osm_id": road.get("osm_id"),
        "road_length_km": round(
            road_length,
            3,
        ),
        "nearest_risk_distance_km": (
            round(nearest_distance, 3)
            if nearest_distance != float("inf")
            else None
        ),
        "exposure_percent": round(
            exposure_score,
            2,
        ),
        "risk_level": vulnerability,
        "contributing_risks": contributing_risks,
        "geometry": coordinates,
    }


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
    """

    start_time = time.time()

    if radius_km <= 0:
        radius_km = DEFAULT_RADIUS_KM

    if radius_km > 25:
        radius_km = 25

    # --------------------------------------------------------
    # 1. Get nearby risk predictions
    # --------------------------------------------------------

    risk_predictions = get_nearby_risk_predictions(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
    )

    # --------------------------------------------------------
    # 2. If there are no elevated risk locations
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
            "message": (
                "No elevated landslide-risk locations "
                "were found within the selected radius."
            ),
            "analysis_time_seconds": round(
                time.time() - start_time,
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

    # --------------------------------------------------------
    # 4. Calculate road vulnerability
    # --------------------------------------------------------

    analyzed_roads: List[Dict[str, Any]] = []

    for road in roads:

        result = calculate_road_exposure(
            road=road,
            risk_predictions=risk_predictions,
        )

        # Only return roads with some exposure.
        if result["risk_level"] != "SAFE":

            analyzed_roads.append(
                result
            )

    # --------------------------------------------------------
    # 5. Sort highest exposure first
    # --------------------------------------------------------

    analyzed_roads.sort(
        key=lambda item: item[
            "exposure_percent"
        ],
        reverse=True,
    )

    # Limit dashboard response.
    analyzed_roads = analyzed_roads[:100]

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

        level = road["risk_level"].lower()

        if level in summary:
            summary[level] += 1

    elapsed = time.time() - start_time

    return {
        "success": True,
        "latitude": latitude,
        "longitude": longitude,
        "radius_km": radius_km,
        "risk_locations": risk_predictions,
        "total_roads_analyzed": len(roads),
        "vulnerable_roads_count": len(
            analyzed_roads
        ),
        "summary": summary,
        "roads": analyzed_roads,
        "message": (
            f"{len(analyzed_roads)} potentially "
            "vulnerable road segments identified."
            if analyzed_roads
            else (
                "No vulnerable road segments "
                "identified within the selected radius."
            )
        ),
        "analysis_time_seconds": round(
            elapsed,
            2,
        ),
    }