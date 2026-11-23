from pprint import pprint
from app.history.analytics import get_aqi_line_chart_data
from app.history.analytics import get_daily_analysis
from app.history.analytics import get_monthly_analysis
from app.history.analytics import get_severity_distribution
from app.history.analytics import get_weekly_analysis
from app.history.analytics import (
    get_history_dataframe,
    calculate_aqi_statistics,
    calculate_pollutant_averages
)
# fetch history
df = get_history_dataframe()

print("\n========== HISTORY DATAFRAME ==========")
print(df)

# calculate statistics
statistics = calculate_aqi_statistics(df)

print("\n========== OVERALL AQI STATISTICS ==========")
pprint(statistics)

pollutant_averages = calculate_pollutant_averages(df)

print("\n========== POLLUTANT AVERAGES ==========")
pprint(pollutant_averages)

daily = get_daily_analysis()

print("\n========== DAILY ANALYSIS ==========")
print(daily.to_string(index=False))

weekly = get_weekly_analysis()

print("\n========== WEEKLY ANALYSIS ==========")
print(weekly.to_string(index=False))

monthly = get_monthly_analysis()

print("\n========== MONTHLY ANALYSIS ==========")
print(monthly.to_string(index=False))

severity = get_severity_distribution()

print("\n========== SEVERITY DISTRIBUTION ==========")
pprint(severity)

line_data = get_aqi_line_chart_data()

print("\n========== AQI LINE CHART DATA ==========")
print(line_data)