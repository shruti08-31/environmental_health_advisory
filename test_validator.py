from app.waqi_client import get_aqi_data
from app.validator import validate_aqi_data


def print_result(title, result):
    print()
    print("=" * 50)
    print(title)
    print("=" * 50)

    print("Valid:", result["valid"])
    print("Data:", result["data"])

    print("Errors:")

    if result["errors"]:
        for error in result["errors"]:
            print(" -", error)
    else:
        print(" None")


def test_live_waqi():
    """
    Integration test:
    Part 2 -> Part 3
    """

    waqi_result = get_aqi_data("Delhi")

    validation_result = validate_aqi_data(
        waqi_result
    )

    print_result(
        "LIVE WAQI -> VALIDATION",
        validation_result
    )


def test_missing_pollutant():
    """
    Test that a missing pollutant does not crash validation.
    """

    data = {
        "success": True,
        "location": "Delhi",
        "aqi": 144,
        "pollutants": {
            "pm25": 144,
            "pm10": 85,
            "no2": None,
            "so2": 4.3,
            "co": 12.2,
            "o3": 19.6
        },
        "timestamp": "2026-10-07 15:00:00",
        "error": None
    }

    result = validate_aqi_data(data)

    print_result(
        "MISSING POLLUTANT TEST",
        result
    )


def test_invalid_pollutant():
    """
    Test non-numeric pollutant value.
    """

    data = {
        "success": True,
        "location": "Delhi",
        "aqi": 144,
        "pollutants": {
            "pm25": "not-a-number",
            "pm10": 85,
            "no2": 9.6,
            "so2": 4.3,
            "co": 12.2,
            "o3": 19.6
        },
        "timestamp": "2026-10-07 15:00:00",
        "error": None
    }

    result = validate_aqi_data(data)

    print_result(
        "INVALID POLLUTANT TEST",
        result
    )


def test_missing_aqi():
    """
    Test missing AQI.
    """

    data = {
        "success": True,
        "location": "Delhi",
        "aqi": None,
        "pollutants": {
            "pm25": 144,
            "pm10": 85,
            "no2": 9.6,
            "so2": 4.3,
            "co": 12.2,
            "o3": 19.6
        },
        "timestamp": "2026-10-07 15:00:00",
        "error": None
    }

    result = validate_aqi_data(data)

    print_result(
        "MISSING AQI TEST",
        result
    )


def test_malformed_input():
    """
    Test completely malformed input.
    """

    data = None

    result = validate_aqi_data(data)

    print_result(
        "MALFORMED INPUT TEST",
        result
    )


def test_invalid_location():
    """
    Test invalid location.
    """

    data = {
        "success": True,
        "location": "",
        "aqi": 144,
        "pollutants": {
            "pm25": 144,
            "pm10": 85,
            "no2": 9.6,
            "so2": 4.3,
            "co": 12.2,
            "o3": 19.6
        },
        "timestamp": "2026-10-07 15:00:00",
        "error": None
    }

    result = validate_aqi_data(data)

    print_result(
        "INVALID LOCATION TEST",
        result
    )


if __name__ == "__main__":

    test_live_waqi()
    test_missing_pollutant()
    test_invalid_pollutant()
    test_missing_aqi()
    test_malformed_input()
    test_invalid_location()