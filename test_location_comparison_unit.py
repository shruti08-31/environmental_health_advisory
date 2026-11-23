
import pandas as pd
import pytest

from unittest.mock import patch

from app.comparison.location_comparison import (
    compare_locations,
    get_highest_pollutant,
    calculate_comparison_insights
)


def create_result(
    location,
    aqi,
    timestamp,
    pollutants=None,
    severity="Moderately polluted"
):

    if pollutants is None:
        pollutants = {}

    return {
        "success": True,
        "location": location,
        "aqi": aqi,
        "severity": severity,
        "timestamp": timestamp,
        "pollutants": pollutants
    }


@patch("app.comparison.location_comparison.get_aqi_advisory")
def test_basic_comparison(mock_api):

    mock_api.side_effect = [
        create_result(
            "Delhi",
            120,
            "2026-11-23 16:00:00",
            {"pm25": 120}
        ),
        create_result(
            "Mumbai",
            80,
            "2026-11-23 16:00:00",
            {"pm25": 80}
        )
    ]

    result = compare_locations(
        ["Delhi", "Mumbai"]
    )

    assert result["success"] is True

    assert result["insights"]["average_aqi"] == 100

    assert result["insights"]["highest_aqi"] == 120

    assert result["insights"]["lowest_aqi"] == 80

    assert result["insights"]["available_locations"] == 2


@patch("app.comparison.location_comparison.get_aqi_advisory")
def test_unavailable_location(mock_api):

    mock_api.side_effect = [
        create_result(
            "Delhi",
            120,
            "2026-11-23 16:00:00"
        ),
        {
            "success": False,
            "errors": ["Location not found."]
        }
    ]

    result = compare_locations(
        ["Delhi", "Unknown"]
    )

    assert result["success"] is True

    assert result["insights"]["available_locations"] == 1

    assert result["insights"]["unavailable_locations"] == 1


@patch("app.comparison.location_comparison.get_aqi_advisory")
def test_missing_pollutants(mock_api):

    mock_api.return_value = create_result(
        "Mumbai",
        85,
        "2026-11-23 16:00:00",
        {
            "pm25": 85,
            "pm10": None,
            "no2": 12
        }
    )

    result = compare_locations(
        ["Mumbai"]
    )

    df = result["comparison_data"]

    assert result["success"] is True

    assert df.iloc[0]["pm25"] == 85

    assert pd.isna(df.iloc[0]["pm10"])


@patch("app.comparison.location_comparison.get_aqi_advisory")
def test_outdated_reading_excluded(mock_api):

    mock_api.side_effect = [
        create_result(
            "Delhi",
            100,
            pd.Timestamp.now(tz="Asia/Kolkata").strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ),
        create_result(
            "Pune",
            232,
            "2021-11-15 06:00:00"
        )
    ]

    result = compare_locations(
        ["Delhi", "Pune"]
    )

    df = result["comparison_data"]

    assert df.iloc[0]["reading_status"] == "Fresh"

    assert df.iloc[1]["reading_status"] == "Outdated"

    assert result["insights"]["average_aqi"] == 100

    assert result["insights"]["available_locations"] == 1

    assert result["insights"]["outdated_locations"] == 1


@patch("app.comparison.location_comparison.get_aqi_advisory")
def test_missing_timestamp(mock_api):

    mock_api.return_value = create_result(
        "Delhi",
        120,
        None
    )

    result = compare_locations(
        ["Delhi"]
    )

    df = result["comparison_data"]

    assert df.iloc[0]["reading_status"] == "Timestamp unavailable"

    assert result["insights"]["available_locations"] == 0

    assert result["success"] is False


@patch("app.comparison.location_comparison.get_aqi_advisory")
def test_all_locations_outdated(mock_api):

    mock_api.return_value = create_result(
        "Pune",
        232,
        "2021-11-15 06:00:00"
    )

    result = compare_locations(
        ["Pune"]
    )

    assert result["success"] is False

    assert result["insights"]["available_locations"] == 0

    assert result["insights"]["outdated_locations"] == 1


@patch("app.comparison.location_comparison.get_aqi_advisory")
def test_duplicate_locations(mock_api):

    mock_api.return_value = create_result(
        "Delhi",
        120,
        "2026-11-23 16:00:00"
    )

    result = compare_locations(
        ["Delhi", "delhi", "Delhi"]
    )

    assert mock_api.call_count == 1

    assert len(result["comparison_data"]) == 1


def test_empty_locations():

    with pytest.raises(ValueError):

        compare_locations([])


def test_invalid_locations():

    with pytest.raises(ValueError):

        compare_locations(["Delhi", ""])


def test_highest_pollutant():

    name, value = get_highest_pollutant({
        "pm25": 80,
        "pm10": 120,
        "no2": 20,
        "so2": None
    })

    assert name == "pm10"

    assert value == 120


def test_no_pollutants():

    name, value = get_highest_pollutant({})

    assert name is None

    assert value is None


def test_comparison_insights_empty():

    df = pd.DataFrame({
        "success": [False],
        "aqi": [None],
        "location": ["Unknown"]
    })

    result = calculate_comparison_insights(df)

    assert result["available_locations"] == 0

    assert result["average_aqi"] is None
