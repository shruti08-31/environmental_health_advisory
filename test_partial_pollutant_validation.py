
from pprint import pprint

from app.validator import validate_aqi_data


sample_data = {
    "success": True,
    "location": "Mumbai",
    "aqi": 85,
    "timestamp": "2026-11-23 16:00:00",

    "pollutants": {
        "pm25": 85,
        "pm10": None,
        "no2": 12,
        "so2": 3,
        "co": None,
        "o3": 20
    }
}


result = validate_aqi_data(sample_data)

print("\n========== VALIDATION RESULT ==========")
pprint(result)

print("\n========== VALIDITY ==========")
print(result["valid"])

print("\n========== VALIDATED AQI ==========")
print(result["data"]["aqi"])

print("\n========== VALIDATED POLLUTANTS ==========")
pprint(result["data"]["pollutants"])

print("\n========== CRITICAL ERRORS ==========")
pprint(result["errors"])

print("\n========== WARNINGS ==========")
pprint(result["warnings"])
