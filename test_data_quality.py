
import pytest

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import app.monitoring.data_quality as monitor


def create_validation_result(
    aqi=124,
    pollutants=None,
    timestamp=None,
    valid=True
):

    if pollutants is None:

        pollutants = {
            "pm25": 124,
            "pm10": 68,
            "no2": 4.1,
            "so2": 2.4,
            "co": 9.1,
            "o3": 10.9
        }

    if timestamp is None:

        timestamp = datetime.now(
            ZoneInfo("Asia/Kolkata")
        ).isoformat(timespec="seconds")

    return {
        "valid": valid,
        "data": {
            "location": "Delhi",
            "aqi": aqi,
            "pollutants": pollutants,
            "timestamp": timestamp
        },
        "errors": []
    }


# --------------------------------------------------
# 1. COMPLETE AND FRESH DATA
# --------------------------------------------------

def test_good_data_quality():

    result = monitor.evaluate_data_quality(
        "Delhi",
        create_validation_result()
    )

    assert result["data_available"] is True

    assert result["data_completeness"] == 100.0

    assert result["missing_pollutants"] == []

    assert result["invalid_fields"] == []

    assert result["is_stale"] is False

    assert result["status"] == "GOOD"


# --------------------------------------------------
# 2. MISSING POLLUTANT
# --------------------------------------------------

def test_missing_pollutant():

    pollutants = {
        "pm25": 124,
        "pm10": 68,
        "no2": 4.1,
        "so2": 2.4,
        "co": 9.1
    }

    result = monitor.evaluate_data_quality(
        "Delhi",
        create_validation_result(
            pollutants=pollutants
        )
    )

    assert result["data_completeness"] == 85.7

    assert "o3" in result["missing_pollutants"]

    assert result["status"] == "WARNING"


# --------------------------------------------------
# 3. MULTIPLE MISSING POLLUTANTS
# --------------------------------------------------

def test_multiple_missing_pollutants():

    pollutants = {
        "pm25": 124,
        "pm10": 68
    }

    result = monitor.evaluate_data_quality(
        "Delhi",
        create_validation_result(
            pollutants=pollutants
        )
    )

    assert len(result["missing_pollutants"]) == 4

    assert result["data_completeness"] == 42.9

    assert result["status"] == "WARNING"


# --------------------------------------------------
# 4. INVALID POLLUTANT VALUE
# --------------------------------------------------

def test_invalid_pollutant_value():

    pollutants = {
        "pm25": 124,
        "pm10": 68,
        "no2": "invalid",
        "so2": 2.4,
        "co": 9.1,
        "o3": 10.9
    }

    result = monitor.evaluate_data_quality(
        "Delhi",
        create_validation_result(
            pollutants=pollutants
        )
    )

    assert "no2" in result["invalid_fields"]

    assert result["data_completeness"] == 85.7

    assert result["status"] == "WARNING"


# --------------------------------------------------
# 5. NEGATIVE POLLUTANT VALUE
# --------------------------------------------------

def test_negative_pollutant_value():

    pollutants = {
        "pm25": 124,
        "pm10": -5,
        "no2": 4.1,
        "so2": 2.4,
        "co": 9.1,
        "o3": 10.9
    }

    result = monitor.evaluate_data_quality(
        "Delhi",
        create_validation_result(
            pollutants=pollutants
        )
    )

    assert "pm10" in result["invalid_fields"]

    assert result["status"] == "WARNING"


# --------------------------------------------------
# 6. NON-FINITE POLLUTANT VALUE
# --------------------------------------------------

def test_non_finite_pollutant_value():

    pollutants = {
        "pm25": 124,
        "pm10": 68,
        "no2": float("nan"),
        "so2": 2.4,
        "co": 9.1,
        "o3": 10.9
    }

    result = monitor.evaluate_data_quality(
        "Delhi",
        create_validation_result(
            pollutants=pollutants
        )
    )

    assert "no2" in result["invalid_fields"]


# --------------------------------------------------
# 7. INVALID AQI VALUE
# --------------------------------------------------

def test_invalid_aqi_value():

    result = monitor.evaluate_data_quality(
        "Delhi",
        create_validation_result(
            aqi=-10
        )
    )

    assert "aqi" in result["invalid_fields"]

    assert result["status"] == "CRITICAL"


# --------------------------------------------------
# 8. STALE READING
# --------------------------------------------------

def test_stale_reading():

    old_timestamp = (
        datetime.now(
            ZoneInfo("Asia/Kolkata")
        ) - timedelta(hours=48)
    ).isoformat()

    result = monitor.evaluate_data_quality(
        "Delhi",
        create_validation_result(
            timestamp=old_timestamp
        )
    )

    assert result["is_stale"] is True

    assert result["status"] == "CRITICAL"

    assert any(
        "older than" in warning
        for warning in result["warnings"]
    )


# --------------------------------------------------
# 9. FRESH READING
# --------------------------------------------------

def test_fresh_reading():

    result = monitor.evaluate_data_quality(
        "Delhi",
        create_validation_result()
    )

    assert result["is_stale"] is False


