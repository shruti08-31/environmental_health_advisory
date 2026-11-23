from datetime import datetime
from zoneinfo import ZoneInfo

from app.aqi_pipeline import get_aqi_advisory
from app.history.database import (
    get_connection,
    create_history_table,
    get_aqi_history,
    save_aqi_reading
)


ALERT_TYPES = [
    "AQI threshold exceeded",
    "AQI increased significantly",
    "Unhealthy air-quality condition",
    "Sensitive-group precaution",
    "Data unavailable"
]

DEFAULT_AQI_THRESHOLD = 100
DEFAULT_AQI_INCREASE = 50
MAX_READING_AGE_HOURS = 24

UNHEALTHY_SEVERITIES = [
    "poor",
    "very poor",
    "severe"
]

SENSITIVE_SEVERITIES = [
    "moderately polluted",
    "poor",
    "very poor",
    "severe"
]

LOCAL_TIMEZONE = "Asia/Kolkata"


def get_current_timestamp():
    """Return the current Indian local timestamp."""

    return datetime.now(
        ZoneInfo(LOCAL_TIMEZONE)
    ).strftime("%Y-%m-%d %H:%M:%S")
def check_reading_freshness(timestamp):
    """Check whether an AQI measurement is recent enough for alerts."""

    if not timestamp:
        return False, "Timestamp unavailable"

    try:
        reading_time = datetime.fromisoformat(timestamp)

        if reading_time.tzinfo is None:
            reading_time = reading_time.replace(
                tzinfo=ZoneInfo(LOCAL_TIMEZONE)
            )
        else:
            reading_time = reading_time.astimezone(
                ZoneInfo(LOCAL_TIMEZONE)
            )

        current_time = datetime.now(
            ZoneInfo(LOCAL_TIMEZONE)
        )

        age_hours = (
            current_time - reading_time
        ).total_seconds() / 3600

        if age_hours < 0:
            return False, "Future timestamp"

        if age_hours > MAX_READING_AGE_HOURS:
            return False, "Outdated"

        return True, "Fresh"

    except (ValueError, TypeError):
        return False, "Invalid timestamp"




