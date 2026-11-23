
import json
import math
import sqlite3

from datetime import datetime, timezone
from numbers import Real
from pathlib import Path
from zoneinfo import ZoneInfo

from app.waqi_client import get_aqi_data
from app.validator import validate_aqi_data


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "aqi_monitoring.db"

LOCAL_TIMEZONE = "Asia/Kolkata"

MAX_READING_AGE_HOURS = 24

POLLUTANT_NAMES = [
    "pm25",
    "pm10",
    "no2",
    "so2",
    "co",
    "o3"
]

EXPECTED_FIELDS = [
    "aqi",
    "pm25",
    "pm10",
    "no2",
    "so2",
    "co",
    "o3"
]


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_monitoring_connection():

    connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row

    return connection


# --------------------------------------------------
# CREATE MONITORING TABLE
# --------------------------------------------------

def create_monitoring_table():

    connection = get_monitoring_connection()

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_quality_log (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            location TEXT NOT NULL,

            request_status TEXT NOT NULL,

            data_available INTEGER NOT NULL,

            data_completeness REAL NOT NULL,

            missing_pollutants TEXT,

            invalid_fields TEXT,

            is_stale INTEGER NOT NULL,

            last_updated TEXT,

            warnings TEXT,

            status TEXT NOT NULL,

            checked_at TEXT NOT NULL,

            error_message TEXT

        )
    """)

    connection.commit()

    connection.close()


# --------------------------------------------------
# CURRENT TIMESTAMP
# --------------------------------------------------

def get_current_timestamp():

    current_time = datetime.now(
        ZoneInfo(LOCAL_TIMEZONE)
    )

    return current_time.isoformat(timespec="seconds")


# --------------------------------------------------
# NUMERIC VALIDATION
# --------------------------------------------------

def get_field_value(data, field):
    """Read AQI or a pollutant from the validated data."""

    if field == "aqi":
        return field in data, data.get(field)

    pollutants = data.get("pollutants", {})

    if isinstance(pollutants, dict) and field in pollutants:
        return True, pollutants.get(field)

    # Support a flat structure too, if another caller uses it.
    if field in data:
        return True, data.get(field)

    return False, None



def convert_number(value):

    if isinstance(value, bool):
        return None

    if not isinstance(value, Real):
        return None

    number = float(value)

    if not math.isfinite(number):
        return None

    if number < 0:
        return None

    return number


# --------------------------------------------------
# API REQUEST STATUS
# --------------------------------------------------

def check_api_request_status(api_result):

    """
    Determine whether the WAQI request returned
    a successful API response.

    This is separate from data quality validation.
    """

    if not isinstance(api_result, dict):
        return False

    if api_result.get("success") is False:
        return False

    if api_result.get("status") == "error":
        return False

    return True


# --------------------------------------------------
# TIMESTAMP FRESHNESS
# --------------------------------------------------

def check_timestamp_freshness(timestamp):

    """
    Check whether the AQI reading is within
    the configured freshness period.

    Returns:
        is_stale, timestamp_warning
    """

    if not isinstance(timestamp, str) or not timestamp.strip():

        return False, "Reading timestamp is missing."

    try:

        reading_time = datetime.fromisoformat(
            timestamp.strip().replace("Z", "+00:00")
        )

        local_timezone = ZoneInfo(LOCAL_TIMEZONE)

        if reading_time.tzinfo is None:

            reading_time = reading_time.replace(
                tzinfo=local_timezone
            )

        else:

            reading_time = reading_time.astimezone(
                local_timezone
            )

        current_time = datetime.now(
            local_timezone
        )

        age = current_time - reading_time

        if age.total_seconds() < -300:

            return True, (
                "Reading timestamp is in the future."
            )

        if age.total_seconds() < 0:

            return False, None

        if age.total_seconds() > MAX_READING_AGE_HOURS * 3600:

            return True, (
                f"Reading is older than "
                f"{MAX_READING_AGE_HOURS} hours."
            )

        return False, None

    except (ValueError, TypeError, OverflowError):

        return False, (
            "Reading timestamp has an invalid format."
        )


# --------------------------------------------------
# DATA QUALITY EVALUATION
# --------------------------------------------------

def evaluate_data_quality(
    location,
    validation_result,
    request_status=True
):

    """
    Evaluate the completeness and reliability
    of the validated AQI information.

    This function does not modify the original data.
    """

    warnings = []

    missing_pollutants = []

    invalid_fields = []

    data_available = False

    is_stale = False

    last_updated = None

    data = {}

    # --------------------------------------------------
    # 1. CHECK VALIDATION RESULT
    # --------------------------------------------------

    if isinstance(validation_result, dict):

        validated_data = validation_result.get("data")

        if isinstance(validated_data, dict):

            data = validated_data

            data_available = bool(request_status)

    # --------------------------------------------------
    # 2. HANDLE UNAVAILABLE DATA
    # --------------------------------------------------

    if not data_available:

        missing_pollutants = POLLUTANT_NAMES.copy()

        warnings.append(
            "AQI data is unavailable."
        )

        completeness = 0.0

        status = "UNAVAILABLE"

        if not request_status:

            warnings.append(
                "WAQI API request failed."
            )

        elif isinstance(validation_result, dict):

            validation_errors = validation_result.get(
                "errors",
                []
            )

            if validation_errors:

                warnings.extend(
                    str(error)
                    for error in validation_errors
                )

        return {
            "location": location,
            "data_available": False,
            "data_completeness": completeness,
            "missing_pollutants": missing_pollutants,
            "invalid_fields": invalid_fields,
            "is_stale": False,
            "last_updated": None,
            "warnings": warnings,
            "status": status
        }

    # --------------------------------------------------
    # 3. CHECK AQI AND POLLUTANT VALUES
    # --------------------------------------------------

   
    valid_field_count = 0

    for field in EXPECTED_FIELDS:

        field_exists, value = get_field_value(
            data,
            field
        )

        if not field_exists or value is None:

            if field in POLLUTANT_NAMES:

                missing_pollutants.append(field)

                warnings.append(
                    f"Pollutant reading '{field}' is missing."
                )

            else:

                warnings.append(
                    "AQI value is missing."
                )

            continue

        number = convert_number(value)

        if number is None:

            invalid_fields.append(field)

            warnings.append(
                f"Field '{field}' contains an invalid numerical value."
            )

            continue

        valid_field_count += 1


    # --------------------------------------------------
    # 4. CALCULATE COMPLETENESS
    # --------------------------------------------------

    completeness = round(
        (valid_field_count / len(EXPECTED_FIELDS)) * 100,
        1
    )

    # --------------------------------------------------
    # 5. CHECK TIMESTAMP
    # --------------------------------------------------

    last_updated = data.get("timestamp")

    is_stale, timestamp_warning = (
        check_timestamp_freshness(last_updated)
    )

    if timestamp_warning:

        warnings.append(timestamp_warning)

    # --------------------------------------------------
    # 6. CHECK VALIDATION WARNINGS
    # --------------------------------------------------

    validation_errors = validation_result.get(
        "errors",
        []
    )

    if validation_errors:

        warnings.extend(
            str(error)
            for error in validation_errors
        )

    # --------------------------------------------------
    # 7. DETERMINE DATA QUALITY STATUS
    # --------------------------------------------------

    if not request_status:

        status = "UNAVAILABLE"

    elif is_stale:

        status = "CRITICAL"

    elif "aqi" in invalid_fields:

        status = "CRITICAL"

    elif completeness < 100 or invalid_fields:

        status = "WARNING"

    elif timestamp_warning:

        status = "WARNING"

    else:

        status = "GOOD"

    # --------------------------------------------------
    # 8. FINAL RESULT
    # --------------------------------------------------

    return {
        "location": location,
        "data_available": data_available,
        "data_completeness": completeness,
        "missing_pollutants": missing_pollutants,
        "invalid_fields": invalid_fields,
        "is_stale": is_stale,
        "last_updated": last_updated,
        "warnings": warnings,
        "status": status
    }


# --------------------------------------------------
# SAVE MONITORING LOG
# --------------------------------------------------

def save_monitoring_log(
    quality_result,
    request_status,
    error_message=None
):

    create_monitoring_table()

    connection = get_monitoring_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO data_quality_log (

            location,
            request_status,
            data_available,
            data_completeness,
            missing_pollutants,
            invalid_fields,
            is_stale,
            last_updated,
            warnings,
            status,
            checked_at,
            error_message

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

    """, (

        quality_result["location"],

        "SUCCESS" if request_status else "FAILED",

        int(quality_result["data_available"]),

        quality_result["data_completeness"],

        json.dumps(
            quality_result["missing_pollutants"]
        ),

        json.dumps(
            quality_result["invalid_fields"]
        ),

        int(quality_result["is_stale"]),

        quality_result["last_updated"],

        json.dumps(
            quality_result["warnings"]
        ),

        quality_result["status"],

        get_current_timestamp(),

        error_message

    ))

    connection.commit()

    connection.close()


