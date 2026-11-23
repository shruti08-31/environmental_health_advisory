
from pprint import pprint

from app.activity_advisor import get_live_activity_advisory


result = get_live_activity_advisory(
    location="Delhi",
    activity="running",
    sensitivity_category="general"
)

print("\n========== OUTDOOR ACTIVITY ADVISORY ==========")

pprint(result)

if result["success"]:

    print("\n========== RECOMMENDATION ==========")
    print(result["recommendation"])

    print("\n========== PRECAUTIONS ==========")

    for item in result["precautions"]:
        print("-", item)

    print("\n========== REASON ==========")
    print(result["reason"])

    print("\n========== ALTERNATIVE ==========")
    print(result["alternative_activity"])

else:

    print("\n========== ERRORS ==========")
    pprint(result["errors"])
