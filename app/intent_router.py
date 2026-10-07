import re


AQI_QUERY = "AQI_QUERY"
HEALTH_GUIDANCE = "HEALTH_GUIDANCE"
KNOWLEDGE_QUERY = "KNOWLEDGE_QUERY"
UNKNOWN = "UNKNOWN"


AQI_KEYWORDS = [
    "aqi",
    "air quality",
    "current air quality",
    "current aqi",
    "air pollution level",
    "pollution level",
]

HEALTH_KEYWORDS = [
    "what should i do",
    "what can i do",
    "what precautions",
    "precautions",
    "precaution",
    "what should i take",
    "is it safe",
    "safe",
    "should i go outside",
    "can i go outside",
    "how can i protect",
    "how to protect",
    "protect myself",
    "protect my health",
    "health advice",
    "health guidance",
    "what should we do",
]

KNOWLEDGE_KEYWORDS = [
    "tell me about",
    "what is",
    "what are",
    "effects of",
    "health effects",
    "impact of",
    "meaning of",
    "explain",
    "information about",
]

POLLUTANT_KEYWORDS = [
    "pm2.5",
    "pm25",
    "pm10",
    "no2",
    "so2",
    "o3",
    "co",
    "vocs",
    "nh3",
]


def _clean_query(query):
    """
    Clean and normalize the user query.
    """

    if not isinstance(query, str):
        return None

    query = query.strip()

    if not query:
        return None

    query = re.sub(r"\s+", " ", query)

    return query


def _contains_keyword(query, keywords):
    """
    Check whether any keyword or phrase exists in the query.
    """

    query = query.lower()

    for keyword in keywords:
        if keyword in query:
            return True

    return False


def route_intent(query):
    """
    Route a user query to one of the supported intents.

    Returns:
        {
            "intent": "...",
            "query": "...",
            "confidence": ...,
            "needs_location": True/False
        }
    """

    cleaned_query = _clean_query(query)

    # Handle empty or invalid queries
    if cleaned_query is None:
        return {
            "intent": UNKNOWN,
            "query": "",
            "confidence": 0.0,
            "needs_location": False
        }

    query_lower = cleaned_query.lower()

    # -------------------------------------------------
    # 1. HEALTH GUIDANCE
    # -------------------------------------------------
    #
    # Health/action words get priority because queries
    # such as "Is the air quality safe?" are asking
    # for advice rather than only asking for AQI.
    #
    if _contains_keyword(query_lower, HEALTH_KEYWORDS):

        return {
            "intent": HEALTH_GUIDANCE,
            "query": cleaned_query,
            "confidence": 0.95,
            "needs_location": True
        }

    # -------------------------------------------------
    # 2. AQI QUERY
    # -------------------------------------------------

    if _contains_keyword(query_lower, AQI_KEYWORDS):

        return {
            "intent": AQI_QUERY,
            "query": cleaned_query,
            "confidence": 0.95,
            "needs_location": True
        }

    # -------------------------------------------------
    # 3. KNOWLEDGE QUERY
    # -------------------------------------------------

    has_pollutant = _contains_keyword(
        query_lower,
        POLLUTANT_KEYWORDS
    )

    has_knowledge_phrase = _contains_keyword(
        query_lower,
        KNOWLEDGE_KEYWORDS
    )

    if has_pollutant and has_knowledge_phrase:

        return {
            "intent": KNOWLEDGE_QUERY,
            "query": cleaned_query,
            "confidence": 0.95,
            "needs_location": False
        }

    # A pollutant name alone is also treated as
    # a knowledge query.
    if has_pollutant:

        return {
            "intent": KNOWLEDGE_QUERY,
            "query": cleaned_query,
            "confidence": 0.85,
            "needs_location": False
        }

    # -------------------------------------------------
    # 4. AMBIGUOUS / UNKNOWN QUERY
    # -------------------------------------------------

    return {
        "intent": UNKNOWN,
        "query": cleaned_query,
        "confidence": 0.0,
        "needs_location": False
    }