# --------------------------------------------------
# MAIN MONITORING FUNCTION
# --------------------------------------------------

def monitor_aqi_data(location):

    """
    Fetch AQI data, validate it, evaluate data quality,
    and save the monitoring result in SQLite.
    """

    if not isinstance(location, str) or not location.strip():

        return {
            "location": location,
            "data_available": False,
            "data_completeness": 0.0,
            "missing_pollutants": POLLUTANT_NAMES.copy(),
            "invalid_fields": [],
            "is_stale": False,
            "last_updated": None,
            "warnings": [
                "A valid location is required."
            ],
            "status": "UNAVAILABLE"
        }

    location = location.strip()

    create_monitoring_table()

    api_result = None

    request_status = False

    error_message = None

    validation_result = None

    # --------------------------------------------------
    # 1. FETCH WAQI DATA
    # --------------------------------------------------

    try:

        api_result = get_aqi_data(location)

        request_status = check_api_request_status(
            api_result
        )

        if not request_status:

            error_message = (
                "WAQI API request did not return a successful response."
            )

    except Exception as error:

        request_status = False

        error_message = str(error)

    # --------------------------------------------------
    # 2. REUSE EXISTING VALIDATOR
    # --------------------------------------------------

    if request_status:

        try:

            validation_result = validate_aqi_data(
                api_result
            )

        except Exception as error:

            validation_result = {
                "valid": False,
                "data": None,
                "errors": [
                    f"Validation failed: {str(error)}"
                ]
            }

            error_message = str(error)

    # --------------------------------------------------
    # 3. EVALUATE DATA QUALITY
    # --------------------------------------------------

    quality_result = evaluate_data_quality(
        location,
        validation_result,
        request_status
    )

    # --------------------------------------------------
    # 4. SAVE MONITORING LOG
    # --------------------------------------------------

    save_monitoring_log(
        quality_result,
        request_status,
        error_message
    )

    return quality_result


