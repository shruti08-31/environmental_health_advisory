
import pytest

from app.activity_advisor import (
    generate_activity_advisory,
    generate_activity_guidance,
    get_live_activity_advisory
)


def create_inputs(aqi, severity, pollutants=None):

    validation_result = {
        "valid": True,
        "data": {
            "location": "Delhi",
            "aqi": aqi,
            "pollutants": pollutants or {},
            "timestamp": "2026-11-23 16:00:00"
        },
        "errors": []
    }

    severity_result = {
        "severity": severity,
        "severity_reason": "Test severity result."
    }

    return validation_result, severity_result


# --------------------------------------------------
# 1. GOOD AQI + WALKING
# --------------------------------------------------

def test_good_aqi_walking():

    validation, severity = create_inputs(
        40,
        "Good"
    )

    result = generate_activity_advisory(
        validation,
        severity,
        "walking"
    )

    assert result["success"] is True
    assert result["activity"] == "walking"
    assert result["severity"] == "Good"
    assert "generally continue" in result["recommendation"]


# --------------------------------------------------
# 2. SATISFACTORY AQI + RUNNING
# --------------------------------------------------

def test_satisfactory_aqi_running():

    validation, severity = create_inputs(
        80,
        "Satisfactory"
    )

    result = generate_activity_advisory(
        validation,
        severity,
        "running"
    )

    assert result["success"] is True
    assert result["activity"] == "running"


# --------------------------------------------------
# 3. MODERATE AQI + RUNNING
# --------------------------------------------------

def test_moderate_aqi_running():

    validation, severity = create_inputs(
        150,
        "Moderately polluted"
    )

    result = generate_activity_advisory(
        validation,
        severity,
        "running"
    )

    assert result["success"] is True

    assert "indoors" in result["recommendation"]


# --------------------------------------------------
# 4. MODERATE AQI + WALKING
# --------------------------------------------------

def test_moderate_aqi_walking():

    validation, severity = create_inputs(
        150,
        "Moderately polluted"
    )

    result = generate_activity_advisory(
        validation,
        severity,
        "walking"
    )

    assert result["success"] is True

    assert "shorter" in result["recommendation"]


# --------------------------------------------------
# 5. POOR AQI + CYCLING
# --------------------------------------------------

def test_poor_aqi_cycling():

    validation, severity = create_inputs(
        250,
        "Poor"
    )

    result = generate_activity_advisory(
        validation,
        severity,
        "cycling"
    )

    assert result["success"] is True

    assert "Postpone" in result["recommendation"]


# --------------------------------------------------
# 6. VERY POOR AQI + OUTDOOR EXERCISE
# --------------------------------------------------

def test_very_poor_aqi_outdoor_exercise():

    validation, severity = create_inputs(
        350,
        "Very Poor"
    )

    result = generate_activity_advisory(
        validation,
        severity,
        "outdoor exercise"
    )

    assert result["success"] is True

    assert "Postpone" in result["recommendation"]

    assert result["alternative_activity"] is not None


# --------------------------------------------------
# 7. SEVERE AQI + WALKING
# --------------------------------------------------

def test_severe_aqi_walking():

    validation, severity = create_inputs(
        450,
        "Severe"
    )

    result = generate_activity_advisory(
        validation,
        severity,
        "walking"
    )

    assert result["success"] is True

    assert "Avoid outdoor" in result["recommendation"]


# --------------------------------------------------
# 8. SENSITIVE GROUP + MODERATE AQI
# --------------------------------------------------

def test_sensitive_group_moderate_aqi():

    validation, severity = create_inputs(
        150,
        "Moderately polluted"
    )

    result = generate_activity_advisory(
        validation,
        severity,
        "walking",
        "children"
    )

    assert result["success"] is True

    assert result["sensitivity_category"] == "children"

    assert any(
        "strenuous outdoor" in item.lower()
        for item in result["precautions"]
    )


# --------------------------------------------------
# 9. RESPIRATORY SENSITIVITY + POOR AQI
# --------------------------------------------------

