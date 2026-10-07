from app import aqi_pipeline


def print_result(title, result):

    print()
    print("=" * 65)
    print(title)
    print("=" * 65)

    print("Success:", result["success"])
    print("Location:", result["location"])
    print("AQI:", result["aqi"])

    print("Pollutants:")

    for name, value in result["pollutants"].items():
        print(f"  {name}: {value}")

    print("Severity:", result["severity"])
    print("Severity Reason:", result["severity_reason"])
    print("Urgency:", result["urgency"])

    print("Guidance:")

    if result["guidance"]:

        for item in result["guidance"]:
            print(" -", item)

    else:
        print(" None")

    print("Errors:")

    if result["errors"]:

        for error in result["errors"]:
            print(" -", error)

    else:
        print(" None")


# ============================================================
# 1. VALID LOCATION TEST
# ============================================================

def test_valid_location():

    result = aqi_pipeline.get_aqi_advisory(
        "Delhi"
    )

    print_result(
        "VALID LOCATION TEST",
        result
    )


# ============================================================
# 2. INVALID LOCATION TEST
# ============================================================

def test_invalid_location():

    result = aqi_pipeline.get_aqi_advisory(
        ""
    )

    print_result(
        "INVALID LOCATION TEST",
        result
    )


# ============================================================
# 3. MISSING POLLUTANT TEST
# ============================================================

def test_missing_pollutant():

    original_function = (
        aqi_pipeline.get_aqi_data
    )

    def fake_waqi_result(location):

        return {
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

    try:

        aqi_pipeline.get_aqi_data = (
            fake_waqi_result
        )

        result = aqi_pipeline.get_aqi_advisory(
            "Delhi"
        )

        print_result(
            "MISSING POLLUTANT TEST",
            result
        )

    finally:

        aqi_pipeline.get_aqi_data = (
            original_function
        )


# ============================================================
# 4. API FAILURE TEST
# ============================================================

def test_api_failure():

    original_function = (
        aqi_pipeline.get_aqi_data
    )

    def fake_api_failure(location):

        return {
            "success": False,
            "location": None,
            "aqi": None,
            "pollutants": {
                "pm25": None,
                "pm10": None,
                "no2": None,
                "so2": None,
                "co": None,
                "o3": None
            },
            "timestamp": None,
            "error": "WAQI API error: Invalid key"
        }

    try:

        aqi_pipeline.get_aqi_data = (
            fake_api_failure
        )

        result = aqi_pipeline.get_aqi_advisory(
            "Delhi"
        )

        print_result(
            "API FAILURE TEST",
            result
        )

    finally:

        aqi_pipeline.get_aqi_data = (
            original_function
        )


# ============================================================
# RUN ALL TESTS
# ============================================================

if __name__ == "__main__":

    test_valid_location()
    test_invalid_location()
    test_missing_pollutant()
    test_api_failure()