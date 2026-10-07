from app.waqi_client import get_aqi_data
from app.validator import validate_aqi_data
from app.severity_engine import determine_severity


def print_result(title, result):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)

    print("Severity:", result["severity"])
    print("AQI:", result["aqi"])
    print("Reason:", result["severity_reason"])

    print("Pollutant conditions:")

    if result["pollutant_conditions"]:

        for condition in result["pollutant_conditions"]:
            print(
                f" - {condition['pollutant']}: "
                f"{condition['value']} -> "
                f"{condition['condition']}"
            )

    else:
        print(" None")


def create_validation_data(
    aqi,
    pm25=20,
    pm10=40,
    no2=30,
    so2=20,
    co=0.5,
    o3=30
):
    """
    Create data in exactly the same structure produced
    by Part 3.
    """

    api_result = {
        "success": True,
        "location": "Delhi",
        "aqi": aqi,
        "pollutants": {
            "pm25": pm25,
            "pm10": pm10,
            "no2": no2,
            "so2": so2,
            "co": co,
            "o3": o3
        },
        "timestamp": "2026-10-07 15:00:00",
        "error": None
    }

    return validate_aqi_data(api_result)


def test_low_severity():
    """
    AQI 40 -> Good
    """

    validation_result = create_validation_data(
        aqi=40
    )

    result = determine_severity(
        validation_result
    )

    print_result(
        "LOW SEVERITY TEST",
        result
    )


def test_moderate_severity():
    """
    AQI 144 -> Moderately polluted
    """

    validation_result = create_validation_data(
        aqi=144,
        pm25=144,
        pm10=85,
        no2=9.6,
        so2=4.3,
        co=12.2,
        o3=19.6
    )

    result = determine_severity(
        validation_result
    )

    print_result(
        "MODERATE SEVERITY TEST",
        result
    )


def test_high_severity():
    """
    AQI 350 -> Very Poor
    """

    validation_result = create_validation_data(
        aqi=350
    )

    result = determine_severity(
        validation_result
    )

    print_result(
        "HIGH SEVERITY TEST",
        result
    )


def test_boundary_values():
    """
    Test the boundaries between AQI categories.
    """

    boundary_values = [
        0,
        50,
        51,
        100,
        101,
        200,
        201,
        300,
        301,
        400,
        401,
        500
    ]

    print()
    print("=" * 60)
    print("AQI BOUNDARY TEST")
    print("=" * 60)

    for aqi in boundary_values:

        validation_result = create_validation_data(
            aqi=aqi
        )

        result = determine_severity(
            validation_result
        )

        print(
            f"AQI {aqi:>3} -> "
            f"{result['severity']}"
        )


def test_invalid_data():
    """
    Part 3 says the data is invalid.
    Part 4 must not classify it.
    """

    validation_result = {
        "valid": False,
        "data": {
            "location": "Delhi",
            "aqi": None,
            "pollutants": {
                "pm25": None,
                "pm10": 85,
                "no2": 9.6,
                "so2": 4.3,
                "co": 12.2,
                "o3": 19.6
            },
            "timestamp": None
        },
        "errors": [
            "AQI is missing."
        ]
    }

    result = determine_severity(
        validation_result
    )

    print_result(
        "INVALID DATA TEST",
        result
    )


def test_live_integration():
    """
    Actual Part 2 -> Part 3 -> Part 4 integration.
    """

    waqi_result = get_aqi_data("Delhi")

    validation_result = validate_aqi_data(
        waqi_result
    )

    severity_result = determine_severity(
        validation_result
    )

    print_result(
        "LIVE WAQI -> VALIDATION -> SEVERITY",
        severity_result
    )


if __name__ == "__main__":

    test_low_severity()
    test_moderate_severity()
    test_high_severity()
    test_boundary_values()
    test_invalid_data()
    test_live_integration()