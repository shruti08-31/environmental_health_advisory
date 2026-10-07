# ============================================================
# COMPLETE AQI ADVISORY PIPELINE
# ============================================================
#
# Part 2 -> WAQI API
# Part 3 -> Validation
# Part 4 -> Severity Mapping
# Part 5 -> Health Guidance
#
# This module only integrates the existing modules.
#
# It does NOT implement:
# - Intent routing
# - RAG
# - LLM
# - Dashboard
# - FastAPI
# ============================================================

from app.waqi_client import get_aqi_data
from app.validator import validate_aqi_data
from app.severity_engine import determine_severity
from app.health_guidance import generate_health_guidance


def get_aqi_advisory(location):
    """
    Run the complete AQI advisory pipeline.

    Pipeline:
        WAQI API
            ->
        Validation
            ->
        Severity
            ->
        Health Guidance

    Parameters
    ----------
    location : str
        City or location to query.

    Returns
    -------
    dict
        Standardized complete AQI response.
    """

    # --------------------------------------------------------
    # 1. Fetch live WAQI data
    # --------------------------------------------------------

    waqi_result = get_aqi_data(location)

    # --------------------------------------------------------
    # Basic safety check
    # --------------------------------------------------------

    if not isinstance(waqi_result, dict):

        return {
            "success": False,
            "location": None,
            "aqi": None,
            "pollutants": {},
            "severity": None,
            "severity_reason": None,
            "guidance": [],
            "urgency": None,
            "errors": [
                "WAQI module returned malformed data."
            ]
        }

    # --------------------------------------------------------
    # Extract basic AQI data
    # --------------------------------------------------------

    location_value = waqi_result.get("location")
    aqi = waqi_result.get("aqi")
    pollutants = waqi_result.get("pollutants")

    if not isinstance(pollutants, dict):
        pollutants = {}

    # --------------------------------------------------------
    # API-level failure
    # --------------------------------------------------------

    if waqi_result.get("success") is not True:

        error = waqi_result.get("error")

        if error is None:
            error = "WAQI API request failed."

        return {
            "success": False,
            "location": location_value,
            "aqi": aqi,
            "pollutants": pollutants,
            "severity": None,
            "severity_reason": None,
            "guidance": [],
            "urgency": None,
            "errors": [
                error
            ]
        }

    # --------------------------------------------------------
    # 2. Validate AQI and pollutant data
    # --------------------------------------------------------

    validation_result = validate_aqi_data(
        waqi_result
    )

    if not isinstance(validation_result, dict):

        return {
            "success": False,
            "location": location_value,
            "aqi": aqi,
            "pollutants": pollutants,
            "severity": None,
            "severity_reason": None,
            "guidance": [],
            "urgency": None,
            "errors": [
                "Validation module returned malformed data."
            ]
        }

    # --------------------------------------------------------
    # Validation failure
    # --------------------------------------------------------

    if validation_result.get("valid") is not True:

        errors = validation_result.get(
            "errors",
            []
        )

        if not isinstance(errors, list):
            errors = [
                str(errors)
            ]

        return {
            "success": False,
            "location": location_value,
            "aqi": aqi,
            "pollutants": pollutants,
            "severity": None,
            "severity_reason": None,
            "guidance": [],
            "urgency": None,
            "errors": errors
        }

    # Use validated data from Part 3.
    validated_data = validation_result.get(
        "data",
        {}
    )

    if isinstance(validated_data, dict):

        location_value = validated_data.get(
            "location",
            location_value
        )

        aqi = validated_data.get(
            "aqi",
            aqi
        )

        pollutants = validated_data.get(
            "pollutants",
            pollutants
        )

    # --------------------------------------------------------
    # 3. Determine severity
    # --------------------------------------------------------

    severity_result = determine_severity(
        validation_result
    )

    if not isinstance(severity_result, dict):

        return {
            "success": False,
            "location": location_value,
            "aqi": aqi,
            "pollutants": pollutants,
            "severity": None,
            "severity_reason": None,
            "guidance": [],
            "urgency": None,
            "errors": [
                "Severity module returned malformed data."
            ]
        }

    severity = severity_result.get(
        "severity"
    )

    severity_reason = severity_result.get(
        "severity_reason"
    )

    # --------------------------------------------------------
    # Severity failure
    # --------------------------------------------------------

    if severity is None:

        error = severity_result.get(
            "severity_reason",
            "Severity could not be determined."
        )

        return {
            "success": False,
            "location": location_value,
            "aqi": aqi,
            "pollutants": pollutants,
            "severity": None,
            "severity_reason": severity_reason,
            "guidance": [],
            "urgency": None,
            "errors": [
                error
            ]
        }

    # --------------------------------------------------------
    # 4. Generate deterministic health guidance
    # --------------------------------------------------------

    health_result = generate_health_guidance(
        validation_result,
        severity_result
    )

    if not isinstance(health_result, dict):

        return {
            "success": False,
            "location": location_value,
            "aqi": aqi,
            "pollutants": pollutants,
            "severity": severity,
            "severity_reason": severity_reason,
            "guidance": [],
            "urgency": None,
            "errors": [
                "Health guidance module returned malformed data."
            ]
        }

    urgency = health_result.get(
        "urgency"
    )

    guidance = health_result.get(
        "guidance",
        []
    )

    # --------------------------------------------------------
    # Health guidance failure
    # --------------------------------------------------------

    if urgency is None:

        errors = health_result.get(
            "guidance",
            [
                "Health guidance could not be generated."
            ]
        )

        if not isinstance(errors, list):
            errors = [
                str(errors)
            ]

        return {
            "success": False,
            "location": location_value,
            "aqi": aqi,
            "pollutants": pollutants,
            "severity": severity,
            "severity_reason": severity_reason,
            "guidance": [],
            "urgency": None,
            "errors": errors
        }

    # --------------------------------------------------------
    # 5. Final successful response
    # --------------------------------------------------------

    return {
        "success": True,
        "location": location_value,
        "aqi": aqi,
        "pollutants": pollutants,
        "severity": severity,
        "severity_reason": severity_reason,
        "guidance": guidance,
        "urgency": urgency,
        "errors": []
    }