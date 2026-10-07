from app.config import settings
from app.models import PollutantData, AQIData, APIResponse


def main():

    print("=== Environmental Health Advisory System ===")
    print()

    # Test configuration
    print("Application:", settings.app_name)
    print("Default location:", settings.default_location)
    print("Request timeout:", settings.request_timeout)

    # Do not print actual API keys.
    print(
        "WAQI API key configured:",
        bool(settings.waqi_api_key)
    )

    print(
        "LLM API key configured:",
        bool(settings.llm_api_key)
    )

    # Test common data structure
    pollutants = PollutantData(
        pm25=45.5,
        pm10=82.0,
        no2=31.2,
        so2=8.4,
        co=0.7,
        o3=24.1
    )

    aqi_data = AQIData(
        location="Delhi",
        aqi=164,
        pollutants=pollutants,
        timestamp="2026-10-07T15:00:00",
        source="WAQI"
    )

    response = APIResponse(
        success=True,
        data=aqi_data,
        message="Foundation test successful."
    )

    print()
    print("=== Common Data Structure ===")
    print("Success:", response.success)
    print("Location:", response.data.location)
    print("AQI:", response.data.aqi)
    print("PM2.5:", response.data.pollutants.pm25)
    print("PM10:", response.data.pollutants.pm10)
    print("Source:", response.data.source)
    print("Message:", response.message)

    print()
    print("Foundation test completed successfully.")


if __name__ == "__main__":
    main()