# --------------------------------------------------
# 10. MISSING TIMESTAMP
# --------------------------------------------------

def test_missing_timestamp():

    result = monitor.evaluate_data_quality(
        "Delhi",
        create_validation_result(
            timestamp=None
        )
    )

    # create_validation_result supplies a current timestamp
    # when timestamp is None, so remove it explicitly.

    validation = create_validation_result()

    validation["data"]["timestamp"] = None

    result = monitor.evaluate_data_quality(
        "Delhi",
        validation
    )

    assert result["is_stale"] is False

    assert result["status"] == "WARNING"

    assert any(
        "timestamp is missing" in warning.lower()
        for warning in result["warnings"]
    )


# --------------------------------------------------
# 11. FUTURE TIMESTAMP
# --------------------------------------------------

def test_future_timestamp():

    future_timestamp = (
        datetime.now(
            ZoneInfo("Asia/Kolkata")
        ) + timedelta(hours=2)
    ).isoformat()

    result = monitor.evaluate_data_quality(
        "Delhi",
        create_validation_result(
            timestamp=future_timestamp
        )
    )

    assert result["is_stale"] is True

    assert result["status"] == "CRITICAL"


# --------------------------------------------------
# 12. UNAVAILABLE DATA
# --------------------------------------------------

def test_unavailable_data():

    result = monitor.evaluate_data_quality(
        "Delhi",
        None,
        request_status=False
    )

    assert result["data_available"] is False

    assert result["data_completeness"] == 0.0

    assert result["status"] == "UNAVAILABLE"

    assert len(result["missing_pollutants"]) == 6


# --------------------------------------------------
# 13. INVALID VALIDATION RESULT
# --------------------------------------------------

def test_invalid_validation_result():

    validation = {
        "valid": False,
        "data": None,
        "errors": ["AQI data is invalid."]
    }

    result = monitor.evaluate_data_quality(
        "Delhi",
        validation
    )

    assert result["data_available"] is False

    assert result["status"] == "UNAVAILABLE"


# --------------------------------------------------
# 14. API FAILURE
# --------------------------------------------------

def test_api_failure(monkeypatch, tmp_path):

    monkeypatch.setattr(
        monitor,
        "DB_PATH",
        tmp_path / "test_monitoring.db"
    )

    monkeypatch.setattr(
        monitor,
        "get_aqi_data",
        lambda location: {
            "status": "error"
        }
    )

    result = monitor.monitor_aqi_data(
        "Delhi"
    )

    assert result["data_available"] is False

    assert result["status"] == "UNAVAILABLE"


# --------------------------------------------------
# 15. SUCCESSFUL API REQUEST AND DATABASE LOG
# --------------------------------------------------

def test_successful_monitoring_log(monkeypatch, tmp_path):

    monkeypatch.setattr(
        monitor,
        "DB_PATH",
        tmp_path / "test_monitoring.db"
    )

    monkeypatch.setattr(
        monitor,
        "get_aqi_data",
        lambda location: {
            "status": "ok",
            "data": {}
        }
    )

    monkeypatch.setattr(
        monitor,
        "validate_aqi_data",
        lambda api_result: create_validation_result()
    )

    result = monitor.monitor_aqi_data(
        "Delhi"
    )

    assert result["status"] == "GOOD"

    history = monitor.get_monitoring_history(
        "Delhi"
    )

    assert len(history) == 1

    assert history[0]["request_status"] == "SUCCESS"


# --------------------------------------------------
# 16. REQUEST STATISTICS
# --------------------------------------------------

def test_request_statistics(monkeypatch, tmp_path):

    monkeypatch.setattr(
        monitor,
        "DB_PATH",
        tmp_path / "test_monitoring.db"
    )

    monkeypatch.setattr(
        monitor,
        "get_aqi_data",
        lambda location: {
            "status": "ok",
            "data": {}
        }
    )

    monkeypatch.setattr(
        monitor,
        "validate_aqi_data",
        lambda api_result: create_validation_result()
    )

    monitor.monitor_aqi_data("Delhi")

    monkeypatch.setattr(
        monitor,
        "get_aqi_data",
        lambda location: {
            "status": "error"
        }
    )

    monitor.monitor_aqi_data("Delhi")

    statistics = monitor.get_request_statistics(
        "Delhi"
    )

    assert statistics["total_requests"] == 2

    assert statistics["successful_requests"] == 1

    assert statistics["failed_requests"] == 1


# --------------------------------------------------
# 17. INVALID LOCATION
# --------------------------------------------------

def test_invalid_location():

    result = monitor.monitor_aqi_data("")

    assert result["data_available"] is False

    assert result["status"] == "UNAVAILABLE"


# --------------------------------------------------
# 18. COMPLETENESS DOES NOT MODIFY DATA
# --------------------------------------------------

def test_original_pollutant_values_remain_unchanged():

    validation = create_validation_result()

    original_pollutants = (
        validation["data"]["pollutants"].copy()
    )

    monitor.evaluate_data_quality(
        "Delhi",
        validation
    )

    assert (
        validation["data"]["pollutants"]
        == original_pollutants
    )
