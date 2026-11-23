from pprint import pprint

from app.aqi_pipeline import get_aqi_advisory
from app.history.database import (
    create_history_table,
    save_aqi_reading,
    get_aqi_history
)

# create database table
create_history_table()

# get live aqi result
result = get_aqi_advisory("Delhi")

print("\n========== PIPELINE OUTPUT ==========")
pprint(result)

if result.get("success"):

    # save reading
    storage_result = save_aqi_reading(result)

    print("\n========== STORAGE RESULT ==========")
    pprint(storage_result)

    # retrieve saved readings
    history = get_aqi_history(
        location=result.get("location")
    )

    print("\n========== SAVED HISTORY ==========")
    pprint(history)

else:
    print("\nAQI retrieval failed.")
    print(result.get("errors"))