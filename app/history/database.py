
import sqlite3
import os
from pathlib import Path


# -------------------------------------------------
# DATABASE CONFIGURATION
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "aqi_history.db"


# -------------------------------------------------
# DATABASE CONNECTION
# -------------------------------------------------

def get_connection():
    """
    Create and return a SQLite database connection.
    """

    connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row

    return connection


# -------------------------------------------------
# CREATE DATABASE TABLE
# -------------------------------------------------

def create_history_table():
    """
    Create the AQI history table if it does not exist.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aqi_history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            location TEXT NOT NULL,

            aqi REAL NOT NULL,

            pm25 REAL,
            pm10 REAL,
            no2 REAL,
            so2 REAL,
            co REAL,
            o3 REAL,

            severity TEXT NOT NULL,

            timestamp TEXT NOT NULL,

            UNIQUE(location, timestamp, aqi)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_aqi_location_timestamp
        ON aqi_history(location, timestamp)
    """)

    connection.commit()

    connection.close()


# -------------------------------------------------
# INSERT AQI READING
# -------------------------------------------------



def save_aqi_reading(aqi_result):
    """
    Save the structured result returned by the existing AQI pipeline.
    """

    if not isinstance(aqi_result, dict):

        raise ValueError(
            "AQI result must be a dictionary."
        )

    if not aqi_result.get("success"):

        raise ValueError(
            "Cannot store an unsuccessful AQI result."
        )

    location = aqi_result.get("location")
    aqi = aqi_result.get("aqi")
    pollutants = aqi_result.get("pollutants")
    severity = aqi_result.get("severity")
    timestamp = aqi_result.get("timestamp")

    # Validate required information

    if not location:
        raise ValueError("Location is missing.")

    if aqi is None:
        raise ValueError("AQI value is missing.")

    if not timestamp:
        raise ValueError(
            "Timestamp is missing from the pipeline result."
        )

    if not severity:
        raise ValueError("Severity is missing.")

    if not isinstance(pollutants, dict):

        raise ValueError(
            "Pollutant information must be a dictionary."
        )

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT OR IGNORE INTO aqi_history (
                location,
                aqi,
                pm25,
                pm10,
                no2,
                so2,
                co,
                o3,
                severity,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            location,
            aqi,
            pollutants.get("pm25"),
            pollutants.get("pm10"),
            pollutants.get("no2"),
            pollutants.get("so2"),
            pollutants.get("co"),
            pollutants.get("o3"),
            severity,
            timestamp
        ))

        connection.commit()

        inserted = cursor.rowcount == 1

        return {
            "success": True,
            "inserted": inserted,
            "message": (
                "AQI reading stored successfully."
                if inserted
                else "Duplicate AQI reading ignored."
            )
        }

    finally:

        connection.close()



# -------------------------------------------------
# RETRIEVE HISTORY
# -------------------------------------------------

def get_aqi_history(
    location=None,
    start_date=None,
    end_date=None
):
    """
    Retrieve historical AQI records.

    Optional filters:
        location
        start_date
        end_date
    """

    connection = get_connection()

    query = "SELECT * FROM aqi_history WHERE 1=1"

    params = []

    if location:

        query += " AND location = ?"

        params.append(location)

    if start_date:

        query += " AND timestamp >= ?"

        params.append(start_date)

    if end_date:

        query += " AND timestamp < ?"

        params.append(end_date)

    query += " ORDER BY timestamp ASC, id ASC"

    try:

        cursor = connection.cursor()

        cursor.execute(query, params)

        rows = cursor.fetchall()

        records = []

        for row in rows:

            records.append(dict(row))

        return records

    finally:

        connection.close()


# -------------------------------------------------
# GET AVAILABLE LOCATIONS
# -------------------------------------------------

def get_available_locations():
    """
    Return all distinct locations stored in history.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT DISTINCT location
            FROM aqi_history
            ORDER BY location
        """)

        rows = cursor.fetchall()

        locations = []

        for row in rows:

            locations.append(row["location"])

        return locations

    finally:

        connection.close()
