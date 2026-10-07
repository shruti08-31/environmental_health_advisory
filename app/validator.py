from numbers import Real


POLLUTANT_NAMES = [
    "pm25",
    "pm10",
    "no2",
    "so2",
    "co",
    "o3"
]


def _create_result(valid, data, errors):
    """
    Create the standard validation result.
    """

    return {
        "valid": valid,
        "data": data,
        "errors": errors
    }


def _is_valid_number(value):
    """
    Check whether a value is a valid numeric value.

    Boolean values are rejected because True/False are technically
    subclasses of integers in Python but are not pollutant values.
    """

    if isinstance(value, bool):
        return False

    if not isinstance(value, Real):
        return False

    return True


def validate_aqi_data(api_result):
    """
    Validate the structured result returned by Part 2.

    Parameters:
        api_result (dict):
            Result returned by get_aqi_data().

    Returns:
        dict:
            {
                "valid": True/False,
                "data": {...},
                "errors": [...]
            }

    Validation performed:
        - response structure
        - location
        - AQI availability
        - AQI numeric validity
        - pollutant availability
        - pollutant numeric validity
        - null/malformed values
    """

    errors = []

    # --------------------------------------------------
    # 1. Check that input itself is a dictionary
    # --------------------------------------------------

    if not isinstance(api_result, dict):
        return _create_result(
            False,
            None,
            ["Input must be a dictionary."]
        )

    # --------------------------------------------------
    # 2. Check whether Part 2 itself failed
    # --------------------------------------------------

    success = api_result.get("success")

    if success is not True:
        part2_error = api_result.get("error")

        if part2_error:
            errors.append(
                f"WAQI data retrieval failed: {part2_error}"
            )
        else:
            errors.append(
                "WAQI data retrieval failed."
            )

    # --------------------------------------------------
    # 3. Create a safe data structure
    # --------------------------------------------------

    location = api_result.get("location")
    aqi = api_result.get("aqi")
    timestamp = api_result.get("timestamp")

    pollutants = api_result.get("pollutants")

    if not isinstance(pollutants, dict):
        pollutants = {}

        errors.append(
            "Pollutants data is missing or malformed."
        )

    # --------------------------------------------------
    # 4. Validate location
    # --------------------------------------------------

    if location is None:
        errors.append(
            "Location is missing."
        )

    elif not isinstance(location, str):
        errors.append(
            "Location is invalid: expected a string."
        )

    elif not location.strip():
        errors.append(
            "Location is invalid: value is empty."
        )

    # --------------------------------------------------
    # 5. Validate AQI availability
    # --------------------------------------------------

    if aqi is None:
        errors.append(
            "AQI is missing."
        )

    # --------------------------------------------------
    # 6. Validate AQI numeric value
    # --------------------------------------------------

    elif not _is_valid_number(aqi):
        errors.append(
            "AQI is invalid: expected a numeric value."
        )

    elif aqi < 0:
        errors.append(
            "AQI is invalid: value cannot be negative."
        )

    # --------------------------------------------------
    # 7. Validate pollutants
    # --------------------------------------------------

    validated_pollutants = {}

    for pollutant_name in POLLUTANT_NAMES:

        if pollutant_name not in pollutants:
            validated_pollutants[pollutant_name] = None

            errors.append(
                f"Pollutant '{pollutant_name}' is missing."
            )

            continue

        value = pollutants.get(pollutant_name)

        # Missing/null pollutant
        if value is None:
            validated_pollutants[pollutant_name] = None

            errors.append(
                f"Pollutant '{pollutant_name}' is missing."
            )

            continue

        # Invalid/non-numeric pollutant
        if not _is_valid_number(value):
            validated_pollutants[pollutant_name] = None

            errors.append(
                f"Pollutant '{pollutant_name}' is invalid: "
                f"expected a numeric value."
            )

            continue

        # Negative pollutant value
        if value < 0:
            validated_pollutants[pollutant_name] = None

            errors.append(
                f"Pollutant '{pollutant_name}' is invalid: "
                f"value cannot be negative."
            )

            continue

        # Valid pollutant
        validated_pollutants[pollutant_name] = value

    # --------------------------------------------------
    # 8. Create cleaned data object
    # --------------------------------------------------

    cleaned_data = {
        "location": location,
        "aqi": aqi,
        "pollutants": validated_pollutants,
        "timestamp": timestamp
    }

    # --------------------------------------------------
    # 9. Determine overall validity
    # --------------------------------------------------

    valid = len(errors) == 0

    return _create_result(
        valid,
        cleaned_data,
        errors
    )