
from pprint import pprint

from app.alerts.alert_engine import (
    initialize_alert_tables,
    configure_default_alert_rules,
    evaluate_multiple_locations,
    get_alert_history
)


# 1. Initialize SQLite alert tables.
initialize_alert_tables()


# 2. Configure default rules.
# Run this once initially, not on every monitoring call.
locations = [
    "Delhi",
    "Mumbai",
    "Pune",
    "Bengaluru"
]

configure_default_alert_rules(
    locations,
    aqi_threshold=100,
    increase_threshold=50
)


# 3. Evaluate current AQI for all locations.
result = evaluate_multiple_locations(locations)

print("\n========== MONITORING RESULT ==========")
pprint(result)


# 4. Retrieve stored alert history.
history = get_alert_history(limit=50)

print("\n========== ALERT HISTORY ==========")
pprint(history)
