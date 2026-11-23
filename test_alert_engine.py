
import sqlite3

import pytest

from app.alerts import alert_engine


@pytest.fixture
def setup_alert_database(tmp_path, monkeypatch):

    db_path = tmp_path / "test_alerts.db"

    monkeypatch.setattr(
        alert_engine,
        "get_connection",
        lambda: sqlite3.connect(str(db_path))
    )

    monkeypatch.setattr(
        alert_engine,
        "create_history_table",
        lambda: None
    )

    alert_engine.initialize_alert_tables()

    return db_path


def test_default_rule_configuration(setup_alert_database):

    locations = ["Delhi", "Mumbai"]

    result = alert_engine.configure_default_alert_rules(
        locations
    )

    assert len(result) == 10

    rules = alert_engine.get_alert_rules("Delhi")

    assert len(rules) == 5


def test_aqi_threshold_alert(
    setup_alert_database,
    monkeypatch
):

    alert_engine.configure_default_alert_rules(["Delhi"])

    monkeypatch.setattr(
        alert_engine,
        "get_aqi_advisory",
        lambda location: {
            "success": True,
            "location": location,
            "aqi": 150,
            "severity": "Moderately polluted",
            "timestamp": "2026-11-23 16:00:00",
            "pollutants": {}
        }
    )

    monkeypatch.setattr(
        alert_engine,
        "get_aqi_history",
        lambda location=None: []
    )

    monkeypatch.setattr(
        alert_engine,
        "save_aqi_reading",
        lambda result: None
    )

    result = alert_engine.evaluate_location_alerts("Delhi")

    alert_types = [
        alert["alert_type"]
        for alert in result["alerts"]
    ]

    assert "AQI threshold exceeded" in alert_types


def test_duplicate_alert_prevention(
    setup_alert_database,
    monkeypatch
):

    alert_engine.configure_default_alert_rules(["Delhi"])

    monkeypatch.setattr(
        alert_engine,
        "get_aqi_advisory",
        lambda location: {
            "success": True,
            "location": location,
            "aqi": 150,
            "severity": "Moderately polluted",
            "timestamp": "2026-11-23 16:00:00",
            "pollutants": {}
        }
    )

    monkeypatch.setattr(
        alert_engine,
        "get_aqi_history",
        lambda location=None: []
    )

    monkeypatch.setattr(
        alert_engine,
        "save_aqi_reading",
        lambda result: None
    )

    first = alert_engine.evaluate_location_alerts("Delhi")
    second = alert_engine.evaluate_location_alerts("Delhi")

    assert len(first["alerts"]) > 0
    assert len(second["alerts"]) == 0


def test_significant_aqi_increase(
    setup_alert_database,
    monkeypatch
):

    alert_engine.configure_default_alert_rules(["Delhi"])

    for alert_type in alert_engine.ALERT_TYPES:

        alert_engine.set_alert_rule(
            "Delhi",
            alert_type,
            enabled=(
                alert_type == "AQI increased significantly"
            ),
            increase_value=50
        )

    monkeypatch.setattr(
        alert_engine,
        "get_aqi_advisory",
        lambda location: {
            "success": True,
            "location": location,
            "aqi": 160,
            "severity": "Moderately polluted",
            "timestamp": "2026-11-23 17:00:00",
            "pollutants": {}
        }
    )

    monkeypatch.setattr(
        alert_engine,
        "get_aqi_history",
        lambda location=None: [
            {
                "location": "Delhi",
                "aqi": 100,
                "timestamp": "2026-11-23 16:00:00"
            }
        ]
    )

    monkeypatch.setattr(
        alert_engine,
        "save_aqi_reading",
        lambda result: None
    )

    result = alert_engine.evaluate_location_alerts("Delhi")

    assert len(result["alerts"]) == 1

    assert (
        result["alerts"][0]["alert_type"]
        == "AQI increased significantly"
    )