# --------------------------------------------------
# GET MONITORING HISTORY
# --------------------------------------------------

def get_monitoring_history(
    location=None,
    limit=100
):

    create_monitoring_table()

    connection = get_monitoring_connection()

    cursor = connection.cursor()

    query = """
        SELECT *
        FROM data_quality_log
    """

    parameters = []

    if location:

        query += """
            WHERE location = ?
        """

        parameters.append(location)

    query += """
        ORDER BY id DESC
        LIMIT ?
    """

    parameters.append(limit)

    cursor.execute(
        query,
        parameters
    )

    rows = cursor.fetchall()

    connection.close()

    history = []

    for row in rows:

        item = dict(row)

        item["missing_pollutants"] = json.loads(
            item["missing_pollutants"] or "[]"
        )

        item["invalid_fields"] = json.loads(
            item["invalid_fields"] or "[]"
        )

        item["warnings"] = json.loads(
            item["warnings"] or "[]"
        )

        item["data_available"] = bool(
            item["data_available"]
        )

        item["is_stale"] = bool(
            item["is_stale"]
        )

        history.append(item)

    return history


# --------------------------------------------------
# REQUEST STATISTICS
# --------------------------------------------------

def get_request_statistics(location=None):

    create_monitoring_table()

    connection = get_monitoring_connection()

    cursor = connection.cursor()

    query = """
        SELECT
            COUNT(*) AS total_requests,

            SUM(
                CASE
                    WHEN request_status = 'SUCCESS'
                    THEN 1
                    ELSE 0
                END
            ) AS successful_requests,

            SUM(
                CASE
                    WHEN request_status = 'FAILED'
                    THEN 1
                    ELSE 0
                END
            ) AS failed_requests,

            AVG(data_completeness) AS average_completeness

        FROM data_quality_log
    """

    parameters = []

    if location:

        query += """
            WHERE location = ?
        """

        parameters.append(location)

    cursor.execute(
        query,
        parameters
    )

    row = cursor.fetchone()

    connection.close()

    total = row["total_requests"] or 0

    successful = row["successful_requests"] or 0

    failed = row["failed_requests"] or 0

    average = row["average_completeness"]

    return {
        "total_requests": total,
        "successful_requests": successful,
        "failed_requests": failed,
        "average_completeness": (
            round(average, 1)
            if average is not None
            else 0.0
        )
    }
