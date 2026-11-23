
import pandas as pd

from app.aqi_pipeline import get_aqi_advisory


POLLUTANTS = [
    "pm25",
    "pm10",
    "no2",
    "so2",
    "co",
    "o3"
]

MAX_READING_AGE_HOURS = 24
LOCAL_TIMEZONE = "Asia/Kolkata"


def convert_number(value):
    """Convert a value into a valid number."""

    if value is None:
        return None

    try:
        number = float(value)

        if pd.isna(number):
            return None

        return number

    except (ValueError, TypeError):
        return None


def parse_timestamp(value):
    """Parse timestamps using Indian local time when timezone is absent."""

    if value is None:
        return pd.NaT

    try:
        timestamp = pd.Timestamp(value)

        if pd.isna(timestamp):
            return pd.NaT

        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize(LOCAL_TIMEZONE)
        else:
            timestamp = timestamp.tz_convert(LOCAL_TIMEZONE)

        return timestamp

    except (ValueError, TypeError):
        return pd.NaT


def get_highest_pollutant(pollutants):
    """Find the pollutant with the highest available numerical value."""

    values = {}

    if not isinstance(pollutants, dict):
        return None, None

    for pollutant in POLLUTANTS:

        value = convert_number(
            pollutants.get(pollutant)
        )

        if value is not None:
            values[pollutant] = value

    if not values:
        return None, None

    highest_value = max(values.values())

    highest_pollutants = [
        name
        for name, value in values.items()
        if value == highest_value
    ]

    return ", ".join(highest_pollutants), highest_value


def fetch_location_data(location):
    """Fetch and standardize AQI information for one location."""

    try:

        result = get_aqi_advisory(location)

        if not isinstance(result, dict):
            raise ValueError("Invalid pipeline response.")

        if not result.get("success"):

            errors = result.get("errors", [])

            return {
                "success": False,
                "location": location,
                "error": str(errors or "AQI reading unavailable.")
            }

        pollutants = result.get("pollutants", {})

        if not isinstance(pollutants, dict):
            pollutants = {}

        aqi = convert_number(
            result.get("aqi")
        )

        if aqi is None:

            return {
                "success": False,
                "location": location,
                "error": "AQI value unavailable."
            }

        highest_pollutant, highest_value = (
            get_highest_pollutant(pollutants)
        )

        row = {
            "location": result.get("location") or location,
            "success": True,
            "aqi": aqi,
            "severity": result.get("severity"),
            "timestamp": result.get("timestamp"),
            "highest_pollutant": highest_pollutant,
            "highest_pollutant_value": highest_value,
            "error": None
        }

        for pollutant in POLLUTANTS:

            row[pollutant] = convert_number(
                pollutants.get(pollutant)
            )

        return row

    except Exception as error:

        return {
            "success": False,
            "location": location,
            "error": str(error)
        }


def calculate_comparison_insights(df):
    """Calculate insights using fresh readings only."""

    if "reading_status" in df.columns:

        available = df[
            (df["success"] == True)
            & (df["reading_status"] == "Fresh")
        ].copy()

    else:

        available = df[
            df["success"] == True
        ].copy()

    successful_count = int(
        df["success"].sum()
    )

    fresh_count = len(available)

    outdated_count = 0
    timestamp_missing_count = 0

    if "reading_status" in df.columns:

        outdated_count = int(
            (df["reading_status"] == "Outdated").sum()
        )

        timestamp_missing_count = int(
            (df["reading_status"] == "Timestamp unavailable").sum()
        )

    insights = {
        "fetched_locations": successful_count,
        "available_locations": fresh_count,
        "outdated_locations": outdated_count,
        "timestamp_unavailable_locations": timestamp_missing_count,
        "unavailable_locations": len(df) - successful_count,
        "lowest_aqi_location": None,
        "lowest_aqi": None,
        "highest_aqi_location": None,
        "highest_aqi": None,
        "average_aqi": None
    }

    if available.empty:
        return insights

    lowest_aqi = available["aqi"].min()
    highest_aqi = available["aqi"].max()

    lowest_locations = available.loc[
        available["aqi"] == lowest_aqi,
        "location"
    ].tolist()

    highest_locations = available.loc[
        available["aqi"] == highest_aqi,
        "location"
    ].tolist()

    insights.update({
        "lowest_aqi_location": lowest_locations,
        "lowest_aqi": float(lowest_aqi),

        "highest_aqi_location": highest_locations,
        "highest_aqi": float(highest_aqi),

        "average_aqi": round(
            float(available["aqi"].mean()),
            2
        )
    })

    return insights


