import requests

from app.config import settings


WAQI_BASE_URL = "https://api.waqi.info/feed"


def _get_pollutant(iaqi, name):
    """
    Safely extract a pollutant value from the WAQI response.

    Returns None when the pollutant is not available or
    the value is malformed.
    """

    pollutant = iaqi.get(name)

    if not isinstance(pollutant, dict):
        return None

    value = pollutant.get("v")

    if value is None:
        return None

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _create_error_response(message):
    """
    Create the standard failed response.
    """

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
        "error": message
    }


def get_aqi_data(location):
    """
    Fetch current AQI and pollutant data from WAQI.

    Parameters:
        location (str): City or location name.

    Returns:
        dict: Standardized AQI response.
    """

    # --------------------------------------------------
    # 1. Validate location
    # --------------------------------------------------

    if not isinstance(location, str):
        return _create_error_response(
            "Location must be a string."
        )

    location = location.strip()

    if not location:
        return _create_error_response(
            "Location cannot be empty."
        )

    # --------------------------------------------------
    # 2. Check API key
    # --------------------------------------------------

    if not settings.waqi_api_key:
        return _create_error_response(
            "WAQI API key is not configured."
        )

    # --------------------------------------------------
    # 3. Build WAQI URL
    # --------------------------------------------------

    url = f"{WAQI_BASE_URL}/{location}/"

    params = {
        "token": settings.waqi_api_key
    }

    # --------------------------------------------------
    # 4. Call WAQI API
    # --------------------------------------------------

    try:
        response = requests.get(
            url,
            params=params,
            timeout=settings.request_timeout
        )

    except requests.exceptions.Timeout:
        return _create_error_response(
            "WAQI API request timed out."
        )

    except requests.exceptions.ConnectionError:
        return _create_error_response(
            "Could not connect to the WAQI API."
        )

    except requests.exceptions.RequestException as error:
        return _create_error_response(
            f"WAQI API request failed: {error}"
        )

    # --------------------------------------------------
    # 5. Check HTTP response
    # --------------------------------------------------

    if response.status_code != 200:
        return _create_error_response(
            f"WAQI API returned HTTP status "
            f"{response.status_code}."
        )

    # --------------------------------------------------
    # 6. Parse JSON
    # --------------------------------------------------

    try:
        result = response.json()

    except ValueError:
        return _create_error_response(
            "WAQI returned malformed JSON."
        )

    # --------------------------------------------------
    # 7. Validate top-level response
    # --------------------------------------------------

    if not isinstance(result, dict):
        return _create_error_response(
            "WAQI response has an invalid format."
        )

    if result.get("status") != "ok":
        api_error = result.get(
            "data",
            "WAQI API returned an error."
        )

        return _create_error_response(
            f"WAQI API error: {api_error}"
        )

    # --------------------------------------------------
    # 8. Get data section
    # --------------------------------------------------

    data = result.get("data")

    if not isinstance(data, dict):
        return _create_error_response(
            "WAQI response is missing the data section."
        )

    # --------------------------------------------------
    # 9. Get AQI
    # --------------------------------------------------

    raw_aqi = data.get("aqi")

    if raw_aqi is None:
        return _create_error_response(
            "AQI is missing from the WAQI response."
        )

    try:
        aqi = float(raw_aqi)

    except (ValueError, TypeError):
        return _create_error_response(
            "AQI value in the WAQI response is invalid."
        )

    # --------------------------------------------------
    # 10. Get location
    # --------------------------------------------------

    city_data = data.get("city")

    if not isinstance(city_data, dict):
        return _create_error_response(
            "Location information is missing from "
            "the WAQI response."
        )

    returned_location = city_data.get("name")

    if not returned_location:
        return _create_error_response(
            "Location name is missing from the "
            "WAQI response."
        )

    # --------------------------------------------------
    # 11. Get pollutants
    # --------------------------------------------------

    iaqi = data.get("iaqi", {})

    if not isinstance(iaqi, dict):
        iaqi = {}

    pollutants = {
        "pm25": _get_pollutant(iaqi, "pm25"),
        "pm10": _get_pollutant(iaqi, "pm10"),
        "no2": _get_pollutant(iaqi, "no2"),
        "so2": _get_pollutant(iaqi, "so2"),
        "co": _get_pollutant(iaqi, "co"),
        "o3": _get_pollutant(iaqi, "o3")
    }

    # --------------------------------------------------
    # 12. Get timestamp when available
    # --------------------------------------------------

    timestamp = None

    time_data = data.get("time")

    if isinstance(time_data, dict):
        timestamp = time_data.get("s")

    # --------------------------------------------------
    # 13. Return standardized response
    # --------------------------------------------------

    return {
        "success": True,
        "location": returned_location,
        "aqi": aqi,
        "pollutants": pollutants,
        "timestamp": timestamp,
        "error": None
    }