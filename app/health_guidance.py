# ============================================================
# PART 5 - DETERMINISTIC HEALTH GUIDANCE MODULE
# ============================================================
#
# This module converts the deterministic severity result into
# precautionary environmental-health guidance.
#
# IMPORTANT:
# - No LLM is used.
# - No ML model is used.
# - No disease is diagnosed.
# - No medical treatment is recommended.
# - Rules are deterministic and explainable.
# ============================================================


# ------------------------------------------------------------
# SEVERITY-BASED HEALTH RULES
# ------------------------------------------------------------
#
# These rules are based on the Associated Health Impacts table
# supplied for the project.
#
# The wording is kept precautionary rather than diagnostic.
# ------------------------------------------------------------

HEALTH_RULES = {

    "Good": {
        "urgency": "Low",
        "guidance": [
            "Air quality is in the Good range.",
            "No special pollution-related precaution is indicated."
        ],
        "sensitive_groups": []
    },

    "Satisfactory": {
        "urgency": "Low",
        "guidance": [
            "Air quality is in the Satisfactory range.",
            "Sensitive people may experience minor breathing discomfort.",
            "Sensitive people should consider reducing prolonged exposure if they notice discomfort."
        ],
        "sensitive_groups": [
            "Sensitive people"
        ]
    },

    "Moderately polluted": {
        "urgency": "Moderate",
        "guidance": [
            "Air quality is in the Moderately polluted range.",
            "People with existing lung or heart conditions should take extra precaution with prolonged outdoor exposure.",
            "Children and older adults should take extra precaution during prolonged outdoor exposure."
        ],
        "sensitive_groups": [
            "People with lung disease such as asthma",
            "People with heart disease",
            "Children",
            "Older adults"
        ]
    },

    "Poor": {
        "urgency": "High",
        "guidance": [
            "Air quality is in the Poor range.",
            "Reduce prolonged exposure to outdoor air when possible.",
            "People with heart disease should take extra precaution during outdoor exposure."
        ],
        "sensitive_groups": [
            "People with heart disease"
        ]
    },

    "Very Poor": {
        "urgency": "Very High",
        "guidance": [
            "Air quality is in the Very Poor range.",
            "Reduce prolonged exposure to outdoor air when possible.",
            "People with lung or heart conditions should take extra precaution."
        ],
        "sensitive_groups": [
            "People with lung disease",
            "People with heart disease"
        ]
    },

    "Severe": {
        "urgency": "Critical",
        "guidance": [
            "Air quality is in the Severe range.",
            "Reduce exposure to outdoor air when possible.",
            "Avoid prolonged outdoor physical activity, particularly when air quality is severe.",
            "Even healthy people may experience respiratory impact at this severity."
        ],
        "sensitive_groups": [
            "People with lung disease",
            "People with heart disease",
            "Healthy people during outdoor physical activity"
        ]
    }
}


# ------------------------------------------------------------
# POLLUTANT CONDITION RULES
# ------------------------------------------------------------
#
# Pollutant conditions come from Part 4.
#
# We do NOT make disease claims from individual pollutants.
# Instead, elevated pollutant conditions generate a general,
# explainable precaution about exposure.
# ------------------------------------------------------------

POLLUTANT_PRECAUTION_LEVELS = {
    "Poor",
    "Very Poor",
    "Severe"
}


def _invalid_result(reason):
    """
    Return a safe result when the input cannot be used.
    """

    return {
        "urgency": None,
        "guidance": [
            reason
        ],
        "sensitive_groups": []
    }


def _get_severity_rules(severity):
    """
    Get predefined health rules for a severity category.
    """

    return HEALTH_RULES.get(severity)


def _add_pollutant_guidance(
    guidance,
    pollutant_conditions
):
    """
    Add deterministic precautionary guidance when one or more
    pollutants are in a high condition.

    This does not diagnose or claim a specific medical effect.
    """

    elevated_pollutants = []

    for condition in pollutant_conditions:

        if not isinstance(condition, dict):
            continue

        pollutant = condition.get("pollutant")
        condition_level = condition.get("condition")

        if (
            pollutant
            and condition_level in POLLUTANT_PRECAUTION_LEVELS
        ):
            elevated_pollutants.append(
                pollutant
            )

    if not elevated_pollutants:
        return

    pollutant_text = ", ".join(
        elevated_pollutants
    )

    guidance.append(
        "Elevated pollutant conditions were detected for: "
        + pollutant_text
        + ". Consider reducing prolonged exposure to outdoor air."
    )


def generate_health_guidance(
    validation_result,
    severity_result
):
    """
    Generate deterministic precautionary health guidance.

    Parameters
    ----------
    validation_result : dict
        Output from Part 3.

    severity_result : dict
        Output from Part 4.

    Returns
    -------
    dict
        {
            "urgency": "...",
            "guidance": [...],
            "sensitive_groups": [...]
        }
    """

    # --------------------------------------------------------
    # 1. Validate Part 3 result
    # --------------------------------------------------------

    if not isinstance(validation_result, dict):
        return _invalid_result(
            "Health guidance cannot be generated because "
            "the validation result is malformed."
        )

    if validation_result.get("valid") is not True:
        return _invalid_result(
            "Health guidance cannot be generated because "
            "the AQI and pollutant data failed validation."
        )

    # --------------------------------------------------------
    # 2. Validate Part 4 result
    # --------------------------------------------------------

    if not isinstance(severity_result, dict):
        return _invalid_result(
            "Health guidance cannot be generated because "
            "the severity result is malformed."
        )

    severity = severity_result.get(
        "severity"
    )

    if severity is None:
        return _invalid_result(
            "Health guidance cannot be generated because "
            "severity is unavailable."
        )

    # --------------------------------------------------------
    # 3. Get predefined severity rules
    # --------------------------------------------------------

    severity_rules = _get_severity_rules(
        severity
    )

    if severity_rules is None:
        return _invalid_result(
            "No health guidance rule exists for severity: "
            + str(severity)
        )

    # --------------------------------------------------------
    # 4. Copy predefined guidance
    # --------------------------------------------------------

    guidance = list(
        severity_rules["guidance"]
    )

    sensitive_groups = list(
        severity_rules["sensitive_groups"]
    )

    # --------------------------------------------------------
    # 5. Get pollutant conditions from Part 4
    # --------------------------------------------------------

    pollutant_conditions = (
        severity_result.get(
            "pollutant_conditions",
            []
        )
    )

    if not isinstance(
        pollutant_conditions,
        list
    ):
        pollutant_conditions = []

    # --------------------------------------------------------
    # 6. Add pollutant-based precaution
    # --------------------------------------------------------

    _add_pollutant_guidance(
        guidance,
        pollutant_conditions
    )

    # --------------------------------------------------------
    # 7. Return standard Part 5 output
    # --------------------------------------------------------

    return {
        "urgency": severity_rules["urgency"],
        "guidance": guidance,
        "sensitive_groups": sensitive_groups
    }