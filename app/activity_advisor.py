
import math
from numbers import Real

from app.aqi_pipeline import get_aqi_advisory


# --------------------------------------------------
# SUPPORTED ACTIVITIES
# --------------------------------------------------

ACTIVITIES = {
    "walking": "moderate",
    "running": "vigorous",
    "cycling": "vigorous",
    "outdoor exercise": "vigorous",
    "indoor exercise": "indoor",
    "general outdoor activities": "moderate"
}


# --------------------------------------------------
# SUPPORTED SENSITIVITY CATEGORIES
# --------------------------------------------------

SENSITIVITY_CATEGORIES = [
    "general",
    "children",
    "older_adults",
    "respiratory_conditions",
    "cardiovascular_conditions",
    "sensitive_group"
]


# --------------------------------------------------
# AQI SEVERITY CATEGORIES
# --------------------------------------------------

SEVERITY_LEVELS = {
    "good": 0,
    "satisfactory": 1,
    "moderately polluted": 2,
    "moderate": 2,
    "poor": 3,
    "very poor": 4,
    "severe": 5
}


POLLUTANTS = [
    "pm25",
    "pm10",
    "no2",
    "so2",
    "co",
    "o3"
]


# --------------------------------------------------
# GENERAL AQI GUIDANCE
# --------------------------------------------------

GENERAL_GUIDANCE = {
    "good": (
        "Air quality is in the Good category. "
        "Routine outdoor activity can generally continue."
    ),

    "satisfactory": (
        "Air quality is Satisfactory. "
        "Sensitive individuals may experience minor breathing discomfort."
    ),

    "moderately polluted": (
        "Air quality is Moderately polluted. "
        "Sensitive groups should reduce prolonged or strenuous outdoor exertion."
    ),

    "poor": (
        "Air quality is Poor. "
        "Reduce prolonged outdoor exposure and physical exertion."
    ),

    "very poor": (
        "Air quality is Very Poor. "
        "Limit outdoor exposure, especially for sensitive groups."
    ),

    "severe": (
        "Air quality is Severe. "
        "Avoid unnecessary outdoor exposure and physical exertion."
    )
}


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def create_error_result(errors):
    """Create a standard error response."""

    return {
        "success": False,
        "activity": None,
        "severity": None,
        "recommendation": None,
        "precautions": [],
        "reason": None,
        "alternative_activity": None,
        "general_guidance": [],
        "activity_specific_guidance": [],
        "errors": errors
    }


def convert_number(value):
    """Convert a value into a valid finite number."""

    if isinstance(value, bool):
        return None

    if not isinstance(value, Real):
        return None

    number = float(value)

    if not math.isfinite(number):
        return None

    return number


def normalize_activity(activity):
    """Validate and normalize an activity name."""

    if not isinstance(activity, str):
        return None

    activity = " ".join(
        activity.strip().lower().split()
    )

    if activity not in ACTIVITIES:
        return None

    return activity


def normalize_sensitivity(sensitivity_category):
    """Validate a user-selected sensitivity category."""

    if not isinstance(sensitivity_category, str):
        return None

    sensitivity_category = (
        sensitivity_category.strip().lower()
    )

    if sensitivity_category not in SENSITIVITY_CATEGORIES:
        return None

    return sensitivity_category


def normalize_severity(severity):
    """Normalize the severity returned by the severity engine."""

    if not isinstance(severity, str):
        return None

    severity = " ".join(
        severity.strip().lower().split()
    )

    if severity not in SEVERITY_LEVELS:
        return None

    return severity


def get_pollutant_readings(pollutants):
    """Return available numeric pollutant readings."""

    readings = {}

    if not isinstance(pollutants, dict):
        return readings

    for pollutant in POLLUTANTS:

        value = convert_number(
            pollutants.get(pollutant)
        )

        if value is not None and value >= 0:
            readings[pollutant] = value

    return readings


def is_sensitive(sensitivity_category):
    """Check whether a sensitive category was selected."""

    return sensitivity_category != "general"


# --------------------------------------------------
# GENERAL GUIDANCE
# --------------------------------------------------

