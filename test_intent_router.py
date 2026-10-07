from app.intent_router import route_intent


def print_result(test_name, query):

    result = route_intent(query)

    print()
    print("=" * 60)
    print(test_name)
    print("=" * 60)

    print("Query:", query)
    print("Intent:", result["intent"])
    print("Confidence:", result["confidence"])
    print("Needs Location:", result["needs_location"])


def main():

    # -------------------------------------------------
    # AQI QUERY TESTS
    # -------------------------------------------------

    print_result(
        "AQI TEST 1",
        "What is the AQI?"
    )

    print_result(
        "AQI TEST 2",
        "What is the current AQI?"
    )

    print_result(
        "AQI TEST 3",
        "Tell me the current air quality."
    )

    # -------------------------------------------------
    # HEALTH GUIDANCE TESTS
    # -------------------------------------------------

    print_result(
        "HEALTH TEST 1",
        "What should I do?"
    )

    print_result(
        "HEALTH TEST 2",
        "What precautions should I take?"
    )

    print_result(
        "HEALTH TEST 3",
        "Is the air quality safe?"
    )

    # -------------------------------------------------
    # KNOWLEDGE QUERY TESTS
    # -------------------------------------------------

    print_result(
        "KNOWLEDGE TEST 1",
        "Tell me about PM2.5."
    )

    print_result(
        "KNOWLEDGE TEST 2",
        "What are the effects of PM10?"
    )

    print_result(
        "KNOWLEDGE TEST 3",
        "What is NO2?"
    )

    # -------------------------------------------------
    # AMBIGUOUS TESTS
    # -------------------------------------------------

    print_result(
        "AMBIGUOUS TEST 1",
        "Tell me about pollution."
    )

    print_result(
        "AMBIGUOUS TEST 2",
        "What about the air?"
    )

    print_result(
        "AMBIGUOUS TEST 3",
        "Help me."
    )

    # -------------------------------------------------
    # INVALID / EMPTY TESTS
    # -------------------------------------------------

    print_result(
        "EMPTY TEST",
        ""
    )

    print_result(
        "INVALID TEST",
        None
    )


if __name__ == "__main__":
    main()