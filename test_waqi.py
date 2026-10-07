from app.waqi_client import get_aqi_data


def print_result(result):
    print()
    print("Success:", result["success"])
    print("Location:", result["location"])
    print("AQI:", result["aqi"])

    print("Pollutants:")
    for name, value in result["pollutants"].items():
        print(f"  {name}: {value}")

    print("Timestamp:", result["timestamp"])
    print("Error:", result["error"])


def test_success():
    """
    Test a real WAQI request.
    """

    result = get_aqi_data("Delhi")

    print("=== SUCCESS TEST ===")
    print_result(result)


def test_invalid_location():
    """
    Test invalid location input.
    """

    result = get_aqi_data("")

    print()
    print("=== INVALID LOCATION TEST ===")
    print_result(result)


from app.config import settings

print("WAQI key loaded:", bool(settings.waqi_api_key))
print("WAQI key length:", len(settings.waqi_api_key))

if __name__ == "__main__":
    test_success()
    test_invalid_location()