def generate_general_guidance(severity):
    """Generate guidance based on the AQI category."""

    return [
        GENERAL_GUIDANCE[severity]
    ]


# --------------------------------------------------
# ACTIVITY-SPECIFIC GUIDANCE
# --------------------------------------------------

def generate_activity_guidance(
    activity,
    severity,
    sensitivity_category
):
    """
    Generate deterministic activity-specific guidance.

    The function does not diagnose medical conditions
    or claim that an activity is completely safe.
    """

    severity_level = SEVERITY_LEVELS[severity]

    activity_type = ACTIVITIES[activity]

    sensitive = is_sensitive(
        sensitivity_category
    )

    precautions = []

    recommendation = ""

    alternative_activity = ""

    # --------------------------------------------------
    # 1. INDOOR EXERCISE
    # --------------------------------------------------

    if activity_type == "indoor":

        recommendation = (
            "Indoor exercise is the preferred option over outdoor "
            "exercise under the current air-quality conditions."
        )

        alternative_activity = (
            "Rest or choose a lower-intensity indoor activity "
            "in a space with cleaner air."
        )

        if severity_level >= 3:

            precautions.append(
                "Choose an indoor space with cleaner air. "
                "Keep outdoor air from entering when outdoor pollution is high."
            )

            precautions.append(
                "Use suitable air filtration if available."
            )

        if severity_level >= 4:

            precautions.append(
                "Indoor air can also be affected by pollution. "
                "Avoid assuming that every indoor space has clean air."
            )

        if sensitive:

            precautions.append(
                "Pay attention to discomfort and reduce or stop activity "
                "if symptoms occur."
            )

        return {
            "recommendation": recommendation,
            "precautions": precautions,
            "alternative_activity": alternative_activity
        }

    # --------------------------------------------------
    # 2. GOOD AIR QUALITY
    # --------------------------------------------------

    if severity_level == 0:

        recommendation = (
            f"{activity.capitalize()} can generally continue "
            "with routine awareness of changing air quality."
        )

        alternative_activity = (
            "No change is required based on the current AQI category."
        )

    # --------------------------------------------------
    # 3. SATISFACTORY AIR QUALITY
    # --------------------------------------------------

    elif severity_level == 1:

        if sensitive and activity_type == "vigorous":

            recommendation = (
                f"Reduce the duration and intensity of {activity}. "
                "Consider moving the activity indoors."
            )

            alternative_activity = (
                "Indoor exercise in a space with cleaner air."
            )

            precautions.append(
                "Avoid prolonged or strenuous outdoor physical exertion."
            )

        else:

            recommendation = (
                f"{activity.capitalize()} may generally continue. "
                "Avoid unnecessarily prolonged strenuous exertion "
                "if you are sensitive to air pollution."
            )

            alternative_activity = (
                "Indoor exercise is an available alternative."
            )

    # --------------------------------------------------
    # 4. MODERATELY POLLUTED
    # --------------------------------------------------

    elif severity_level == 2:

        if sensitive:

            recommendation = (
                f"Reduce outdoor exposure during {activity}. "
                "Avoid prolonged or strenuous exertion and prefer "
                "an indoor alternative."
            )

            alternative_activity = (
                "Indoor exercise in a space with cleaner air."
            )

            precautions.append(
                "Avoid prolonged or strenuous outdoor physical exertion."
            )

        elif activity_type == "vigorous":

            recommendation = (
                f"Reduce the duration and intensity of {activity}. "
                "Moving the activity indoors is preferable."
            )

            alternative_activity = (
                "Indoor exercise in a space with cleaner air."
            )

            precautions.append(
                "Avoid prolonged high-intensity outdoor exercise."
            )

        else:

            recommendation = (
                f"Keep {activity} shorter and avoid prolonged "
                "outdoor exertion."
            )

            alternative_activity = (
                "Indoor walking or light indoor activity."
            )

    # --------------------------------------------------
    # 5. POOR AIR QUALITY
    # --------------------------------------------------

    elif severity_level == 3:

        if sensitive:

            recommendation = (
                f"Avoid {activity} outdoors under the current conditions. "
                "Choose an indoor alternative."
            )

        elif activity_type == "vigorous":

            recommendation = (
                f"Postpone outdoor {activity}. "
                "Choose an indoor alternative instead."
            )

        else:

            recommendation = (
                f"Reduce outdoor exposure during {activity}. "
                "Avoid prolonged activity and consider postponing it."
            )

        alternative_activity = (
            "Indoor exercise in a space with cleaner air."
        )

        precautions.append(
            "Avoid prolonged outdoor exposure."
        )

        precautions.append(
            "Reduce physical exertion and monitor for discomfort."
        )

    # --------------------------------------------------
    # 6. VERY POOR AIR QUALITY
    # --------------------------------------------------

    elif severity_level == 4:

        recommendation = (
            f"Postpone outdoor {activity}. "
            "Reduce outdoor exposure and choose an indoor alternative."
        )

        alternative_activity = (
            "Indoor exercise in a space with cleaner air, "
            "or rest until air quality improves."
        )

        precautions.append(
            "Avoid outdoor exercise and prolonged outdoor exposure."
        )

        precautions.append(
            "Sensitive individuals should take additional precautions."
        )

    # --------------------------------------------------
    # 7. SEVERE AIR QUALITY
    # --------------------------------------------------

    else:

        recommendation = (
            f"Avoid outdoor {activity} under the current conditions. "
            "Avoid unnecessary outdoor physical exertion."
        )

        alternative_activity = (
            "Rest or choose only a suitable low-intensity indoor activity "
            "in a space with cleaner air."
        )

        precautions.append(
            "Avoid unnecessary outdoor exposure, including strenuous activity."
        )

        precautions.append(
            "Even light physical activity may have health impacts "
            "under Severe AQI conditions."
        )

    # --------------------------------------------------
    # 8. ADDITIONAL SENSITIVE-GROUP PRECAUTIONS
    # --------------------------------------------------

    if sensitive and severity_level >= 1:

        precautions.append(
            "Pay attention to breathing discomfort or other symptoms. "
            "Stop the activity if discomfort occurs."
        )

    return {
        "recommendation": recommendation,
        "precautions": precautions,
        "alternative_activity": alternative_activity
    }


