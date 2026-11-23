
from app.history.database import (
    create_history_table,
    save_aqi_reading,
    get_aqi_history
)

from app.history.analytics import (
    get_history_dataframe,
    calculate_aqi_statistics,
    calculate_pollutant_averages,
    get_daily_analysis,
    get_weekly_analysis,
    get_monthly_analysis,
    get_severity_distribution,
    get_aqi_analytics
)


# -------------------------------------------------
# SAMPLE DATA
# -------------------------------------------------

sample_data = [

    {
        "success": True,
        "location": "Part 10 Test Location",
        "aqi": 80,
        "pollutants": {
            "pm25": 25,
            "pm10": 40,
            "no2": 12,
            "so2": 4,
            "co": 0.5,
            "o3": 20
        },
        "severity": "Satisfactory",
        "timestamp": "2026-11-20 08:00:00"
    },

    {
        "success": True,
        "location": "Part 10 Test Location",
        "aqi": 120,
        "pollutants": {
            "pm25": 55,
            "pm10": 65,
            "no2": 18,
            "so2": 6,
            "co": 0.8,
            "o3": 25
        },
        "severity": "Moderately polluted",
        "timestamp": "2026-11-20 20:00:00"
    },

    {
        "success": True,
        "location": "Part 10 Test Location",
        "aqi": 140,
        "pollutants": {
            "pm25": 65,
            "pm10": 75,
            "no2": 20,
            "so2": 7,
            "co": 0.9,
            "o3": 28
        },
        "severity": "Moderately polluted",
        "timestamp": "2026-11-21 08:00:00"
    },

    {
        "success": True,
        "location": "Part 10 Test Location",
        "aqi": 160,
        "pollutants": {
            "pm25": 80,
            "pm10": 90,
            "no2": 22,
            "so2": 8,
            "co": 1.0,
            "o3": 30
        },
        "severity": "Moderately polluted",
        "timestamp": "2026-11-22 08:00:00"
    }
]


# -------------------------------------------------
# TEST 1: CREATE DATABASE TABLE
# -------------------------------------------------

print("\nTEST 1: DATABASE CREATION")

create_history_table()

print("Database table created successfully.")


# -------------------------------------------------
# TEST 2: INSERT SAMPLE DATA
# -------------------------------------------------

print("\nTEST 2: INSERT SAMPLE DATA")

for item in sample_data:

    result = save_aqi_reading(item)

    print(result)


# -------------------------------------------------
# TEST 3: DUPLICATE HANDLING
# -------------------------------------------------

print("\nTEST 3: DUPLICATE HANDLING")

duplicate_result = save_aqi_reading(
    sample_data[0]
)

print(duplicate_result)


# -------------------------------------------------
# TEST 4: RETRIEVE HISTORY
# -------------------------------------------------

print("\nTEST 4: RETRIEVE HISTORY")

records = get_aqi_history(
    location="Part 10 Test Location"
)

print("Total records:", len([
    item for item in records
    if item["timestamp"] >= "2026-11-20"
    and item["timestamp"] < "2026-11-23"
]))

# Use a date-filtered DataFrame for calculations.
df = get_history_dataframe(
    location="Part 10 Test Location",
    start_date="2026-11-20 00:00:00",
    end_date="2026-11-23 00:00:00"
)

print(df[["location", "aqi", "severity", "timestamp"]])


# -------------------------------------------------
# TEST 5: AQI STATISTICS
# -------------------------------------------------

print("\nTEST 5: AQI STATISTICS")

statistics = calculate_aqi_statistics(df)

print(statistics)


# -------------------------------------------------
# TEST 6: POLLUTANT AVERAGES
# -------------------------------------------------

print("\nTEST 6: POLLUTANT AVERAGES")

pollutant_averages = calculate_pollutant_averages(df)

print(pollutant_averages)


# -------------------------------------------------
# TEST 7: DAILY ANALYSIS
# -------------------------------------------------

print("\nTEST 7: DAILY ANALYSIS")

daily = get_daily_analysis(
    location="Part 10 Test Location",
    start_date="2026-11-20 00:00:00",
    end_date="2026-11-23 00:00:00"
)

print(daily)


# -------------------------------------------------
# TEST 8: WEEKLY ANALYSIS
# -------------------------------------------------

print("\nTEST 8: WEEKLY ANALYSIS")

weekly = get_weekly_analysis(
    location="Part 10 Test Location",
    start_date="2026-11-20 00:00:00",
    end_date="2026-11-23 00:00:00"
)

print(weekly)


# -------------------------------------------------
# TEST 9: MONTHLY ANALYSIS
# -------------------------------------------------

print("\nTEST 9: MONTHLY ANALYSIS")

monthly = get_monthly_analysis(
    location="Part 10 Test Location",
    start_date="2026-11-20 00:00:00",
    end_date="2026-11-23 00:00:00"
)

print(monthly)


# -------------------------------------------------
# TEST 10: SEVERITY DISTRIBUTION
# -------------------------------------------------

print("\nTEST 10: SEVERITY DISTRIBUTION")

severity = get_severity_distribution(
    location="Part 10 Test Location",
    start_date="2026-11-20 00:00:00",
    end_date="2026-11-23 00:00:00"
)

print(severity)


# -------------------------------------------------
# TEST 11: COMPLETE ANALYTICS REPORT
# -------------------------------------------------

print("\nTEST 11: COMPLETE ANALYTICS REPORT")

report = get_aqi_analytics(
    location="Part 10 Test Location",
    start_date="2026-11-20 00:00:00",
    end_date="2026-11-23 00:00:00",
    period="daily"
)

print(report["message"])
print(report["statistics"])
print(report["pollutant_averages"])

print("\nPeriod Analysis:")
print(report["period_analysis"])

print("\nLine Chart Data:")
print(report["line_chart_data"])


# -------------------------------------------------
# TEST 12: MISSING HISTORICAL DATA
# -------------------------------------------------

print("\nTEST 12: MISSING HISTORICAL DATA")

empty_report = get_aqi_analytics(
    location="Unknown Test Location"
)

print(empty_report["message"])
print(empty_report["statistics"])


# -------------------------------------------------
# TEST 13: INVALID PERIOD
# -------------------------------------------------

print("\nTEST 13: INVALID PERIOD")

try:

    get_aqi_analytics(
        location="Part 10 Test Location",
        period="yearly"
    )

except ValueError as error:

    print("Expected error:", error)


print("\nALL TESTS COMPLETED.")
