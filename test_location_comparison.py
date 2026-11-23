
from pprint import pprint

from app.comparison.location_comparison import compare_locations


locations = [
    "Delhi",
    "Mumbai",
    "Pune",
    "Bengaluru"
]


result = compare_locations(locations)


print("\n========== COMPARISON STATUS ==========")
print(result["success"])


print("\n========== LOCATION COMPARISON ==========")
print(
    result["comparison_data"].to_string(index=False)
)


print("\n========== COMPARISON INSIGHTS ==========")
pprint(result["insights"])


print("\n========== UNAVAILABLE LOCATIONS ==========")
pprint(result["errors"])