# --------------------------------------------------
# MAIN ACTIVITY ADVISOR
# --------------------------------------------------

def generate_activity_advisory(
    validation_result,
    severity_result,
    activity,
    sensitivity_category="general"
):
    """
    Generate an outdoor activity advisory.

    Parameters:
        validation_result:
            Output from validate_aqi_data().

        severity_result:
            Output from determine_severity().

        activity:
            Selected activity.

        sensitivity_category:
            Optional user-selected sensitivity category.

    Returns:
        Dictionary containing activity recommendations.
    """

    # --------------------------------------------------
    # 1. Validate input structures
    # --------------------------------------------------

    if not isinstance(validation_result, dict):

        return create_error_result([
            "Validation result must be a dictionary."
        ])

    if validation_result.get("valid") is not True:

        errors = validation_result.get(
            "errors",
            ["AQI validation failed."]
        )

        return create_error_result(errors)

    validated_data = validation_result.get("data")

    if not isinstance(validated_data, dict):

        return create_error_result([
            "Validated AQI data is missing."
        ])

    if not isinstance(severity_result, dict):

        return create_error_result([
            "Severity result must be a dictionary."
        ])

    # --------------------------------------------------
    # 2. Validate AQI
    # --------------------------------------------------

    aqi = convert_number(
        validated_data.get("aqi")
    )

    if aqi is None or aqi < 0:

        return create_error_result([
            "A valid non-negative AQI value is required."
        ])

    # --------------------------------------------------
    # 3. Validate severity
    # --------------------------------------------------

    severity = normalize_severity(
        severity_result.get("severity")
    )

    if severity is None:

        return create_error_result([
            "A valid severity category is required."
        ])

    # --------------------------------------------------
    # 4. Validate activity
    # --------------------------------------------------

    activity = normalize_activity(activity)

    if activity is None:

        return create_error_result([
            "Unsupported activity selected."
        ])

    # --------------------------------------------------
    # 5. Validate sensitivity category
    # --------------------------------------------------

    sensitivity_category = normalize_sensitivity(
        sensitivity_category
    )

    if sensitivity_category is None:

        return create_error_result([
            "Invalid sensitivity category selected."
        ])

    # --------------------------------------------------
    # 6. Get pollutant readings
    # --------------------------------------------------

    pollutant_readings = get_pollutant_readings(
        validated_data.get("pollutants")
    )

    available_pollutants = list(
        pollutant_readings.keys()
    )

    # --------------------------------------------------
    # 7. Generate general guidance
    # --------------------------------------------------

    general_guidance = generate_general_guidance(
        severity
    )

    # --------------------------------------------------
    # 8. Generate activity-specific guidance
    # --------------------------------------------------

    activity_result = generate_activity_guidance(
        activity,
        severity,
        sensitivity_category
    )

    activity_guidance = [
        activity_result["recommendation"]
    ]

    # --------------------------------------------------
    # 9. Generate explanation
    # --------------------------------------------------

    reason = (
        f"The validated AQI is {aqi}, and the existing severity "
        f"engine classified the air quality as "
        f"'{severity_result.get('severity')}'. "
        f"The selected activity is '{activity}', which is "
        f"classified as '{ACTIVITIES[activity]}' exertion. "
    )

    if sensitivity_category != "general":

        reason += (
            f"The selected sensitivity category is "
            f"'{sensitivity_category}', so additional precautions "
            "have been applied. "
        )

    else:

        reason += (
            "General-population guidance has been applied. "
        )

    if available_pollutants:

        reason += (
            "Available pollutant readings were provided for: "
            + ", ".join(available_pollutants)
            + ". "
        )

    else:

        reason += (
            "No usable individual pollutant readings were available. "
        )

    reason += (
        "The recommendation is based primarily on the existing AQI "
        "severity category and activity intensity. This module does "
        "not independently calculate AQI or apply pollutant-specific "
        "concentration thresholds."
    )

    # --------------------------------------------------
    # 10. Combine precautions
    # --------------------------------------------------

    precautions = (
        general_guidance
        + activity_result["precautions"]
    )

    # --------------------------------------------------
    # 11. Final response
    # --------------------------------------------------

    return {
        "success": True,
        "activity": activity,
        "severity": severity_result.get("severity"),
        "aqi": aqi,
        "sensitivity_category": sensitivity_category,
        "recommendation": activity_result["recommendation"],
        "precautions": precautions,
        "general_guidance": general_guidance,
        "activity_specific_guidance": activity_guidance,
        "reason": reason,
        "alternative_activity": activity_result["alternative_activity"],
        "pollutant_readings": pollutant_readings,
        "errors": []
    }


