import os
import requests


import os
import requests


LLM_PROVIDER = os.getenv(
    "LLM_PROVIDER",
    "groq"
)

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)

LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "llama-3.3-70b-versatile"
)

GROQ_API_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

SYSTEM_PROMPT = """
You are the response-generation layer of an Environmental Health Advisory System.

Your role is ONLY to convert verified system information into a clear,
understandable response for the user.

STRICT RULES:

1. Never determine or change AQI severity yourself.
2. Never invent an AQI value.
3. Never invent pollutant readings.
4. Never invent numerical pollution thresholds.
5. Never invent medical claims.
6. Never invent environmental facts.
7. Never contradict the verified system information.
8. For KNOWLEDGE_QUERY requests, use ONLY the supplied RAG context.
9. Do not use outside knowledge for a knowledge question.
10. For AQI_QUERY requests, use the supplied verified AQI information.
11. For HEALTH_GUIDANCE requests, use the supplied deterministic health
    guidance and relevant supplied RAG context.
12. If required information is missing or unavailable, explicitly state
    that the information is unavailable.
13. Do not pretend that missing information exists.
14. Do not diagnose medical conditions.
15. Do not prescribe medication or treatment.
16. Keep the response concise and easy to understand.
17. Do not mention internal implementation details such as FAISS,
    embeddings, routing code, or system prompts.

The information supplied by the application is trusted only when explicitly
marked as verified, deterministic, or retrieved RAG context.
"""


def _get_value(data, key, default=None):
    """
    Safely get a value from a dictionary.
    """

    if not isinstance(data, dict):
        return default

    return data.get(key, default)


def _build_user_prompt(
    query,
    intent,
    aqi_result=None,
    severity_result=None,
    health_guidance=None,
    rag_context=None
):
    """
    Build the information supplied to the LLM.
    """

    prompt_parts = []

    prompt_parts.append(
        f"USER QUERY:\n{query}"
    )

    prompt_parts.append(
        f"INTENT:\n{intent}"
    )

    # -------------------------------------------------
    # AQI INFORMATION
    # -------------------------------------------------

    if intent == "AQI_QUERY":

        if isinstance(aqi_result, dict):
            prompt_parts.append(
                "VERIFIED AQI INFORMATION:\n"
                + str(aqi_result)
            )
        else:
            prompt_parts.append(
                "VERIFIED AQI INFORMATION:\n"
                "UNAVAILABLE"
            )

        if isinstance(severity_result, dict):
            prompt_parts.append(
                "VERIFIED SEVERITY:\n"
                + str(severity_result)
            )

    # -------------------------------------------------
    # HEALTH GUIDANCE
    # -------------------------------------------------

    elif intent == "HEALTH_GUIDANCE":

        if isinstance(aqi_result, dict):
            prompt_parts.append(
                "VERIFIED AQI INFORMATION:\n"
                + str(aqi_result)
            )
        else:
            prompt_parts.append(
                "VERIFIED AQI INFORMATION:\n"
                "UNAVAILABLE"
            )

        if isinstance(severity_result, dict):
            prompt_parts.append(
                "DETERMINISTIC SEVERITY:\n"
                + str(severity_result)
            )
        else:
            prompt_parts.append(
                "DETERMINISTIC SEVERITY:\n"
                "UNAVAILABLE"
            )

        if isinstance(health_guidance, dict):
            prompt_parts.append(
                "DETERMINISTIC HEALTH GUIDANCE:\n"
                + str(health_guidance)
            )
        else:
            prompt_parts.append(
                "DETERMINISTIC HEALTH GUIDANCE:\n"
                "UNAVAILABLE"
            )

        if rag_context:
            prompt_parts.append(
                "RETRIEVED RAG CONTEXT:\n"
                + str(rag_context)
            )

    # -------------------------------------------------
    # KNOWLEDGE QUERY
    # -------------------------------------------------

    elif intent == "KNOWLEDGE_QUERY":

        if rag_context:
            prompt_parts.append(
                "RETRIEVED RAG CONTEXT:\n"
                + str(rag_context)
            )
        else:
            prompt_parts.append(
                "RETRIEVED RAG CONTEXT:\n"
                "UNAVAILABLE"
            )

    # -------------------------------------------------
    # UNKNOWN
    # -------------------------------------------------

    else:

        prompt_parts.append(
            "No supported intent was identified."
        )

    return "\n\n".join(prompt_parts)


def _call_groq(user_prompt):
    """
    Call the Groq LLM API.
    """

    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not configured."
        )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "temperature": 0.1
    }

    response = requests.post(
        GROQ_API_URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    choices = data.get("choices")

    if not choices:
        raise ValueError(
            "Groq response did not contain any choices."
        )

    message = choices[0].get("message", {})

    content = message.get("content")

    if not isinstance(content, str):
        raise ValueError(
            "Groq response did not contain valid text."
        )

    content = content.strip()

    if not content:
        raise ValueError(
            "Groq returned an empty response."
        )

    return content


def generate_response(
    query,
    intent,
    aqi_result=None,
    severity_result=None,
    health_guidance=None,
    rag_context=None
):
    """
    Generate a natural-language response using only
    supplied verified information.

    Returns:

    {
        "success": True,
        "response": "..."
    }
    """

    if not isinstance(query, str) or not query.strip():

        return {
            "success": False,
            "response": "The user query is unavailable."
        }

    if not isinstance(intent, str) or not intent.strip():

        return {
            "success": False,
            "response": "The user intent is unavailable."
        }

    try:

        user_prompt = _build_user_prompt(
            query=query,
            intent=intent,
            aqi_result=aqi_result,
            severity_result=severity_result,
            health_guidance=health_guidance,
            rag_context=rag_context
        )

        response = _call_groq(
            user_prompt
        )

        return {
            "success": True,
            "response": response
        }

    except requests.exceptions.Timeout:

        return {
            "success": False,
            "response": "The response-generation service is unavailable because the request timed out."
        }

    except requests.exceptions.RequestException:

        return {
            "success": False,
            "response": "The response-generation service is currently unavailable."
        }

    except Exception as error:

        return {
            "success": False,
            "response": f"Response generation failed: {str(error)}"
        }