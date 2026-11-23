
from pprint import pprint

from app.monitoring.data_quality import (
    monitor_aqi_data,
    get_monitoring_history,
    get_request_statistics
)


location = "Delhi"

# Run one monitoring check
result = monitor_aqi_data(location)

print("\n========== AQI DATA QUALITY ==========")

pprint(result)

print("\n========== MONITORING HISTORY ==========")

history = get_monitoring_history(
    location=location,
    limit=5
)

pprint(history)

print("\n========== REQUEST STATISTICS ==========")

statistics = get_request_statistics(
    location=location
)

pprint(statistics)