def test_respiratory_sensitivity_poor_aqi():

    validation, severity = create_inputs(
        250,
        "Poor"
    )

    result = generate_activity_advisory(
        validation,
        severity,
        "running",
        "respiratory_conditions"
    )

    assert result["success"] is True

    assert "Avoid" in result["recommendation"]


# --------------------------------------------------
# 10. INDOOR EXERCISE + SEVERE AQI
# --------------------------------------------------

def test_indoor_exercise_severe_aqi():

    validation, severity = create_inputs(
        450,
        "Severe"
    )

    result = generate_activity_advisory(
        validation,
        severity,
        "indoor exercise"
    )

    assert result["success"] is True

    assert "indoor" in result["recommendation"].lower()

    assert any(
        "indoor air" in item.lower()
        for item in result["precautions"]
    )


# --------------------------------------------------
# 11. POLLUTANT DATA
# --------------------------------------------------

def test_pollutant_readings():

    validation, severity = create_inputs(
        124,
        "Moderately polluted",
        {
            "pm25": 124,
            "pm10": 68,
            "no2": 4.1,
            "so2": 2.4,
            "co": 9.1,
            "o3": 10.9
        }
    )

    result = generate_activity_advisory(
        validation,
        severity,
        "cycling"
    )

    assert result["success"] is True

    assert result["pollutant_readings"]["pm25"] == 124

    assert len(result["pollutant_readings"]) == 6


# --------------------------------------------------
# 12. MISSING POLLUTANT DATA
# --------------------------------------------------

def test_missing_pollutant_data():

    validation, severity = create_inputs(
        100,
        "Satisfactory",
        {
            "pm25": 100,
            "pm10": None
        }
    )

    result = generate_activity_advisory(
        validation,
        severity,
        "walking"
    )

    assert result["success"] is True

    assert "pm25" in result["pollutant_readings"]

    assert "pm10" not in result["pollutant_readings"]


# --------------------------------------------------
# 13. INVALID ACTIVITY
# --------------------------------------------------

def test_invalid_activity():

    validation, severity = create_inputs(
        100,
        "Satisfactory"
    )

    result = generate_activity_advisory(
        validation,
        severity,
        "swimming"
    )

    assert result["success"] is False

    assert "Unsupported activity selected." in result["errors"]


# --------------------------------------------------
# 14. INVALID SENSITIVITY CATEGORY
# --------------------------------------------------

def test_invalid_sensitivity():

    validation, severity = create_inputs(
        100,
        "Satisfactory"
    )

    result = generate_activity_advisory(
        validation,
        severity,
        "walking",
        "unknown"
    )

    assert result["success"] is False


# --------------------------------------------------
# 15. INVALID VALIDATION RESULT
# --------------------------------------------------

def test_failed_validation():

    validation = {
        "valid": False,
        "data": None,
        "errors": ["AQI is missing."]
    }

    severity = {
        "severity": "Good"
    }

    result = generate_activity_advisory(
        validation,
        severity,
        "walking"
    )

    assert result["success"] is False


# --------------------------------------------------
# 16. INVALID SEVERITY
# --------------------------------------------------

def test_invalid_severity():

    validation, severity = create_inputs(
        100,
        "Unknown"
    )

    result = generate_activity_advisory(
        validation,
        severity,
        "walking"
    )

    assert result["success"] is False


# --------------------------------------------------
# 17. ACTIVITY RULE SEPARATION
# --------------------------------------------------

def test_activity_guidance_separation():

    result = generate_activity_guidance(
        "running",
        "poor",
        "general"
    )

    assert "recommendation" in result
    assert "precautions" in result
    assert "alternative_activity" in result


# --------------------------------------------------
# 18. LIVE PIPELINE FAILURE
# --------------------------------------------------

def test_live_pipeline_failure(monkeypatch):

    import app.activity_advisor as advisor

    monkeypatch.setattr(
        advisor,
        "get_aqi_advisory",
        lambda location: {
            "success": False,
            "errors": ["WAQI API unavailable."]
        }
    )

    result = get_live_activity_advisory(
        "Delhi",
        "walking"
    )

    assert result["success"] is False
    assert "WAQI API unavailable." in result["errors"]
