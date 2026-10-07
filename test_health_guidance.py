from app.waqi_client import get_aqi_data
from app.validator import validate_aqi_data
from app.severity_engine import determine_severity
from app.health_guidance import generate_health_guidance


def print_result(title, result):

    print()
    print("=" * 60)
    print(title)
    print("=" * 60)

    print("Urgency:", result["urgency"])

    print("Guidance:")

    for item in result["guidance"]:
        print(" -", item)

    print("Sensitive groups:")

    if result["sensitive_groups"]:

        for group in result["sensitive_groups"]:
            print(" -", group)

    else:
        print(" None")


def create_pipeline_data(
    aqi,
    pm25=20,
    pm10=40,
    no2=30,
    so2=20,
    co=0.5,
    o3=30
):
    """
    Create the same Part 2 structure and pass it
    through Part 3 and Part 4.
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

    validation_result = validate_aqi_data(
        api_result
    )

    severity_result = determine_severity(
        validation_result
    )

    return validation_result, severity_result


def test_good():

    validation_result, severity_result = (
        create_pipeline_data(
            aqi=40
        )
    )

    result = generate_health_guidance(
        validation_result,
        severity_result
    )

    print_result(
        "GOOD AQI TEST",
        result
    )


def test_moderate():

    validation_result, severity_result = (
        create_pipeline_data(
            aqi=144,
            pm25=144,
            pm10=85,
            no2=9.6,
            so2=4.3,
            co=12.2,
            o3=19.6
        )
    )

    result = generate_health_guidance(
        validation_result,
        severity_result
    )

    print_result(
        "MODERATE AQI TEST",
        result
    )


def test_very_poor():

    validation_result, severity_result = (
        create_pipeline_data(
            aqi=350,
            pm25=200,
            pm10=300,
            no2=250,
            so2=500,
            co=15,
            o3=180
        )
    )

    result = generate_health_guidance(
        validation_result,
        severity_result
    )

    print_result(
        "VERY POOR AQI TEST",
        result
    )


def test_severe():

    validation_result, severity_result = (
        create_pipeline_data(
            aqi=450,
            pm25=300,
            pm10=500,
            no2=450,
            so2=1700,
            co=40,
            o3=800
        )
    )

    result = generate_health_guidance(
        validation_result,
        severity_result
    )

    print_result(
        "SEVERE AQI TEST",
        result
    )


def test_invalid_data():

    validation_result = {
        "valid": False,
        "data": {
            "location": "Delhi",
            "aqi": None,
            "pollutants": {},
            "timestamp": None
        },
        "errors": [
            "AQI is missing."
        ]
    }

    severity_result = {
        "severity": None,
        "aqi": None,
        "severity_reason": (
            "Severity cannot be determined."
        ),
        "pollutant_conditions": []
    }

    result = generate_health_guidance(
        validation_result,
        severity_result
    )

    print_result(
        "INVALID DATA TEST",
        result
    )


def test_live_integration():

    waqi_result = get_aqi_data(
        "Delhi"
    )

    validation_result = validate_aqi_data(
        waqi_result
    )

    severity_result = determine_severity(
        validation_result
    )

    health_result = generate_health_guidance(
        validation_result,
        severity_result
    )

    print_result(
        "LIVE WAQI -> VALIDATION -> SEVERITY -> GUIDANCE",
        health_result
    )


if __name__ == "__main__":

    test_good()
    test_moderate()
    test_very_poor()
    test_severe()
    test_invalid_data()
    test_live_integration()