# ============================================================
# SIH LANDSLIDE EARLY WARNING SYSTEM
# ALERT + SMS + WEB PUSH ENGINE
# ============================================================

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from ..database import engine


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger("sih.alerts")


# ============================================================
# CONFIGURATION
# ============================================================

ALERT_MIN_LEVEL = os.getenv(
    "ALERT_MIN_LEVEL",
    "HIGH",
).upper()

ALERT_DEDUP_MINUTES = int(
    os.getenv(
        "ALERT_DEDUP_MINUTES",
        "30",
    )
)


# ============================================================
# RISK SEVERITY
# ============================================================

RISK_SEVERITY = {
    "NONE": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "MODERATE": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


def risk_severity(level: str) -> int:
    return RISK_SEVERITY.get(
        str(level or "").upper(),
        0,
    )


def should_alert(level: str) -> bool:
    return (
        risk_severity(level)
        >= risk_severity(ALERT_MIN_LEVEL)
    )


# ============================================================
# DATABASE INITIALISATION
# ============================================================

def init_alert_tables() -> None:
    """
    Creates only alert-specific tables.

    Existing project tables are not modified.
    """

    statements = [

        # ----------------------------------------------------
        # Alert subscribers
        # ----------------------------------------------------

        """
        CREATE TABLE IF NOT EXISTS alert_subscribers (
            id BIGSERIAL PRIMARY KEY,

            name VARCHAR(120),

            phone VARCHAR(32),

            latitude DOUBLE PRECISION NOT NULL,

            longitude DOUBLE PRECISION NOT NULL,

            radius_km DOUBLE PRECISION
                NOT NULL DEFAULT 5,

            sms_enabled BOOLEAN
                NOT NULL DEFAULT TRUE,

            push_enabled BOOLEAN
                NOT NULL DEFAULT TRUE,

            active BOOLEAN
                NOT NULL DEFAULT TRUE,

            created_at TIMESTAMPTZ
                NOT NULL DEFAULT NOW(),

            updated_at TIMESTAMPTZ
                NOT NULL DEFAULT NOW()
        )
        """,

        # ----------------------------------------------------
        # Push subscriptions
        # ----------------------------------------------------

        """
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id BIGSERIAL PRIMARY KEY,

            subscriber_id BIGINT NULL,

            endpoint TEXT NOT NULL UNIQUE,

            subscription_json JSONB NOT NULL,

            latitude DOUBLE PRECISION,

            longitude DOUBLE PRECISION,

            active BOOLEAN
                NOT NULL DEFAULT TRUE,

            created_at TIMESTAMPTZ
                NOT NULL DEFAULT NOW(),

            updated_at TIMESTAMPTZ
                NOT NULL DEFAULT NOW()
        )
        """,

        # ----------------------------------------------------
        # Alert event history
        # ----------------------------------------------------

        """
        CREATE TABLE IF NOT EXISTS alert_events (
            id BIGSERIAL PRIMARY KEY,

            fingerprint VARCHAR(300)
                NOT NULL UNIQUE,

            alert_type VARCHAR(40)
                NOT NULL,

            level VARCHAR(20)
                NOT NULL,

            title VARCHAR(255)
                NOT NULL,

            message TEXT
                NOT NULL,

            latitude DOUBLE PRECISION
                NOT NULL,

            longitude DOUBLE PRECISION
                NOT NULL,

            probability DOUBLE PRECISION,

            road_name VARCHAR(255),

            road_score DOUBLE PRECISION,

            prediction_id BIGINT,

            created_at TIMESTAMPTZ
                NOT NULL DEFAULT NOW()
        )
        """,

        # ----------------------------------------------------
        # Delivery logs
        # ----------------------------------------------------

        """
        CREATE TABLE IF NOT EXISTS alert_deliveries (
            id BIGSERIAL PRIMARY KEY,

            alert_id BIGINT NOT NULL,

            channel VARCHAR(30)
                NOT NULL,

            destination TEXT,

            status VARCHAR(30)
                NOT NULL,

            provider_message_id TEXT,

            error_message TEXT,

            created_at TIMESTAMPTZ
                NOT NULL DEFAULT NOW()
        )
        """,

        # ----------------------------------------------------
        # Indexes
        # ----------------------------------------------------

        """
        CREATE INDEX IF NOT EXISTS
        idx_alert_subscribers_location
        ON alert_subscribers(latitude, longitude)
        """,

        """
        CREATE INDEX IF NOT EXISTS
        idx_alert_events_created
        ON alert_events(created_at DESC)
        """,

        """
        CREATE INDEX IF NOT EXISTS
        idx_push_subscriptions_active
        ON push_subscriptions(active)
        """,
    ]

    with engine.begin() as connection:

        for statement in statements:
            connection.execute(
                text(statement)
            )

    logger.info(
        "Alert tables initialised successfully."
    )


# ============================================================
# TIME
# ============================================================

def utc_now():
    return datetime.now(timezone.utc)


# ============================================================
# FINGERPRINT
# ============================================================

def build_fingerprint(
    alert_type: str,
    level: str,
    latitude: float,
    longitude: float,
    probability: float | None = None,
    road_name: str | None = None,
) -> str:

    lat_bucket = round(
        float(latitude),
        3,
    )

    lon_bucket = round(
        float(longitude),
        3,
    )

    probability_bucket = (
        round(
            float(probability) * 100
        )
        if probability is not None
        else ""
    )

    return "|".join(
        [
            str(alert_type).upper(),
            str(level).upper(),
            str(lat_bucket),
            str(lon_bucket),
            str(probability_bucket),
            str(road_name or ""),
        ]
    )


# ============================================================
# SMS
# ============================================================

def send_sms(
    phone: str,
    message: str,
) -> dict[str, Any]:
    """
    Sends SMS through Twilio.

    If Twilio is not configured, the system records
    SKIPPED rather than crashing the prediction system.
    """

    sid = os.getenv(
        "TWILIO_ACCOUNT_SID"
    )

    token = os.getenv(
        "TWILIO_AUTH_TOKEN"
    )

    from_number = os.getenv(
        "TWILIO_FROM_NUMBER"
    )

    if not all(
        [
            sid,
            token,
            from_number,
        ]
    ):

        return {
            "status": "SKIPPED",
            "message": (
                "Twilio is not configured."
            ),
        }

    try:

        from twilio.rest import Client

        client = Client(
            sid,
            token,
        )

        result = client.messages.create(
            body=message,
            from_=from_number,
            to=phone,
        )

        return {
            "status": "SENT",
            "message_id": result.sid,
        }

    except Exception as exc:

        logger.exception(
            "SMS delivery failed."
        )

        return {
            "status": "FAILED",
            "error": str(exc),
        }


# ============================================================
# WEB PUSH
# ============================================================

def send_web_push(
    subscription: dict,
    title: str,
    message: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Sends Web Push using VAPID.
    """

    private_key = os.getenv(
        "VAPID_PRIVATE_KEY"
    )

    claim_email = os.getenv(
        "VAPID_CLAIM_EMAIL"
    )

    if not private_key:

        return {
            "status": "SKIPPED",
            "message": (
                "VAPID_PRIVATE_KEY "
                "not configured."
            ),
        }

    try:

        from pywebpush import webpush

        payload = json.dumps(
            {
                "title": title,
                "body": message,
                "data": data,
            }
        )

        vapid_claims = {
            "sub":
                claim_email
                or
                "mailto:admin@example.com"
        }

        webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=private_key,
            vapid_claims=vapid_claims,
        )

        return {
            "status": "SENT",
        }

    except Exception as exc:

        logger.exception(
            "Web push failed."
        )

        return {
            "status": "FAILED",
            "error": str(exc),
        }


# ============================================================
# NEARBY SMS RECIPIENTS
# ============================================================

def get_nearby_sms_recipients(
    latitude: float,
    longitude: float,
):

    query = text(
        """
        SELECT
            id,
            name,
            phone,
            latitude,
            longitude,
            radius_km

        FROM alert_subscribers

        WHERE active = TRUE

        AND sms_enabled = TRUE

        AND phone IS NOT NULL

        AND ST_DWithin(

            ST_SetSRID(
                ST_MakePoint(
                    longitude,
                    latitude
                ),
                4326
            )::geography,

            ST_SetSRID(
                ST_MakePoint(
                    :longitude,
                    :latitude
                ),
                4326
            )::geography,

            radius_km * 1000
        )
        """
    )

    with engine.begin() as connection:

        result = connection.execute(
            query,
            {
                "latitude": latitude,
                "longitude": longitude,
            },
        )

        return result.mappings().all()


# ============================================================
# NEARBY PUSH SUBSCRIPTIONS
# ============================================================

def get_push_subscriptions(
    latitude: float,
    longitude: float,
):

    query = text(
        """
        SELECT
            ps.id,
            ps.subscriber_id,
            ps.subscription_json

        FROM push_subscriptions ps

        LEFT JOIN alert_subscribers s
            ON s.id = ps.subscriber_id

        WHERE ps.active = TRUE

        AND (
            s.id IS NULL
            OR s.active = TRUE
        )

        AND (
            s.id IS NULL
            OR s.push_enabled = TRUE
        )

        AND (
            s.id IS NULL

            OR ST_DWithin(

                ST_SetSRID(
                    ST_MakePoint(
                        s.longitude,
                        s.latitude
                    ),
                    4326
                )::geography,

                ST_SetSRID(
                    ST_MakePoint(
                        :longitude,
                        :latitude
                    ),
                    4326
                )::geography,

                s.radius_km * 1000
            )
        )
        """
    )

    with engine.begin() as connection:

        result = connection.execute(
            query,
            {
                "latitude": latitude,
                "longitude": longitude,
            },
        )

        return result.mappings().all()


# ============================================================
# SMS MESSAGE
# ============================================================

def build_sms_message(
    title: str,
    message: str,
    latitude: float,
    longitude: float,
    probability: float | None,
    road_name: str | None = None,
) -> str:

    if probability is not None:

        probability_text = (
            f"{float(probability) * 100:.1f}%"
        )

    else:

        probability_text = "N/A"


    if road_name:

        road_text = (
            f" Road: {road_name}."
        )

    else:

        road_text = ""


    return (
        "NER LANDSLIDE ALERT: "
        f"{title}. "
        f"{message} "
        f"Probability: "
        f"{probability_text}."
        f"{road_text} "
        "Location: "
        f"{latitude:.5f}, "
        f"{longitude:.5f}. "
        "Please follow local "
        "disaster-management instructions."
    )


# ============================================================
# SAVE DELIVERY
# ============================================================

def save_delivery(
    alert_id: int,
    channel: str,
    destination: str | None,
    status: str,
    provider_message_id: str | None = None,
    error_message: str | None = None,
):

    query = text(
        """
        INSERT INTO alert_deliveries (
            alert_id,
            channel,
            destination,
            status,
            provider_message_id,
            error_message
        )

        VALUES (
            :alert_id,
            :channel,
            :destination,
            :status,
            :provider_message_id,
            :error_message
        )
        """
    )

    with engine.begin() as connection:

        connection.execute(
            query,
            {
                "alert_id":
                    alert_id,

                "channel":
                    channel,

                "destination":
                    destination,

                "status":
                    status,

                "provider_message_id":
                    provider_message_id,

                "error_message":
                    error_message,
            },
        )


# ============================================================
# DISPATCH ALERT
# ============================================================

def dispatch_alert(
    *,
    alert_type: str,
    level: str,
    title: str,
    message: str,
    latitude: float,
    longitude: float,
    probability: float | None = None,
    prediction_id: int | None = None,
    road_name: str | None = None,
    road_score: float | None = None,
) -> dict[str, Any]:

    level = str(
        level or ""
    ).upper()


    # --------------------------------------------------------
    # Threshold
    # --------------------------------------------------------

    if not should_alert(level):

        return {
            "created": False,
            "reason":
                "Below alert threshold",
            "level": level,
        }


    # --------------------------------------------------------
    # Fingerprint
    # --------------------------------------------------------

    fingerprint = build_fingerprint(

        alert_type=alert_type,

        level=level,

        latitude=latitude,

        longitude=longitude,

        probability=probability,

        road_name=road_name,
    )


    # --------------------------------------------------------
    # Deduplication
    # --------------------------------------------------------

    duplicate_query = text(
        """
        SELECT id

        FROM alert_events

        WHERE fingerprint = :fingerprint

        AND created_at >
            NOW() -
            (:minutes * INTERVAL '1 minute')

        LIMIT 1
        """
    )

    with engine.begin() as connection:

        duplicate = connection.execute(

            duplicate_query,

            {
                "fingerprint":
                    fingerprint,

                "minutes":
                    ALERT_DEDUP_MINUTES,
            },

        ).first()


    if duplicate:

        return {
            "created": False,

            "reason":
                "Duplicate alert",

            "alert_id":
                duplicate[0],

            "fingerprint":
                fingerprint,
        }


    # --------------------------------------------------------
    # Create alert event
    # --------------------------------------------------------

    insert_query = text(
        """
        INSERT INTO alert_events (
            fingerprint,
            alert_type,
            level,
            title,
            message,
            latitude,
            longitude,
            probability,
            road_name,
            road_score,
            prediction_id
        )

        VALUES (
            :fingerprint,
            :alert_type,
            :level,
            :title,
            :message,
            :latitude,
            :longitude,
            :probability,
            :road_name,
            :road_score,
            :prediction_id
        )

        RETURNING id
        """
    )

    with engine.begin() as connection:

        alert_id = connection.execute(

            insert_query,

            {
                "fingerprint":
                    fingerprint,

                "alert_type":
                    alert_type,

                "level":
                    level,

                "title":
                    title,

                "message":
                    message,

                "latitude":
                    latitude,

                "longitude":
                    longitude,

                "probability":
                    probability,

                "road_name":
                    road_name,

                "road_score":
                    road_score,

                "prediction_id":
                    prediction_id,
            },

        ).scalar_one()


    # --------------------------------------------------------
    # Push data
    # --------------------------------------------------------

    push_data = {

        "alert_id":
            alert_id,

        "type":
            alert_type,

        "level":
            level,

        "latitude":
            latitude,

        "longitude":
            longitude,

        "probability":
            probability,

        "road_name":
            road_name,
    }


    # --------------------------------------------------------
    # SMS MESSAGE
    # --------------------------------------------------------

    sms_message = build_sms_message(

        title=title,

        message=message,

        latitude=latitude,

        longitude=longitude,

        probability=probability,

        road_name=road_name,
    )


    sms_results = []

    push_results = []


    # ========================================================
    # SMS DISPATCH
    # ========================================================

    try:

        recipients = get_nearby_sms_recipients(

            latitude,

            longitude,
        )


        for recipient in recipients:

            result = send_sms(

                recipient["phone"],

                sms_message,
            )


            sms_results.append({

                "phone":
                    recipient["phone"],

                **result,
            })


            save_delivery(

                alert_id=
                    alert_id,

                channel=
                    "SMS",

                destination=
                    recipient["phone"],

                status=
                    result.get(
                        "status",
                        "UNKNOWN",
                    ),

                provider_message_id=
                    result.get(
                        "message_id"
                    ),

                error_message=
                    result.get(
                        "error"
                    ),
            )


    except Exception as exc:

        logger.exception(
            "SMS dispatch failed."
        )

        sms_results.append({

            "status":
                "FAILED",

            "error":
                str(exc),
        })


    # ========================================================
    # PUSH DISPATCH
    # ========================================================

    try:

        subscriptions = get_push_subscriptions(

            latitude,

            longitude,
        )


        for item in subscriptions:

            subscription = item[
                "subscription_json"
            ]


            # PostgreSQL JSONB may already
            # arrive as a Python dictionary.

            if isinstance(
                subscription,
                str,
            ):

                subscription = json.loads(
                    subscription
                )


            result = send_web_push(

                subscription=

                    subscription,

                title=

                    title,

                message=

                    message,

                data=

                    push_data,
            )


            push_results.append({

                "subscription_id":
                    item["id"],

                **result,
            })


            save_delivery(

                alert_id=
                    alert_id,

                channel=
                    "PUSH",

                destination=
                    str(
                        item["id"]
                    ),

                status=
                    result.get(
                        "status",
                        "UNKNOWN",
                    ),

                error_message=
                    result.get(
                        "error"
                    ),
            )


    except Exception as exc:

        logger.exception(
            "Push dispatch failed."
        )

        push_results.append({

            "status":
                "FAILED",

            "error":
                str(exc),
        })


    # ========================================================
    # RESPONSE
    # ========================================================

    return {

        "created":
            True,

        "alert_id":
            alert_id,

        "fingerprint":
            fingerprint,

        "level":
            level,

        "sms":
            sms_results,

        "push":
            push_results,
    }


# ============================================================
# ALERT HISTORY
# ============================================================

def get_alert_history(
    limit: int = 50,
):

    limit = max(
        1,
        min(
            int(limit),
            200,
        ),
    )


    query = text(
        """
        SELECT
            id,
            alert_type,
            level,
            title,
            message,
            latitude,
            longitude,
            probability,
            road_name,
            road_score,
            prediction_id,
            created_at

        FROM alert_events

        ORDER BY created_at DESC

        LIMIT :limit
        """
    )


    with engine.begin() as connection:

        rows = connection.execute(

            query,

            {
                "limit":
                    limit,
            },

        ).mappings().all()


    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# ALERTS NEAR LOCATION
# ============================================================

def get_alerts_near_location(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
):

    if radius_km <= 0:

        radius_km = 5.0


    query = text(
        """
        SELECT
            id,
            alert_type,
            level,
            title,
            message,
            latitude,
            longitude,
            probability,
            road_name,
            road_score,
            prediction_id,
            created_at,

            ST_Distance(

                ST_SetSRID(
                    ST_MakePoint(
                        longitude,
                        latitude
                    ),
                    4326
                )::geography,

                ST_SetSRID(
                    ST_MakePoint(
                        :longitude,
                        :latitude
                    ),
                    4326
                )::geography

            ) / 1000 AS distance_km

        FROM alert_events

        WHERE created_at >
            NOW() -
            INTERVAL '24 hours'

        AND ST_DWithin(

            ST_SetSRID(
                ST_MakePoint(
                    longitude,
                    latitude
                ),
                4326
            )::geography,

            ST_SetSRID(
                ST_MakePoint(
                    :longitude,
                    :latitude
                ),
                4326
            )::geography,

            :radius_m
        )

        ORDER BY created_at DESC
        """
    )


    with engine.begin() as connection:

        rows = connection.execute(

            query,

            {
                "latitude":
                    latitude,

                "longitude":
                    longitude,

                "radius_m":
                    radius_km * 1000,
            },

        ).mappings().all()


    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# ALERT CONFIGURATION
# ============================================================

def get_alert_configuration():

    twilio_configured = all(
        [
            os.getenv(
                "TWILIO_ACCOUNT_SID"
            ),

            os.getenv(
                "TWILIO_AUTH_TOKEN"
            ),

            os.getenv(
                "TWILIO_FROM_NUMBER"
            ),
        ]
    )


    push_configured = bool(
        os.getenv(
            "VAPID_PRIVATE_KEY"
        )
    )


    return {

        "alert_system":
            "enabled",

        "minimum_level":
            ALERT_MIN_LEVEL,

        "deduplication_minutes":
            ALERT_DEDUP_MINUTES,

        "twilio_configured":
            twilio_configured,

        "web_push_configured":
            push_configured,
    }