import requests
from datetime import datetime, timezone
from typing import Any


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _safe_value(values, index, default=0.0):
    try:
        value = values[index]

        if value is None:
            return default

        return float(value)

    except (IndexError, TypeError, ValueError):
        return default


def _sum_last_hours(values, hours: int):
    """
    Sum the latest `hours` hourly precipitation values.
    """

    if not values:
        return 0.0

    usable = values[-hours:]

    total = 0.0

    for value in usable:
        if value is not None:
            try:
                total += float(value)
            except (TypeError, ValueError):
                pass

    return round(total, 2)


def _get_rainfall_alert(
    rainfall_24h: float,
    rainfall_72h: float
):
    """
    IMPORTANT:
    This is a rule-based rainfall warning.
    It is NOT an ML prediction.
    """

    if rainfall_24h >= 100 or rainfall_72h >= 200:

        return {
            "level": "HIGH",
            "message": (
                "Heavy rainfall conditions detected. "
                "Landslide susceptibility may increase."
            )
        }

    if rainfall_24h >= 50 or rainfall_72h >= 100:

        return {
            "level": "MEDIUM",
            "message": (
                "Elevated rainfall detected. "
                "Monitor landslide-prone areas closely."
            )
        }

    return {
        "level": "LOW",
        "message": (
            "No significant rainfall-based warning "
            "detected at this location."
        )
    }


def get_weather(
    latitude: float,
    longitude: float
) -> dict[str, Any]:

    params = {

        "latitude": latitude,

        "longitude": longitude,

        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "rain,"
            "showers,"
            "cloud_cover,"
            "wind_speed_10m,"
            "wind_direction_10m,"
            "wind_gusts_10m,"
            "weather_code"
        ),

        "hourly": (
            "precipitation,"
            "rain,"
            "showers,"
            "temperature_2m,"
            "relative_humidity_2m,"
            "wind_speed_10m"
        ),

        "past_hours": 72,

        "forecast_hours": 24,

        "timezone": "Asia/Kolkata",

        "temperature_unit": "celsius",

        "wind_speed_unit": "kmh",

        "precipitation_unit": "mm",

        "cell_selection": "land"
    }

    try:

        response = requests.get(
            OPEN_METEO_URL,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException as exc:

        raise RuntimeError(
            f"Weather service unavailable: {exc}"
        ) from exc

    except ValueError as exc:

        raise RuntimeError(
            "Invalid response received from weather service."
        ) from exc


    current = data.get("current", {})

    hourly = data.get("hourly", {})


    precipitation = hourly.get(
        "precipitation",
        []
    )


    rain = hourly.get(
        "rain",
        []
    )


    showers = hourly.get(
        "showers",
        []
    )


    rainfall_24h = _sum_last_hours(
        precipitation,
        24
    )


    rainfall_72h = _sum_last_hours(
        precipitation,
        72
    )


    rain_24h = _sum_last_hours(
        rain,
        24
    )


    showers_24h = _sum_last_hours(
        showers,
        24
    )


    alert = _get_rainfall_alert(
        rainfall_24h,
        rainfall_72h
    )


    current_precipitation = float(
        current.get(
            "precipitation",
            0
        ) or 0
    )


    current_rain = float(
        current.get(
            "rain",
            0
        ) or 0
    )


    result = {

        "latitude": latitude,

        "longitude": longitude,

        "timezone": data.get(
            "timezone",
            "Asia/Kolkata"
        ),

        "weather_source": "Open-Meteo",

        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "current": {

            "temperature_c": current.get(
                "temperature_2m"
            ),

            "relative_humidity_percent": current.get(
                "relative_humidity_2m"
            ),

            "precipitation_mm": current_precipitation,

            "rain_mm": current_rain,

            "showers_mm": current.get(
                "showers"
            ),

            "cloud_cover_percent": current.get(
                "cloud_cover"
            ),

            "wind_speed_kmh": current.get(
                "wind_speed_10m"
            ),

            "wind_direction_deg": current.get(
                "wind_direction_10m"
            ),

            "wind_gusts_kmh": current.get(
                "wind_gusts_10m"
            ),

            "weather_code": current.get(
                "weather_code"
            )
        },

        "rainfall": {

            "last_24h_mm": rainfall_24h,

            "last_72h_mm": rainfall_72h,

            "rain_last_24h_mm": rain_24h,

            "showers_last_24h_mm": showers_24h
        },

        "rainfall_alert": alert
    }


    return result