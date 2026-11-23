
from numbers import Real
import math


POLLUTANT_NAMES = [
    "pm25",
    "pm10",
    "no2",
    "so2",
    "co",
    "o3"
]


def _create_result(valid, data, errors, warnings=None):
    """
    Create the standard validation result.
    """

    return {
        "valid": valid,
        "data": data,
        "errors": errors,
        "warnings": warnings if warnings is not None else []
    }


def _is_valid_number(value):
    """
    Check whether a value is a valid finite number.
    """

    if isinstance(value, bool):
        return False

    if not isinstance(value, Real):
        return False

    return math.isfinite(float(value))


def validate_aqi_data(api_result):
    """
    Validate AQI data while allowing missing optional pollutants.

    Critical errors:
        - Invalid API response
        - Missing or invalid location
        - Missing or invalid AQI

    Warnings:
        - Missing pollutants
        - Invalid pollutants
    """

    errors = []
    warnings = []

    # 1. Check input structure

    if not isinstance(api_result, dict):

        return _create_result(
            False,
            None,
            ["Input must be a dictionary."]
        )

    # 2. Check API success

    if api_result.get("success") is not True:

        part2_error = api_result.get("error")

        if part2_error:
            errors.append(
                f"WAQI data retrieval failed: {part2_error}"
            )
        else:
            errors.append(
                "WAQI data retrieval failed."
            )

    # 3. Extract data

    location = api_result.get("location")
    aqi = api_result.get("aqi")
    timestamp = api_result.get("timestamp")

    pollutants = api_result.get("pollutants")

    if not isinstance(pollutants, dict):

        pollutants = {}

        warnings.append(
            "Pollutants data is missing or malformed."
        )

    # 4. Validate location

    if location is None:

        errors.append("Location is missing.")

    elif not isinstance(location, str):

        errors.append(
            "Location is invalid: expected a string."
        )

    elif not location.strip():

        errors.append(
            "Location is invalid: value is empty."
        )

    # 5. Validate AQI

    if aqi is None:

        errors.append("AQI is missing.")

    elif not _is_valid_number(aqi):

        errors.append(
            "AQI is invalid: expected a finite numeric value."
        )

    elif aqi < 0:

        errors.append(
            "AQI is invalid: value cannot be negative."
        )

    # 6. Validate individual pollutants

    validated_pollutants = {}

    for pollutant_name in POLLUTANT_NAMES:

        value = pollutants.get(pollutant_name)

        if value is None:

            validated_pollutants[pollutant_name] = None

            warnings.append(
                f"Pollutant '{pollutant_name}' is missing."
            )

            continue

        if not _is_valid_number(value):

            validated_pollutants[pollutant_name] = None

            warnings.append(
                f"Pollutant '{pollutant_name}' is invalid."
            )

            continue

        if value < 0:

            validated_pollutants[pollutant_name] = None

            warnings.append(
                f"Pollutant '{pollutant_name}' cannot be negative."
            )

            continue

        validated_pollutants[pollutant_name] = value

    # 7. Create cleaned data

    cleaned_data = {
        "location": location,
        "aqi": aqi,
        "pollutants": validated_pollutants,
        "timestamp": timestamp
    }

    # 8. Determine validity using critical errors only

    valid = len(errors) == 0

    return _create_result(
        valid,
        cleaned_data,
        errors,
        warnings
    )