def check_timestamp_difference(df, tolerance_minutes=15):
    """Compare timestamps of fresh readings only."""

    if "reading_status" in df.columns:

        available = df[
            (df["success"] == True)
            & (df["reading_status"] == "Fresh")
        ].copy()

    else:

        available = df[
            df["success"] == True
        ].copy()

    if available.empty:

        return {
            "timestamp_status": "unavailable",
            "time_difference_minutes": None,
            "message": "No fresh readings are available for timestamp comparison."
        }

    valid_times = available["parsed_timestamp"].dropna()

    if len(valid_times) != len(available):

        return {
            "timestamp_status": "incomplete",
            "time_difference_minutes": None,
            "message": "One or more fresh readings have missing or invalid timestamps."
        }

    if len(valid_times) <= 1:

        return {
            "timestamp_status": "single_reading",
            "time_difference_minutes": 0.0,
            "message": "Only one fresh location reading is available."
        }

    time_difference = (
        valid_times.max() - valid_times.min()
    ).total_seconds() / 60

    if time_difference <= tolerance_minutes:

        status = "within_tolerance"

        message = (
            "Fresh readings were collected within the allowed "
            "time difference."
        )

    else:

        status = "different_times"

        message = (
            "Fresh readings were collected at different times. "
            "Compare AQI values with caution."
        )

    return {
        "timestamp_status": status,
        "time_difference_minutes": round(
            time_difference, 2
        ),
        "message": message
    }


def compare_locations(locations, tolerance_minutes=15):
    """
    Compare AQI readings across multiple locations.

    Only readings from the last 24 hours are included in
    current AQI statistics.

    Outdated readings remain visible in the comparison table.
    """

    if not isinstance(locations, (list, tuple)):
        raise ValueError("Locations must be provided as a list.")

    if len(locations) == 0:
        raise ValueError("At least one location is required.")

    if (
        isinstance(tolerance_minutes, bool)
        or not isinstance(tolerance_minutes, (int, float))
        or tolerance_minutes < 0
    ):
        raise ValueError("Tolerance must be a non-negative number.")

    # Validate and remove duplicate locations.
    unique_locations = []
    seen = set()

    for location in locations:

        if not isinstance(location, str) or not location.strip():
            raise ValueError("Every location must be a non-empty string.")

        location = location.strip()
        key = location.casefold()

        if key not in seen:
            unique_locations.append(location)
            seen.add(key)

    # Fetch data independently for every location.
    records = []

    for location in unique_locations:

        result = fetch_location_data(location)

        if not result.get("success"):

            record = {
                "location": location,
                "success": False,
                "aqi": None,
                "severity": None,
                "timestamp": None,
                "highest_pollutant": None,
                "highest_pollutant_value": None,
                "error": result.get("error")
            }

            for pollutant in POLLUTANTS:
                record[pollutant] = None

            records.append(record)

        else:
            records.append(result)

    # Create standardized comparison dataset.
    df = pd.DataFrame(records)

    # Parse timestamps in Indian local time.
    df["parsed_timestamp"] = df["timestamp"].apply(
        parse_timestamp
    )

    # Determine reading freshness.
    current_time = pd.Timestamp.now(
        tz=LOCAL_TIMEZONE
    )

    def get_reading_status(row):

        if not row["success"]:
            return "Unavailable"

        timestamp = row["parsed_timestamp"]

        if pd.isna(timestamp):
            return "Timestamp unavailable"

        age_hours = (
            current_time - timestamp
        ).total_seconds() / 3600

        if age_hours < 0:
            return "Future timestamp"

        if age_hours > MAX_READING_AGE_HOURS:
            return "Outdated"

        return "Fresh"

    df["reading_status"] = df.apply(
        get_reading_status,
        axis=1
    )

    # Calculate relative timestamp status.
    fresh_rows = df[
        df["reading_status"] == "Fresh"
    ]

    if not fresh_rows.empty:

        latest_timestamp = fresh_rows[
            "parsed_timestamp"
        ].max()

    else:
        latest_timestamp = pd.NaT

    def get_time_status(row):

        timestamp = row["parsed_timestamp"]

        if not row["success"]:
            return "Reading unavailable"

        if pd.isna(timestamp):
            return "Timestamp unavailable"

        if row["reading_status"] == "Outdated":
            return "Outdated reading"

        if row["reading_status"] == "Future timestamp":
            return "Future timestamp"

        if pd.isna(latest_timestamp):
            return "No fresh comparison available"

        difference = (
            latest_timestamp - timestamp
        ).total_seconds() / 60

        if difference == 0:
            return "Latest reading"

        return f"{round(difference, 2)} minutes older"

    df["time_status"] = df.apply(
        get_time_status,
        axis=1
    )

    # Calculate insights using fresh readings only.
    insights = calculate_comparison_insights(df)

    timestamp_info = check_timestamp_difference(
        df,
        tolerance_minutes
    )

    insights.update(timestamp_info)

    # Remove internal timestamp column.
    df = df.drop(
        columns=["parsed_timestamp"]
    )

    return {
        "success": insights["available_locations"] > 0,
        "comparison_data": df,
        "insights": insights,
        "errors": df.loc[
            df["success"] == False,
            ["location", "error"]
        ].to_dict("records")
    }