# --------------------------------------------------
# LIVE PIPELINE INTEGRATION
# --------------------------------------------------

def get_live_activity_advisory(
    location,
    activity,
    sensitivity_category="general"
):
    """
    Get live AQI data using the existing advisory pipeline
    and generate an activity recommendation.

    No existing module interface is modified.
    """

    if not isinstance(location, str) or not location.strip():

        return create_error_result([
            "Location must be a non-empty string."
        ])

    result = get_aqi_advisory(
        location.strip()
    )

    if not isinstance(result, dict):

        return create_error_result([
            "AQI pipeline returned malformed data."
        ])

    if result.get("success") is not True:

        return create_error_result(
            result.get(
                "errors",
                ["AQI data could not be retrieved."]
            )
        )

    # Reconstruct the validated data structure from
    # the successful final pipeline response.

    validation_result = {
        "valid": True,
        "data": {
            "location": result.get("location"),
            "aqi": result.get("aqi"),
            "pollutants": result.get("pollutants", {}),
            "timestamp": result.get("timestamp")
        },
        "errors": []
    }

    # Reconstruct the severity result from the same
    # severity output returned by the existing pipeline.

    severity_result = {
        "severity": result.get("severity"),
        "severity_reason": result.get("severity_reason")
    }

    return generate_activity_advisory(
        validation_result,
        severity_result,
        activity,
        sensitivity_category
    )