def initialize_alert_tables():
    """Create the SQLite tables required by the alert engine."""

    create_history_table()

    connection = get_connection()

    try:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS alert_rules (
                rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                threshold_value REAL,
                increase_value REAL,
                UNIQUE(location, alert_type)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id INTEGER NOT NULL,
                location TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL,
                aqi REAL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(rule_id)
                    REFERENCES alert_rules(rule_id)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS alert_state (
                location TEXT NOT NULL,
                rule_id INTEGER NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(location, rule_id),
                FOREIGN KEY(rule_id)
                    REFERENCES alert_rules(rule_id)
            )
        """)

        connection.commit()

    finally:
        connection.close()


def set_alert_rule(
    location,
    alert_type,
    enabled=True,
    threshold_value=None,
    increase_value=None
):
    """Create or update an individual alert rule."""

    if not isinstance(location, str) or not location.strip():
        raise ValueError("Location must be a non-empty string.")

    if alert_type not in ALERT_TYPES:
        raise ValueError("Unsupported alert type.")

    if not isinstance(enabled, bool):
        raise ValueError("Enabled must be True or False.")

    if alert_type == "AQI threshold exceeded":

        if threshold_value is None:
            threshold_value = DEFAULT_AQI_THRESHOLD

        if (
            isinstance(threshold_value, bool)
            or not isinstance(threshold_value, (int, float))
            or threshold_value < 0
        ):
            raise ValueError("AQI threshold must be a non-negative number.")

    if alert_type == "AQI increased significantly":

        if increase_value is None:
            increase_value = DEFAULT_AQI_INCREASE

        if (
            isinstance(increase_value, bool)
            or not isinstance(increase_value, (int, float))
            or increase_value <= 0
        ):
            raise ValueError("AQI increase must be a positive number.")

    initialize_alert_tables()

    connection = get_connection()

    try:

        connection.execute("""
            INSERT INTO alert_rules (
                location,
                alert_type,
                enabled,
                threshold_value,
                increase_value
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(location, alert_type)
            DO UPDATE SET
                enabled = excluded.enabled,
                threshold_value = excluded.threshold_value,
                increase_value = excluded.increase_value
        """, (
            location.strip(),
            alert_type,
            int(enabled),
            threshold_value,
            increase_value
        ))

        if not enabled:

            connection.execute("""
                UPDATE alert_state
                SET is_active = 0
                WHERE location = ?
                AND rule_id = (
                    SELECT rule_id
                    FROM alert_rules
                    WHERE location = ?
                    AND alert_type = ?
                )
            """, (
                location.strip(),
                location.strip(),
                alert_type
            ))

        connection.commit()

        return {
            "success": True,
            "message": "Alert rule saved successfully."
        }

    finally:
        connection.close()


def configure_default_alert_rules(
    locations,
    aqi_threshold=DEFAULT_AQI_THRESHOLD,
    increase_threshold=DEFAULT_AQI_INCREASE
):
    """Create all five default alert rules for each location."""

    if not isinstance(locations, (list, tuple)):
        raise ValueError("Locations must be a list.")

    if not locations:
        raise ValueError("At least one location is required.")

    results = []

    for location in locations:

        if not isinstance(location, str) or not location.strip():
            raise ValueError("Every location must be a non-empty string.")

        rules = [
            (
                "AQI threshold exceeded",
                True,
                aqi_threshold,
                None
            ),
            (
                "AQI increased significantly",
                True,
                None,
                increase_threshold
            ),
            (
                "Unhealthy air-quality condition",
                True,
                None,
                None
            ),
            (
                "Sensitive-group precaution",
                True,
                None,
                None
            ),
            (
                "Data unavailable",
                True,
                None,
                None
            )
        ]

        for alert_type, enabled, threshold, increase in rules:

            result = set_alert_rule(
                location,
                alert_type,
                enabled,
                threshold,
                increase
            )

            results.append({
                "location": location,
                "alert_type": alert_type,
                "success": result["success"]
            })

    return results


def get_alert_rules(location=None):
    """Retrieve configured alert rules."""

    initialize_alert_tables()

    connection = get_connection()

    try:

        if location is None:

            rows = connection.execute("""
                SELECT *
                FROM alert_rules
                ORDER BY location, rule_id
            """).fetchall()

        else:

            rows = connection.execute("""
                SELECT *
                FROM alert_rules
                WHERE location = ?
                ORDER BY rule_id
            """, (location,)).fetchall()

        columns = [
            "rule_id",
            "location",
            "alert_type",
            "enabled",
            "threshold_value",
            "increase_value"
        ]

        return [
            dict(zip(columns, row))
            for row in rows
        ]

    finally:
        connection.close()


def get_previous_reading(location, current_timestamp):
    """Retrieve the most recent stored reading before the current one."""

    history = get_aqi_history(location=location)

    if not history:
        return None

    previous_readings = []

    for reading in history:

        timestamp = reading.get("timestamp")

        if not timestamp:
            continue

        if current_timestamp and timestamp >= current_timestamp:
            continue

        aqi = reading.get("aqi")

        if aqi is None:
            continue

        previous_readings.append(reading)

    if not previous_readings:
        return None

    previous_readings.sort(
        key=lambda item: item["timestamp"]
    )

    return previous_readings[-1]


def get_alert_severity(aqi_severity):
    """Convert AQI severity into alert priority."""

    severity = str(aqi_severity or "").strip().casefold()

    if severity == "severe":
        return "Critical"

    if severity in ["poor", "very poor"]:
        return "High"

    if severity == "moderately polluted":
        return "Moderate"

    if severity == "satisfactory":
        return "Low"

    return "Informational"


def create_alert_message(
    alert_type,
    location,
    aqi,
    severity,
    previous_aqi=None,
    threshold_value=None
):
    """Generate deterministic alert messages."""

    if alert_type == "AQI threshold exceeded":

        return (
            f"AQI at {location} is {aqi}, "
            f"which has reached or exceeded the configured "
            f"threshold of {threshold_value}."
        )

    if alert_type == "AQI increased significantly":

        if previous_aqi is None:
            return (
                f"AQI at {location} is {aqi}, "
                "but no previous stored reading is available "
                "to calculate an increase."
            )

        increase = aqi - previous_aqi

        return (
            f"AQI at {location} increased from "
            f"{previous_aqi} to {aqi}, "
            f"an increase of {increase:.1f} points."
        )

    if alert_type == "Unhealthy air-quality condition":

        return (
            f"Unhealthy air quality detected at {location}. "
            f"Current AQI is {aqi} and the category is {severity}."
        )

    if alert_type == "Sensitive-group precaution":

        return (
            f"Precaution for children, older adults, and people "
            f"with existing lung or heart conditions at {location}. "
            f"Current AQI is {aqi} ({severity}). "
            f"Reduce prolonged outdoor exposure."
        )

    if alert_type == "Data unavailable":

        return (
            f"AQI monitoring failed for {location}. "
            f"A current AQI reading could not be retrieved."
        )

    return "AQI alert generated."


def record_alert_if_new(
    rule,
    condition,
    message,
    severity,
    aqi,
    timestamp
):
    """Store an alert only when its condition becomes active."""

    connection = get_connection()

    try:

        rule_id = rule["rule_id"]
        location = rule["location"]

        connection.execute("""
            INSERT OR IGNORE INTO alert_state (
                location,
                rule_id,
                is_active
            )
            VALUES (?, ?, 0)
        """, (
            location,
            rule_id
        ))

        state = connection.execute("""
            SELECT is_active
            FROM alert_state
            WHERE location = ?
            AND rule_id = ?
        """, (
            location,
            rule_id
        )).fetchone()

        is_active = bool(state[0]) if state else False

        # Reset state when the condition is no longer true.
        if not condition:

            connection.execute("""
                UPDATE alert_state
                SET is_active = 0
                WHERE location = ?
                AND rule_id = ?
            """, (
                location,
                rule_id
            ))

            connection.commit()
            return None

        # Do not create a duplicate alert.
        if is_active:
            connection.commit()
            return None

        connection.execute("""
            INSERT INTO alert_history (
                rule_id,
                location,
                alert_type,
                message,
                severity,
                aqi,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            rule_id,
            location,
            rule["alert_type"],
            message,
            severity,
            aqi,
            timestamp
        ))

        connection.execute("""
            UPDATE alert_state
            SET is_active = 1
            WHERE location = ?
            AND rule_id = ?
        """, (
            location,
            rule_id
        ))

        connection.commit()

        return {
            "location": location,
            "alert_type": rule["alert_type"],
            "message": message,
            "severity": severity,
            "aqi": aqi,
            "timestamp": timestamp
        }

    finally:
        connection.close()



def evaluate_location_alerts(location):
    """
    Fetch current AQI and evaluate configured alert rules.

    Only fresh readings are used to generate AQI condition alerts.
    Outdated or invalid readings generate a data-unavailable alert.
    """

    if not isinstance(location, str) or not location.strip():
        raise ValueError("Location must be a non-empty string.")

    location = location.strip()

    initialize_alert_tables()

    rules = get_alert_rules(location)

    if not rules:

        return {
            "success": False,
            "location": location,
            "alerts": [],
            "message": "No alert rules configured for this location."
        }

    result = get_aqi_advisory(location)

    if not isinstance(result, dict):
        result = {
            "success": False,
            "errors": ["Invalid AQI pipeline response."]
        }

    reading_timestamp = result.get("timestamp")

    # This is the time at which the alert evaluation takes place.
    alert_timestamp = get_current_timestamp()

    aqi = result.get("aqi")
    aqi_severity = result.get("severity")

    # Validate AQI.
    try:

        if isinstance(aqi, bool):
            raise ValueError()

        aqi = float(aqi)

        if aqi < 0:
            raise ValueError()

    except (ValueError, TypeError):

        aqi = None

    pipeline_success = (
        result.get("success") is True
        and aqi is not None
    )

    alerts = []

    # --------------------------------------------------
    # 1. Handle pipeline failure
    # --------------------------------------------------

    if not pipeline_success:

        error = result.get(
            "errors",
            ["AQI data unavailable."]
        )

        for rule in rules:

            is_data_rule = (
                rule["alert_type"] == "Data unavailable"
            )

            message = (
                f"AQI monitoring failed for {location}. "
                f"A current AQI reading could not be retrieved. "
                f"Details: {error}"
            )

            alert = record_alert_if_new(
                rule,
                is_data_rule and bool(rule["enabled"]),
                message,
                "High",
                None,
                alert_timestamp
            )

            if alert:
                alerts.append(alert)

        return {
            "success": False,
            "location": location,
            "alerts": alerts,
            "reading_status": "Unavailable",
            "message": str(error)
        }

    # --------------------------------------------------
    # 2. Check reading freshness
    # --------------------------------------------------

    is_fresh, reading_status = check_reading_freshness(
        reading_timestamp
    )

    if not is_fresh:

        for rule in rules:

            is_data_rule = (
                rule["alert_type"] == "Data unavailable"
            )

            message = (
                f"AQI monitoring for {location} returned a "
                f"{reading_status.lower()} reading. "
                f"The reading cannot be used for current AQI alerts."
            )

            alert = record_alert_if_new(
                rule,
                is_data_rule and bool(rule["enabled"]),
                message,
                "High",
                aqi,
                alert_timestamp
            )

            if alert:
                alerts.append(alert)

        return {
            "success": False,
            "location": location,
            "aqi": aqi,
            "severity": aqi_severity,
            "reading_status": reading_status,
            "alerts": alerts,
            "message": (
                f"Reading for {location} is not fresh. "
                f"Normal AQI alerts were not evaluated."
            )
        }

    # --------------------------------------------------
    # 3. Get previous stored reading
    # --------------------------------------------------

    previous_reading = get_previous_reading(
        location,
        reading_timestamp
    )

    previous_aqi = None

    if previous_reading:
        previous_aqi = float(previous_reading["aqi"])

    # --------------------------------------------------
    # 4. Evaluate deterministic alert rules
    # --------------------------------------------------

    for rule in rules:

        alert_type = rule["alert_type"]
        enabled = bool(rule["enabled"])

        condition = False
        threshold = rule["threshold_value"]

        if enabled:

            if alert_type == "AQI threshold exceeded":

                condition = (
                    threshold is not None
                    and aqi >= threshold
                )

            elif alert_type == "AQI increased significantly":

                increase_threshold = rule["increase_value"]

                condition = (
                    previous_aqi is not None
                    and increase_threshold is not None
                    and (aqi - previous_aqi) >= increase_threshold
                )

            elif alert_type == "Unhealthy air-quality condition":

                condition = (
                    str(aqi_severity).strip().casefold()
                    in UNHEALTHY_SEVERITIES
                )

            elif alert_type == "Sensitive-group precaution":

                condition = (
                    str(aqi_severity).strip().casefold()
                    in SENSITIVE_SEVERITIES
                )

            elif alert_type == "Data unavailable":

                condition = False

        message = create_alert_message(
            alert_type,
            location,
            aqi,
            aqi_severity,
            previous_aqi,
            threshold
        )

        alert = record_alert_if_new(
            rule,
            condition,
            message,
            get_alert_severity(aqi_severity),
            aqi,
            alert_timestamp
        )

        if alert:
            alerts.append(alert)

    # --------------------------------------------------
    # 5. Save fresh reading for future comparisons
    # --------------------------------------------------

    try:
        save_aqi_reading(result)

    except Exception as error:
        print(
            f"Warning: AQI history could not be updated: {error}"
        )

    return {
        "success": True,
        "location": location,
        "aqi": aqi,
        "severity": aqi_severity,
        "reading_status": "Fresh",
        "alerts": alerts,
        "message": (
            f"Alert evaluation completed for {location}."
        )
    }


def evaluate_multiple_locations(locations):
    """Evaluate configured alerts for multiple locations."""

    if not isinstance(locations, (list, tuple)):
        raise ValueError("Locations must be provided as a list.")

    if not locations:
        raise ValueError("At least one location is required.")

    results = []
    seen = set()

    for location in locations:

        if not isinstance(location, str) or not location.strip():
            raise ValueError("Every location must be a non-empty string.")

        location = location.strip()

        if location.casefold() in seen:
            continue

        seen.add(location.casefold())

        results.append(
            evaluate_location_alerts(location)
        )

    return {
        "success": True,
        "locations_checked": len(results),
        "results": results,
        "total_alerts": sum(
            len(item["alerts"])
            for item in results
        )
    }


def get_alert_history(location=None, limit=100):
    """Retrieve previously generated alerts."""

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or limit <= 0
    ):
        raise ValueError("Limit must be a positive integer.")

    initialize_alert_tables()

    connection = get_connection()

    try:

        if location is None:

            rows = connection.execute("""
                SELECT
                    location,
                    alert_type,
                    message,
                    severity,
                    aqi,
                    timestamp
                FROM alert_history
                ORDER BY alert_id DESC
                LIMIT ?
            """, (limit,)).fetchall()

        else:

            rows = connection.execute("""
                SELECT
                    location,
                    alert_type,
                    message,
                    severity,
                    aqi,
                    timestamp
                FROM alert_history
                WHERE location = ?
                ORDER BY alert_id DESC
                LIMIT ?
            """, (
                location,
                limit
            )).fetchall()

        columns = [
            "location",
            "alert_type",
            "message",
            "severity",
            "aqi",
            "timestamp"
        ]

        return [
            dict(zip(columns, row))
            for row in rows
        ]

    finally:
        connection.close()