def test_unhealthy_air_alert(
    setup_alert_database,
    monkeypatch
):

    alert_engine.configure_default_alert_rules(["Delhi"])

    monkeypatch.setattr(
        alert_engine,
        "get_aqi_advisory",
        lambda location: {
            "success": True,
            "location": location,
            "aqi": 250,
            "severity": "Poor",
            "timestamp": "2026-11-23 17:00:00",
            "pollutants": {}
        }
    )

    monkeypatch.setattr(
        alert_engine,
        "get_aqi_history",
        lambda location=None: []
    )

    monkeypatch.setattr(
        alert_engine,
        "save_aqi_reading",
        lambda result: None
    )

    result = alert_engine.evaluate_location_alerts("Delhi")

    alert_types = [
        alert["alert_type"]
        for alert in result["alerts"]
    ]

    assert "Unhealthy air-quality condition" in alert_types
    assert "Sensitive-group precaution" in alert_types


def test_data_unavailable_alert(
    setup_alert_database,
    monkeypatch
):

    alert_engine.configure_default_alert_rules(["Mumbai"])

    monkeypatch.setattr(
        alert_engine,
        "get_aqi_advisory",
        lambda location: {
            "success": False,
            "errors": ["WAQI API unavailable."]
        }
    )

    result = alert_engine.evaluate_location_alerts("Mumbai")

    assert len(result["alerts"]) == 1

    assert (
        result["alerts"][0]["alert_type"]
        == "Data unavailable"
    )

    assert result["alerts"][0]["aqi"] is None


def test_disabled_rule(
    setup_alert_database,
    monkeypatch
):

    alert_engine.configure_default_alert_rules(["Delhi"])

    alert_engine.set_alert_rule(
        "Delhi",
        "AQI threshold exceeded",
        enabled=False
    )

    monkeypatch.setattr(
        alert_engine,
        "get_aqi_advisory",
        lambda location: {
            "success": True,
            "location": location,
            "aqi": 200,
            "severity": "Moderately polluted",
            "timestamp": "2026-11-23 17:00:00",
            "pollutants": {}
        }
    )

    monkeypatch.setattr(
        alert_engine,
        "get_aqi_history",
        lambda location=None: []
    )

    monkeypatch.setattr(
        alert_engine,
        "save_aqi_reading",
        lambda result: None
    )

    result = alert_engine.evaluate_location_alerts("Delhi")

    alert_types = [
        alert["alert_type"]
        for alert in result["alerts"]
    ]

    assert "AQI threshold exceeded" not in alert_types


def test_alert_history_retrieval(
    setup_alert_database,
    monkeypatch
):

    alert_engine.configure_default_alert_rules(["Delhi"])

    monkeypatch.setattr(
        alert_engine,
        "get_aqi_advisory",
        lambda location: {
            "success": True,
            "location": location,
            "aqi": 150,
            "severity": "Moderately polluted",
            "timestamp": "2026-11-23 16:00:00",
            "pollutants": {}
        }
    )

    monkeypatch.setattr(
        alert_engine,
        "get_aqi_history",
        lambda location=None: []
    )

    monkeypatch.setattr(
        alert_engine,
        "save_aqi_reading",
        lambda result: None
    )

    alert_engine.evaluate_location_alerts("Delhi")

    history = alert_engine.get_alert_history("Delhi")

    assert len(history) > 0

    assert "location" in history[0]
    assert "alert_type" in history[0]
    assert "message" in history[0]
    assert "severity" in history[0]
    assert "aqi" in history[0]
    assert "timestamp" in history[0]


def test_invalid_location():

    with pytest.raises(ValueError):
        alert_engine.evaluate_location_alerts("")


def test_invalid_alert_type(setup_alert_database):

    with pytest.raises(ValueError):

        alert_engine.set_alert_rule(
            "Delhi",
            "Unknown alert",
            enabled=True
        )

def test_outdated_reading_generates_data_alert(
    setup_alert_database,
    monkeypatch
):

    alert_engine.configure_default_alert_rules(["Pune"])

    monkeypatch.setattr(
        alert_engine,
        "get_aqi_advisory",
        lambda location: {
            "success": True,
            "location": location,
            "aqi": 232,
            "severity": "Poor",
            "timestamp": "2021-11-15 06:00:00",
            "pollutants": {}
        }
    )

    result = alert_engine.evaluate_location_alerts("Pune")

    assert result["success"] is False
    assert result["reading_status"] == "Outdated"

    alert_types = [
        alert["alert_type"]
        for alert in result["alerts"]
    ]

    assert "Data unavailable" in alert_types

    assert "AQI threshold exceeded" not in alert_types

    assert "Unhealthy air-quality condition" not in alert_types

    assert "Sensitive-group precaution" not in alert_types