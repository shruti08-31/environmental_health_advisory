from app.severity_rules import AQI_RULES, POLLUTANT_RULES


POLLUTANT_NAMES = [
    "pm25",
    "pm10",
    "no2",
    "so2",
    "co",
    "o3"
]


def _invalid_result(aqi=None, reason="Invalid data"):
    """
    Standard result returned when Part 3 validation fails.
    """

    return {
        "severity": None,
        "aqi": aqi,
        "severity_reason": reason,
        "pollutant_conditions": []
    }


def _get_aqi_severity(aqi):
    """
    Determine overall severity from AQI.
    """

    for rule in AQI_RULES:

        if (
            aqi >= rule["minimum"]
            and aqi <= rule["maximum"]
        ):
            return rule["severity"]

    return None


def _get_pollutant_severity(pollutant_name, value):
    """
    Determine the condition category of one pollutant.
    """

    rules = POLLUTANT_RULES.get(pollutant_name)

    if rules is None:
        return None

    for severity, minimum, maximum in rules:

        # Open-ended upper range
        if maximum is None:
            if value >= minimum:
                return severity

        # Normal range
        elif (
            value >= minimum
            and value <= maximum
        ):
            return severity

    return None


def _build_pollutant_conditions(pollutants):
    """
    Evaluate all available pollutant measurements.

    Missing values are skipped because Part 3 already records
    them as validation errors.
    """

    conditions = []

    for pollutant_name in POLLUTANT_NAMES:

        value = pollutants.get(pollutant_name)

        # Missing pollutant
        if value is None:
            continue

        pollutant_severity = _get_pollutant_severity(
            pollutant_name,
            value
        )

        if pollutant_severity is None:
            continue

        conditions.append({
            "pollutant": pollutant_name,
            "value": value,
            "condition": pollutant_severity
        })

    return conditions


def determine_severity(validation_result):
    """
    Determine deterministic AQI severity using validated
    data from Part 3.

    Parameters:
        validation_result (dict):
            Output of validate_aqi_data().

    Returns:
        dict:
            {
                "severity": "...",
                "aqi": ...,
                "severity_reason": "...",
                "pollutant_conditions": [...]
            }

    No machine learning or LLM is used.
    """

    # --------------------------------------------------
    # 1. Validate Part 3 result
    # --------------------------------------------------

    if not isinstance(validation_result, dict):
        return _invalid_result(
            reason="Invalid validation result."
        )

    if validation_result.get("valid") is not True:
        return _invalid_result(
            reason=(
                "Severity cannot be determined because "
                "the AQI/pollutant data failed validation."
            )
        )

    # --------------------------------------------------
    # 2. Get validated data
    # --------------------------------------------------

    data = validation_result.get("data")

    if not isinstance(data, dict):
        return _invalid_result(
            reason="Validated data is missing or malformed."
        )

    aqi = data.get("aqi")

    if aqi is None:
        return _invalid_result(
            reason="AQI is missing."
        )

    # --------------------------------------------------
    # 3. Determine overall AQI severity
    # --------------------------------------------------

    severity = _get_aqi_severity(aqi)

    if severity is None:
        return _invalid_result(
            aqi=aqi,
            reason=(
                "AQI value is outside the predefined "
                "0-500 severity range."
            )
        )

    # --------------------------------------------------
    # 4. Evaluate pollutant conditions
    # --------------------------------------------------

    pollutants = data.get("pollutants")

    if not isinstance(pollutants, dict):
        pollutants = {}

    pollutant_conditions = _build_pollutant_conditions(
        pollutants
    )

    # --------------------------------------------------
    # 5. Build deterministic explanation
    # --------------------------------------------------

    severity_reason = (
        f"AQI value {aqi} falls in the "
        f"'{severity}' category according to the "
        f"predefined AQI severity ranges."
    )

    # --------------------------------------------------
    # 6. Return standard output
    # --------------------------------------------------

    return {
        "severity": severity,
        "aqi": aqi,
        "severity_reason": severity_reason,
        "pollutant_conditions": pollutant_conditions
    }