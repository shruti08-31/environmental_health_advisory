from app.llm_generator import generate_response


def print_result(test_name, result):

    print()
    print("=" * 60)
    print(test_name)
    print("=" * 60)

    print("Success:", result["success"])
    print("Response:")
    print(result["response"])


def main():

    # -------------------------------------------------
    # AQI QUERY
    # -------------------------------------------------

    aqi_result = {
        "location": "Delhi",
        "aqi": 144.0,
        "pollutants": {
            "pm25": 144.0,
            "pm10": 85.0,
            "no2": 9.6,
            "so2": 4.3,
            "co": 12.2,
            "o3": 19.6
        },
        "timestamp": "2026-10-07 15:00:00"
    }

    severity_result = {
        "severity": "Moderately polluted",
        "reason": (
            "AQI value 144.0 falls in the "
            "'Moderately polluted' category."
        )
    }

    result = generate_response(
        query="What is the current AQI?",
        intent="AQI_QUERY",
        aqi_result=aqi_result,
        severity_result=severity_result
    )

    print_result(
        "AQI QUERY TEST",
        result
    )

    # -------------------------------------------------
    # HEALTH GUIDANCE
    # -------------------------------------------------

    health_guidance = {
        "urgency": "Moderate",
        "guidance": [
            "Air quality is in the Moderately polluted range.",
            "People with existing lung or heart conditions "
            "should take extra precaution with prolonged "
            "outdoor exposure.",
            "Children and older adults should take extra "
            "precaution during prolonged outdoor exposure."
        ],
        "sensitive_groups": [
            "People with lung disease such as asthma",
            "People with heart disease",
            "Children",
            "Older adults"
        ]
    }

    rag_context = [
        {
            "text": (
                "PM2.5 can penetrate deeply into the lungs "
                "and is associated with cardiovascular and "
                "respiratory effects."
            ),
            "score": 0.72
        }
    ]

    result = generate_response(
        query="What precautions should I take?",
        intent="HEALTH_GUIDANCE",
        aqi_result=aqi_result,
        severity_result=severity_result,
        health_guidance=health_guidance,
        rag_context=rag_context
    )

    print_result(
        "HEALTH GUIDANCE TEST",
        result
    )

    # -------------------------------------------------
    # KNOWLEDGE QUERY
    # -------------------------------------------------

    rag_context = [
        {
            "text": (
                "PM2.5 are fine particles with an "
                "aerodynamic diameter of 2.5 micrometres "
                "or smaller. They can penetrate deeply "
                "into the lungs."
            ),
            "score": 0.81
        },
        {
            "text": (
                "Short-term exposure to air pollution can "
                "include coughing, wheezing, and shortness "
                "of breath."
            ),
            "score": 0.55
        }
    ]

    result = generate_response(
        query="Tell me about PM2.5.",
        intent="KNOWLEDGE_QUERY",
        rag_context=rag_context
    )

    print_result(
        "KNOWLEDGE QUERY TEST",
        result
    )

    # -------------------------------------------------
    # MISSING RAG CONTEXT
    # -------------------------------------------------

    result = generate_response(
        query="What are the effects of PM2.5?",
        intent="KNOWLEDGE_QUERY",
        rag_context=None
    )

    print_result(
        "MISSING RAG CONTEXT TEST",
        result
    )


if __name__ == "__main__":
    main()