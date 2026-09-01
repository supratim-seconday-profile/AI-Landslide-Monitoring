# ============================================================
# CENTRAL RISK ENGINE
# NER LANDSLIDE EARLY WARNING SYSTEM
# ============================================================

"""
Centralised risk classification logic.

IMPORTANT:
The ML model produces a probability.
This module converts that probability into the
application's standard risk level.

Current thresholds:
    < 0.50  -> LOW
    0.50-0.69 -> MEDIUM
    >= 0.70 -> HIGH

These thresholds can later be calibrated using
validation data.
"""


def get_risk_level(probability: float) -> str:
    """
    Convert landslide probability into risk level.
    """

    probability = float(probability)

    # Protect against unexpected values.
    probability = max(0.0, min(1.0, probability))

    if probability >= 0.70:
        return "HIGH"

    if probability >= 0.50:
        return "MEDIUM"

    return "LOW"


def is_alert(probability: float) -> bool:
    """
    Return True when risk reaches MEDIUM or HIGH.
    """

    return get_risk_level(probability) in {
        "MEDIUM",
        "HIGH"
    }


def get_alert_message(risk_level: str) -> str:

    if risk_level == "HIGH":
        return (
            "HIGH landslide risk detected. "
            "Immediate field assessment is recommended."
        )

    if risk_level == "MEDIUM":
        return (
            "MEDIUM landslide risk detected. "
            "Continue monitoring local conditions."
        )

    return (
        "Landslide risk is currently LOW."
    )


def get_recommended_action(risk_level: str) -> str:

    if risk_level == "HIGH":
        return "IMMEDIATE FIELD INSPECTION"

    if risk_level == "MEDIUM":
        return "INCREASED MONITORING"

    return "ROUTINE MONITORING"