
import pandas as pd

from app.history.database import get_aqi_history


# -------------------------------------------------
# CONVERT HISTORY INTO DATAFRAME
# -------------------------------------------------

def get_history_dataframe(
    location=None,
    start_date=None,
    end_date=None
):
    """
    Retrieve AQI history and convert it into a DataFrame.
    """

    records = get_aqi_history(
        location=location,
        start_date=start_date,
        end_date=end_date
    )

    if not records:

        return pd.DataFrame()

    df = pd.DataFrame(records)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    df["aqi"] = pd.to_numeric(
        df["aqi"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["timestamp", "aqi"]
    )

    return df


# -------------------------------------------------
# CALCULATE AQI STATISTICS
# -------------------------------------------------

def calculate_aqi_statistics(df):
    """
    Calculate overall AQI statistics.
    """

    if df.empty:

        return {
            "total_readings": 0,
            "average_aqi": None,
            "maximum_aqi": None,
            "minimum_aqi": None,
            "most_frequent_severity": None
        }

    severity_counts = df["severity"].dropna().value_counts()

    if severity_counts.empty:

        frequent_severity = None

    else:

        frequent_severity = severity_counts.idxmax()

    return {
        "total_readings": int(len(df)),

        "average_aqi": round(
            float(df["aqi"].mean()), 2
        ),

        "maximum_aqi": float(
            df["aqi"].max()
        ),

        "minimum_aqi": float(
            df["aqi"].min()
        ),

        "most_frequent_severity": frequent_severity
    }


# -------------------------------------------------
# POLLUTANT-WISE AVERAGES
# -------------------------------------------------

def calculate_pollutant_averages(df):
    """
    Calculate average pollutant concentrations.
    """

    pollutants = [
        "pm25",
        "pm10",
        "no2",
        "so2",
        "co",
        "o3"
    ]

    if df.empty:

        return {
            pollutant: None
            for pollutant in pollutants
        }

    averages = {}

    for pollutant in pollutants:

        if pollutant in df.columns:

            value = df[pollutant].mean()

            if pd.isna(value):

                averages[pollutant] = None

            else:

                averages[pollutant] = round(
                    float(value), 2
                )

        else:

            averages[pollutant] = None

    return averages


# -------------------------------------------------
# DAILY ANALYSIS
# -------------------------------------------------

def get_daily_analysis(
    location=None,
    start_date=None,
    end_date=None
):
    """
    Group historical readings by calendar day.
    """

    df = get_history_dataframe(
        location,
        start_date,
        end_date
    )

    if df.empty:

        return pd.DataFrame()

    df["date"] = df["timestamp"].dt.strftime(
        "%Y-%m-%d"
    )

    daily = df.groupby("date").agg(
        average_aqi=("aqi", "mean"),
        maximum_aqi=("aqi", "max"),
        minimum_aqi=("aqi", "min"),
        reading_count=("aqi", "count")
    ).reset_index()

    daily["average_aqi"] = daily[
        "average_aqi"
    ].round(2)

    return daily


# -------------------------------------------------
# WEEKLY ANALYSIS
# -------------------------------------------------

def get_weekly_analysis(
    location=None,
    start_date=None,
    end_date=None
):
    """
    Group historical readings by calendar week.
    """

    df = get_history_dataframe(
        location,
        start_date,
        end_date
    )

    if df.empty:

        return pd.DataFrame()

    df["week_start"] = (
        df["timestamp"]
        .dt.to_period("W-SUN")
        .apply(lambda period: period.start_time)
        .dt.strftime("%Y-%m-%d")
    )

    weekly = df.groupby("week_start").agg(
        average_aqi=("aqi", "mean"),
        maximum_aqi=("aqi", "max"),
        minimum_aqi=("aqi", "min"),
        reading_count=("aqi", "count")
    ).reset_index()

    weekly["average_aqi"] = weekly[
        "average_aqi"
    ].round(2)

    return weekly


# -------------------------------------------------
# MONTHLY ANALYSIS
# -------------------------------------------------

def get_monthly_analysis(
    location=None,
    start_date=None,
    end_date=None
):
    """
    Group historical readings by calendar month.
    """

    df = get_history_dataframe(
        location,
        start_date,
        end_date
    )

    if df.empty:

        return pd.DataFrame()

    df["month"] = df["timestamp"].dt.strftime(
        "%Y-%m"
    )

    monthly = df.groupby("month").agg(
        average_aqi=("aqi", "mean"),
        maximum_aqi=("aqi", "max"),
        minimum_aqi=("aqi", "min"),
        reading_count=("aqi", "count")
    ).reset_index()

    monthly["average_aqi"] = monthly[
        "average_aqi"
    ].round(2)

    return monthly


# -------------------------------------------------
# SEVERITY FREQUENCY
# -------------------------------------------------

def get_severity_distribution(
    location=None,
    start_date=None,
    end_date=None
):
    """
    Calculate the frequency of each severity category.
    """

    df = get_history_dataframe(
        location,
        start_date,
        end_date
    )

    if df.empty:

        return pd.DataFrame(
            columns=["severity", "count"]
        )

    distribution = (
        df["severity"]
        .dropna()
        .value_counts()
        .rename_axis("severity")
        .reset_index(name="count")
    )

    return distribution


# -------------------------------------------------
# LINE CHART DATA
# -------------------------------------------------

def get_aqi_line_chart_data(
    location=None,
    start_date=None,
    end_date=None
):
    """
    Return timestamp-wise AQI data for a line chart.
    """

    df = get_history_dataframe(
        location,
        start_date,
        end_date
    )

    if df.empty:

        return pd.DataFrame(
            columns=["timestamp", "aqi"]
        )

    return df[
        ["timestamp", "aqi"]
    ].sort_values("timestamp").reset_index(drop=True)


# -------------------------------------------------
# BAR CHART DATA
# -------------------------------------------------

def get_aqi_bar_chart_data(
    location=None,
    start_date=None,
    end_date=None,
    period="daily"
):
    """
    Return aggregated AQI data for a bar chart.

    period:
        daily
        weekly
        monthly
    """

    if period == "daily":

        return get_daily_analysis(
            location,
            start_date,
            end_date
        )

    elif period == "weekly":

        return get_weekly_analysis(
            location,
            start_date,
            end_date
        )

    elif period == "monthly":

        return get_monthly_analysis(
            location,
            start_date,
            end_date
        )

    else:

        raise ValueError(
            "Period must be daily, weekly or monthly."
        )


# -------------------------------------------------
# COMPLETE ANALYTICS REPORT
# -------------------------------------------------

def get_aqi_analytics(
    location=None,
    start_date=None,
    end_date=None,
    period="daily"
):
    """
    Generate a complete AQI historical analytics report.
    """

    df = get_history_dataframe(
        location,
        start_date,
        end_date
    )

    if df.empty:

        return {
            "success": True,
            "message": "No historical AQI data available.",
            "statistics": calculate_aqi_statistics(df),
            "pollutant_averages": calculate_pollutant_averages(df),
            "period_analysis": pd.DataFrame(),
            "severity_distribution": pd.DataFrame(),
            "line_chart_data": pd.DataFrame()
        }

    return {
        "success": True,

        "message": "AQI analytics generated successfully.",

        "statistics": calculate_aqi_statistics(df),

        "pollutant_averages": calculate_pollutant_averages(df),

        "period_analysis": get_aqi_bar_chart_data(
            location,
            start_date,
            end_date,
            period
        ),

        "severity_distribution": get_severity_distribution(
            location,
            start_date,
            end_date
        ),

        "line_chart_data": get_aqi_line_chart_data(
            location,
            start_date,
            end_date
        )
    }
