# ============================================================
# PART 4 - AQI AND POLLUTANT SEVERITY RULES
# ============================================================
#
# All predefined severity thresholds are kept in this file.
#
# These values are based on the AQI Category, Pollutants and
# Health Breakpoints table provided for this project.
#
# IMPORTANT:
# - AQI determines the overall severity category.
# - Pollutants are evaluated independently.
# - A pollutant does NOT override the overall AQI category.
# ============================================================


# ------------------------------------------------------------
# AQI SEVERITY RULES
# ------------------------------------------------------------
#
# Boundaries:
# Good             : 0 - 50
# Satisfactory     : 51 - 100
# Moderately polluted: 101 - 200
# Poor             : 201 - 300
# Very Poor        : 301 - 400
# Severe           : 401 - 500
#
# Upper limits are inclusive.
# ------------------------------------------------------------

AQI_RULES = [
    {
        "severity": "Good",
        "minimum": 0,
        "maximum": 50
    },
    {
        "severity": "Satisfactory",
        "minimum": 51,
        "maximum": 100
    },
    {
        "severity": "Moderately polluted",
        "minimum": 101,
        "maximum": 200
    },
    {
        "severity": "Poor",
        "minimum": 201,
        "maximum": 300
    },
    {
        "severity": "Very Poor",
        "minimum": 301,
        "maximum": 400
    },
    {
        "severity": "Severe",
        "minimum": 401,
        "maximum": 500
    }
]


# ------------------------------------------------------------
# POLLUTANT BREAKPOINT RULES
# ------------------------------------------------------------
#
# Each pollutant has its own breakpoints.
#
# "severity" uses the same category names as the AQI table.
#
# The table contains:
#
# PM10   : 0-50, 51-100, 101-250, 251-350,
#          351-430, 430+
#
# PM2.5  : 0-30, 31-60, 61-90, 91-120,
#          121-250, 250+
#
# NO2    : 0-40, 41-80, 81-180, 181-280,
#          281-400, 400+
#
# O3     : 0-50, 51-100, 101-168, 169-208,
#          209-748, 748+
#
# CO     : 0-1.0, 1.1-2.0, 2.1-10,
#          10-17, 17-34, 34+
#
# SO2    : 0-40, 41-80, 81-380, 381-800,
#          801-1600, 1600+
#
# For pollutant ranges where the source table visually shows
# overlapping endpoint notation (for example CO at 10 and 17),
# the engine uses ordered ranges: a boundary value belongs to
# the higher severity range.
# ------------------------------------------------------------

POLLUTANT_RULES = {

    "pm25": [
        ("Good", 0, 30),
        ("Satisfactory", 31, 60),
        ("Moderately polluted", 61, 90),
        ("Poor", 91, 120),
        ("Very Poor", 121, 250),
        ("Severe", 251, None)
    ],

    "pm10": [
        ("Good", 0, 50),
        ("Satisfactory", 51, 100),
        ("Moderately polluted", 101, 250),
        ("Poor", 251, 350),
        ("Very Poor", 351, 430),
        ("Severe", 431, None)
    ],

    "no2": [
        ("Good", 0, 40),
        ("Satisfactory", 41, 80),
        ("Moderately polluted", 81, 180),
        ("Poor", 181, 280),
        ("Very Poor", 281, 400),
        ("Severe", 401, None)
    ],

    "o3": [
        ("Good", 0, 50),
        ("Satisfactory", 51, 100),
        ("Moderately polluted", 101, 168),
        ("Poor", 169, 208),
        ("Very Poor", 209, 748),
        ("Severe", 749, None)
    ],

    "co": [
        ("Good", 0, 1.0),
        ("Satisfactory", 1.1, 2.0),
        ("Moderately polluted", 2.1, 9.9),
        ("Poor", 10.0, 17.0),
        ("Very Poor", 17.1, 34.0),
        ("Severe", 34.1, None)
    ],

    "so2": [
        ("Good", 0, 40),
        ("Satisfactory", 41, 80),
        ("Moderately polluted", 81, 380),
        ("Poor", 381, 800),
        ("Very Poor", 801, 1600),
        ("Severe", 1601, None)
    ]
}