# ============================================================
# ALERT ROUTES
# NER LANDSLIDE EARLY WARNING SYSTEM
# ============================================================

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy import text

from ..database import engine

from ..services.alert_service import (
    init_alert_tables,
    dispatch_alert,
    get_alert_history,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"],
)


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class SubscriberRequest(BaseModel):

    name: str = Field(
        min_length=1,
        max_length=200,
    )

    phone: Optional[str] = None

    latitude: float

    longitude: float

    radius_km: float = Field(
        default=10.0,
        gt=0,
        le=500,
    )

    sms_enabled: bool = True

    push_enabled: bool = True


class PushSubscriptionRequest(BaseModel):

    subscriber_id: int

    endpoint: str

    p256dh: str

    auth: str


class DispatchAlertRequest(BaseModel):

    alert_type: str = "LOCATION"

    level: str

    title: str

    message: str

    latitude: float

    longitude: float

    probability: Optional[float] = None

    prediction_id: Optional[int] = None

    road_name: Optional[str] = None


# ============================================================
# STARTUP
# ============================================================

@router.on_event("startup")
def initialize_alert_system():

    try:

        init_alert_tables()

        print(
            "ALERT SYSTEM: tables initialized successfully."
        )

    except Exception as exc:

        print(
            "ALERT SYSTEM: table initialization failed:",
            repr(exc),
        )


# ============================================================
# SUBSCRIBE A USER / AUTHORITY / COMMUNITY
# ============================================================

@router.post("/subscribe")
def subscribe(
    request: SubscriberRequest,
):

    # --------------------------------------------------------
    # Validate coordinates
    # --------------------------------------------------------

    if not (
        -90 <= request.latitude <= 90
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid latitude.",
        )

    if not (
        -180 <= request.longitude <= 180
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid longitude.",
        )


    # --------------------------------------------------------
    # Insert subscriber
    # --------------------------------------------------------

    with engine.begin() as connection:

        result = connection.execute(

            text(
                """
                INSERT INTO alert_subscribers (
                    name,
                    phone,
                    latitude,
                    longitude,
                    radius_km,
                    sms_enabled,
                    push_enabled
                )

                VALUES (
                    :name,
                    :phone,
                    :latitude,
                    :longitude,
                    :radius_km,
                    :sms_enabled,
                    :push_enabled
                )

                RETURNING id
                """
            ),

            {
                "name":
                    request.name,

                "phone":
                    request.phone,

                "latitude":
                    request.latitude,

                "longitude":
                    request.longitude,

                "radius_km":
                    request.radius_km,

                "sms_enabled":
                    request.sms_enabled,

                "push_enabled":
                    request.push_enabled,
            },
        )

        subscriber_id = result.scalar_one()


    return {

        "status":
            "subscribed",

        "subscriber_id":
            subscriber_id,

        "name":
            request.name,

        "phone":
            request.phone,

        "latitude":
            request.latitude,

        "longitude":
            request.longitude,

        "radius_km":
            request.radius_km,

        "sms_enabled":
            request.sms_enabled,

        "push_enabled":
            request.push_enabled,
    }


# ============================================================
# SAVE / UPDATE PUSH SUBSCRIPTION
# ============================================================

@router.post("/push-subscription")
def push_subscription(
    request: PushSubscriptionRequest,
):

    # --------------------------------------------------------
    # Check subscriber
    # --------------------------------------------------------

    with engine.begin() as connection:

        subscriber = connection.execute(

            text(
                """
                SELECT id

                FROM alert_subscribers

                WHERE id = :subscriber_id

                AND active = TRUE
                """
            ),

            {
                "subscriber_id":
                    request.subscriber_id
            },
        ).fetchone()


        if subscriber is None:

            raise HTTPException(
                status_code=404,
                detail="Subscriber not found.",
            )


        # ----------------------------------------------------
        # Insert / update push subscription
        #
        # IMPORTANT:
        # PostgreSQL syntax must be written as:
        #
        # DO UPDATE SET
        #     subscriber_id = EXCLUDED.subscriber_id
        #
        # ----------------------------------------------------

        connection.execute(

            text(
                """
                INSERT INTO push_subscriptions (
                    subscriber_id,
                    endpoint,
                    p256dh,
                    auth,
                    active
                )

                VALUES (
                    :subscriber_id,
                    :endpoint,
                    :p256dh,
                    :auth,
                    TRUE
                )

                ON CONFLICT (endpoint)

                DO UPDATE SET
                    subscriber_id = EXCLUDED.subscriber_id,
                    p256dh = EXCLUDED.p256dh,
                    auth = EXCLUDED.auth,
                    active = TRUE
                """
            ),

            {
                "subscriber_id":
                    request.subscriber_id,

                "endpoint":
                    request.endpoint,

                "p256dh":
                    request.p256dh,

                "auth":
                    request.auth,
            },
        )


    return {

        "status":
            "push subscription saved",

        "subscriber_id":
            request.subscriber_id,
    }


# ============================================================
# ALERT HISTORY
# ============================================================

@router.get("/history")
def alert_history(
    limit: int = 100,
):

    limit = max(
        1,
        min(
            limit,
            500,
        ),
    )


    return {

        "alerts":
            get_alert_history(
                limit
            ),
    }


# ============================================================
# ALERTS ALIAS
# ============================================================

@router.get("")
def alerts(
    limit: int = 100,
):

    limit = max(
        1,
        min(
            limit,
            500,
        ),
    )


    return {

        "alerts":
            get_alert_history(
                limit
            ),
    }


# ============================================================
# MANUAL ALERT DISPATCH
# ============================================================

@router.post("/dispatch")
def manual_dispatch(
    request: DispatchAlertRequest,
):

    # --------------------------------------------------------
    # Coordinate validation
    # --------------------------------------------------------

    if not (
        -90 <= request.latitude <= 90
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid latitude.",
        )

    if not (
        -180 <= request.longitude <= 180
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid longitude.",
        )


    # --------------------------------------------------------
    # Probability validation
    # --------------------------------------------------------

    if request.probability is not None:

        if not (
            0.0 <= request.probability <= 1.0
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "probability must be "
                    "between 0 and 1."
                ),
            )


    # --------------------------------------------------------
    # Dispatch
    # --------------------------------------------------------

    try:

        result = dispatch_alert(

            alert_type=
                request.alert_type,

            level=
                request.level,

            title=
                request.title,

            message=
                request.message,

            latitude=
                request.latitude,

            longitude=
                request.longitude,

            probability=
                request.probability,

            prediction_id=
                request.prediction_id,

            road_name=
                request.road_name,
        )

        return result


    except Exception as exc:

        print(
            "Alert dispatch failed:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Alert dispatch failed: "
                + str(exc)
            ),
        )