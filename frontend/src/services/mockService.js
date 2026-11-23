/**
 * Centralized Mock Backend Service.
 * Simulates the 8 Part-15 backend service outputs so zero domain calculations
 * or severity rules exist inside React UI components.
 */

const LOCATION_DATA = {
  Delhi: {
    location: "Delhi",
    aqi: 214,
    severity: "Very Unhealthy",
    urgency: "High",
    freshness: { is_stale: false, label: "Fresh (4 mins ago)" },
    last_updated: "2026-11-23 19:00:00",
    pollutants: {
      PM25: { value: 142.5, unit: "µg/m³" },
      PM10: { value: 238.0, unit: "µg/m³" },
      NO2: { value: 64.2, unit: "ppb" },
      SO2: { value: 18.4, unit: "ppb" },
      CO: { value: 1.9, unit: "ppm" },
      O3: { value: 41.0, unit: "ppb" }
    }
  },
  Mumbai: {
    location: "Mumbai",
    aqi: 118,
    severity: "Unhealthy for Sensitive Groups",
    urgency: "Moderate",
    freshness: { is_stale: false, label: "Fresh (6 mins ago)" },
    last_updated: "2026-11-23 18:58:00",
    pollutants: {
      PM25: { value: 48.2, unit: "µg/m³" },
      PM10: { value: 94.0, unit: "µg/m³" },
      NO2: { value: 38.5, unit: "ppb" },
      SO2: { value: 12.1, unit: "ppb" },
      CO: { value: 1.1, unit: "ppm" },
      O3: { value: 49.0, unit: "ppb" }
    }
  },
  Bengaluru: {
    location: "Bengaluru",
    aqi: 62,
    severity: "Moderate",
    urgency: "Low",
    freshness: { is_stale: false, label: "Fresh (3 mins ago)" },
    last_updated: "2026-11-23 19:01:00",
    pollutants: {
      PM25: { value: 18.4, unit: "µg/m³" },
      PM10: { value: 44.0, unit: "µg/m³" },
      NO2: { value: 22.0, unit: "ppb" },
      SO2: { value: 7.4, unit: "ppb" },
      CO: { value: 0.6, unit: "ppm" },
      O3: { value: 34.0, unit: "ppb" }
    }
  },
  Vadodara: {
    location: "Vadodara",
    aqi: 136,
    severity: "Unhealthy for Sensitive Groups",
    urgency: "Moderate",
    freshness: { is_stale: false, label: "Fresh (5 mins ago)" },
    last_updated: "2026-11-23 19:00:00",
    pollutants: {
      PM25: { value: 54.0, unit: "µg/m³" },
      PM10: { value: 112.0, unit: "µg/m³" },
      NO2: { value: 31.4, unit: "ppb" },
      SO2: { value: 14.0, unit: "ppb" },
      CO: { value: 1.0, unit: "ppm" },
      O3: { value: 52.0, unit: "ppb" }
    }
  },
  Chennai: {
    location: "Chennai",
    aqi: 44,
    severity: "Good",
    urgency: "Low",
    freshness: { is_stale: false, label: "Fresh (2 mins ago)" },
    last_updated: "2026-11-23 19:02:00",
    pollutants: {
      PM25: { value: 11.2, unit: "µg/m³" },
      PM10: { value: 29.0, unit: "µg/m³" },
      NO2: { value: 15.0, unit: "ppb" },
      SO2: { value: 6.1, unit: "ppb" },
      CO: { value: 0.4, unit: "ppm" },
      O3: { value: 28.0, unit: "ppb" }
    }
  }
};

const GUIDANCE_BY_SEVERITY = {
  Good: {
    summary: "Air quality is satisfactory and poses little or no health risk.",
    precautions: [
      "Normal outdoor activities can proceed without restriction.",
      "Keep indoor spaces ventilated with fresh outdoor air."
    ],
    sensitive_groups: "No special precautions required for sensitive individuals.",
    explanation: "Pollutant concentrations remain well within recommended health thresholds."
  },
  Moderate: {
    summary: "Air quality is acceptable; minor concern for unusually sensitive individuals.",
    precautions: [
      "Unusually sensitive people should monitor for mild respiratory symptoms.",
      "General population can continue regular outdoor routines."
    ],
    sensitive_groups: "People with severe asthma should keep quick-relief inhalers accessible.",
    explanation: "Moderate particulate levels may cause mild irritation during prolonged exertion."
  },
  "Unhealthy for Sensitive Groups": {
    summary: "Members of sensitive groups may experience health effects.",
    precautions: [
      "Reduce prolonged or heavy outdoor exertion.",
      "Take more frequent breaks during outdoor activities.",
      "Close windows during peak traffic hours."
    ],
    sensitive_groups:
      "Children, older adults, pregnant individuals, and people with asthma or heart disease should limit outdoor exposure.",
    explanation:
      "Elevated PM2.5 and O3 concentrations increase airway inflammation risk in vulnerable populations."
  },
  "Very Unhealthy": {
    summary: "Health alert: risk of health effects is increased for everyone.",
    precautions: [
      "Avoid all prolonged or vigorous outdoor physical activity.",
      "Wear a well-fitted N95/KN95 respirator if stepping outdoors.",
      "Run HEPA indoor air purifiers and keep doors/windows sealed."
    ],
    sensitive_groups:
      "Sensitive groups must remain indoors and avoid any physical exertion outdoors.",
    explanation:
      "High fine particulate matter (PM2.5) penetrates deep into the lungs and bloodstream, elevating acute cardiopulmonary stress."
  }
};

const HISTORY_SERIES = {
  daily: [
    { label: "Nov 17", aqi: 168, PM25: 92, PM10: 170, NO2: 48, O3: 39 },
    { label: "Nov 18", aqi: 184, PM25: 108, PM10: 192, NO2: 53, O3: 42 },
    { label: "Nov 19", aqi: 196, PM25: 121, PM10: 205, NO2: 57, O3: 40 },
    { label: "Nov 20", aqi: 175, PM25: 99, PM10: 181, NO2: 50, O3: 44 },
    { label: "Nov 21", aqi: 205, PM25: 132, PM10: 220, NO2: 60, O3: 43 },
    { label: "Nov 22", aqi: 222, PM25: 149, PM10: 245, NO2: 66, O3: 45 },
    { label: "Nov 23", aqi: 214, PM25: 142.5, PM10: 238, NO2: 64.2, O3: 41 }
  ],
  weekly: [
    { label: "Week 1", aqi: 148, PM25: 76, PM10: 145, NO2: 41, O3: 38 },
    { label: "Week 2", aqi: 164, PM25: 89, PM10: 168, NO2: 46, O3: 40 },
    { label: "Week 3", aqi: 189, PM25: 115, PM10: 198, NO2: 55, O3: 42 },
    { label: "Week 4", aqi: 204, PM25: 131, PM10: 221, NO2: 61, O3: 43 }
  ],
  monthly: [
    { label: "Jun", aqi: 92, PM25: 34, PM10: 78, NO2: 26, O3: 44 },
    { label: "Jul", aqi: 78, PM25: 25, PM10: 62, NO2: 22, O3: 35 },
    { label: "Aug", aqi: 84, PM25: 29, PM10: 69, NO2: 24, O3: 37 },
    { label: "Sep", aqi: 116, PM25: 47, PM10: 96, NO2: 33, O3: 41 },
    { label: "Oct", aqi: 174, PM25: 98, PM10: 182, NO2: 52, O3: 45 },
    { label: "Nov", aqi: 208, PM25: 135, PM10: 225, NO2: 62, O3: 42 }
  ]
};

let alertState = {
  enabled: true,
  threshold: 150,
  active: [
    {
      id: "ALT-101",
      type: "Threshold Exceeded",
      location: "Delhi",
      severity: "Very Unhealthy",
      aqi: 214,
      message: "Delhi AQI (214) exceeded configured threshold of 150.",
      timestamp: "2026-11-23 19:00:00"
    },
    {
      id: "ALT-102",
      type: "Rapid AQI Spike",
      location: "Vadodara",
      severity: "Unhealthy for Sensitive Groups",
      aqi: 136,
      message: "Vadodara AQI increased by +32 points over the last 3 hours.",
      timestamp: "2026-11-23 18:30:00"
    }
  ],
  history: [
    {
      id: "ALT-101",
      type: "Threshold Exceeded",
      location: "Delhi",
      severity: "Very Unhealthy",
      aqi: 214,
      message: "Delhi AQI (214) exceeded configured threshold of 150.",
      timestamp: "2026-11-23 19:00:00"
    },
    {
      id: "ALT-102",
      type: "Rapid AQI Spike",
      location: "Vadodara",
      severity: "Unhealthy for Sensitive Groups",
      aqi: 136,
      message: "Vadodara AQI increased by +32 points over the last 3 hours.",
      timestamp: "2026-11-23 18:30:00"
    },
    {
      id: "ALT-099",
      type: "Threshold Exceeded",
      location: "Mumbai",
      severity: "Unhealthy for Sensitive Groups",
      aqi: 156,
      message: "Mumbai AQI (156) exceeded threshold during morning rush hour.",
      timestamp: "2026-11-23 09:15:00"
    },
    {
      id: "ALT-095",
      type: "Threshold Exceeded",
      location: "Delhi",
      severity: "Very Unhealthy",
      aqi: 222,
      message: "Delhi AQI (222) remained in Very Unhealthy range.",
      timestamp: "2026-11-22 20:00:00"
    }
  ]
};

const delay = (ms = 220) => new Promise((resolve) => setTimeout(resolve, ms));

function resolveCity(location) {
  if (!location) return LOCATION_DATA.Delhi;
  const key = Object.keys(LOCATION_DATA).find(
    (city) => city.toLowerCase() === location.trim().toLowerCase()
  );
  if (key) return LOCATION_DATA[key];

  return {
    ...LOCATION_DATA.Vadodara,
    location: location.trim(),
    last_updated: "2026-11-23 19:05:00"
  };
}

export const mockBackendService = {
  async getCurrentAQI(location = "Delhi") {
    await delay();
    return {
      success: true,
      feature: "get_current_aqi",
      data: resolveCity(location)
    };
  },

  async getHealthGuidance(location = "Delhi") {
    await delay();
    const cityData = resolveCity(location);
    const guidance = GUIDANCE_BY_SEVERITY[cityData.severity] || GUIDANCE_BY_SEVERITY.Moderate;
    return {
      success: true,
      feature: "get_health_advisory",
      data: {
        location: cityData.location,
        aqi: cityData.aqi,
        severity: cityData.severity,
        urgency: cityData.urgency,
        ...guidance
      }
    };
  },

  async sendChatMessage(question, location = "Delhi") {
    await delay(350);
    const cityData = resolveCity(location);
    const q = question.toLowerCase();
    let answer = "";
    let intent = "environmental_knowledge";

    if (q.includes("current aqi") || q.includes("air quality")) {
      intent = "live_aqi_query";
      answer = `The current AQI in ${cityData.location} is ${cityData.aqi} (${cityData.severity}), with PM2.5 at ${cityData.pollutants.PM25.value} ${cityData.pollutants.PM25.unit} and PM10 at ${cityData.pollutants.PM10.value} ${cityData.pollutants.PM10.unit}.`;
    } else if (q.includes("difference") && q.includes("pm2.5") && q.includes("pm10")) {
      intent = "rag_knowledge_query";
      answer =
        "PM10 refers to inhalable coarse particles with diameters of 10 micrometers or smaller (such as dust, pollen, and mold), which mainly irritate the eyes, nose, and throat. PM2.5 refers to fine inhalable particles 2.5 micrometers or smaller (from combustion, vehicle exhaust, and industrial emissions) that can penetrate deep into lung alveoli and enter the bloodstream.";
    } else if (q.includes("effects of pm2.5") || q.includes("pm2.5")) {
      intent = "rag_knowledge_query";
      answer =
        "Short-term exposure to elevated PM2.5 can trigger coughing, shortness of breath, eye/throat irritation, and asthma attacks. Long-term exposure increases the risk of reduced lung function, chronic bronchitis, cardiovascular events, and stroke.";
    } else if (q.includes("precaution")) {
      intent = "health_advisory_query";
      const guidance = GUIDANCE_BY_SEVERITY[cityData.severity] || GUIDANCE_BY_SEVERITY.Moderate;
      answer = `For ${cityData.location} (${cityData.severity}, AQI ${cityData.aqi}): ${guidance.precautions.join(" ")} ${guidance.sensitive_groups}`;
    } else {
      answer = `Based on retrieved environmental health guidelines and current monitoring in ${cityData.location} (AQI ${cityData.aqi} — ${cityData.severity}), limiting prolonged outdoor exertion during high particulate periods and monitoring PM2.5 trends helps minimize respiratory exposure.`;
    }

    return {
      success: true,
      feature: "ask_environmental_question",
      data: {
        question,
        location: cityData.location,
        intent,
        answer
      }
    };
  },

  async getAQIHistory(location = "Delhi", period = "daily", dateRange = {}) {
    await delay();
    const series = HISTORY_SERIES[period] || HISTORY_SERIES.daily;
    const values = series.map((item) => item.aqi);
    const avg = Math.round(values.reduce((acc, v) => acc + v, 0) / values.length);
    const max = Math.max(...values);
    const min = Math.min(...values);

    return {
      success: true,
      feature: "get_aqi_history",
      data: {
        location,
        period,
        date_range: dateRange,
        stats: {
          average_aqi: avg,
          max_aqi: max,
          min_aqi: min
        },
        series
      }
    };
  },

  async compareLocations(locations = ["Delhi", "Mumbai", "Bengaluru"]) {
    await delay();
    const items = locations.map((loc) => resolveCity(loc));
    const sorted = [...items].sort((a, b) => b.aqi - a.aqi);
    const highest = sorted[0];
    const lowest = sorted[sorted.length - 1];

    return {
      success: true,
      feature: "compare_locations",
      data: {
        locations: items,
        highest_location: { location: highest.location, aqi: highest.aqi, severity: highest.severity },
        lowest_location: { location: lowest.location, aqi: lowest.aqi, severity: lowest.severity },
        summary: `${highest.location} currently has the highest pollution burden (AQI ${highest.aqi}, ${highest.severity}), which is ${highest.aqi - lowest.aqi} AQI points higher than ${lowest.location} (AQI ${lowest.aqi}, ${lowest.severity}).`
      }
    };
  },

  async getAlerts() {
    await delay(150);
    return {
      success: true,
      feature: "get_alerts",
      data: {
        enabled: alertState.enabled,
        threshold: alertState.threshold,
        active_alerts: alertState.enabled ? alertState.active : [],
        alert_history: alertState.history
      }
    };
  },

  async generateAlerts({ locations = ["Delhi", "Mumbai", "Vadodara"], threshold, enabled }) {
    await delay();
    if (typeof threshold === "number") {
      alertState.threshold = threshold;
    }
    if (typeof enabled === "boolean") {
      alertState.enabled = enabled;
    }

    const triggered = [];
    if (alertState.enabled) {
      locations.forEach((loc, idx) => {
        const city = resolveCity(loc);
        if (city.aqi >= alertState.threshold) {
          const entry = {
            id: `ALT-${200 + idx}`,
            type: "Threshold Exceeded",
            location: city.location,
            severity: city.severity,
            aqi: city.aqi,
            message: `${city.location} AQI (${city.aqi}) exceeded threshold (${alertState.threshold}).`,
            timestamp: "2026-11-23 19:15:00"
          };
          triggered.push(entry);
        }
      });
      alertState.active = triggered;
      alertState.history = [...triggered, ...alertState.history].slice(0, 15);
    } else {
      alertState.active = [];
    }

    return {
      success: true,
      feature: "generate_aqi_alerts",
      data: {
        enabled: alertState.enabled,
        threshold: alertState.threshold,
        active_alerts: alertState.active,
        alert_history: alertState.history
      }
    };
  },

  async getActivityAdvice(location = "Delhi", activity = "Walking") {
    await delay();
    const city = resolveCity(location);
    const isIndoor = activity.toLowerCase().includes("indoor");
    const highPollution = city.aqi > 150;

    let recommendation = "Recommended";
    let precautions = [
      "Stay hydrated and monitor local AQI updates before starting.",
      "Choose routes away from congested roadways."
    ];
    let reason = `Current AQI in ${city.location} is ${city.aqi} (${city.severity}), which supports ${activity.toLowerCase()} with standard awareness.`;
    let alternative = "Light park walk during early morning hours";

    if (isIndoor) {
      recommendation = "Recommended";
      precautions = [
        "Ensure indoor ventilation filters are clean.",
        "Keep windows closed if outdoor AQI is elevated."
      ];
      reason = `Indoor activities minimize direct exposure to outdoor particulate pollution (${city.severity}).`;
      alternative = "Indoor yoga or stationary cycling";
    } else if (highPollution) {
      recommendation = "Not Recommended Outdoors";
      precautions = [
        "Move workout indoors to avoid inhaling elevated PM2.5.",
        "If going outside is unavoidable, wear a fitted N95 mask and keep duration brief."
      ];
      reason = `${city.location} is currently at AQI ${city.aqi} (${city.severity}), increasing respiratory strain during ${activity.toLowerCase()}.`;
      alternative = "Indoor exercise (treadmill, indoor cycling, or bodyweight training)";
    } else if (city.aqi > 100) {
      recommendation = "Proceed with Caution";
      precautions = [
        "Reduce intensity and shorten session duration.",
        "Sensitive individuals should switch to indoor exercise."
      ];
      reason = `AQI ${city.aqi} (${city.severity}) can cause airway irritation during sustained ${activity.toLowerCase()}.`;
      alternative = "Indoor exercise or short low-intensity walk";
    }

    return {
      success: true,
      feature: "get_activity_advice",
      data: {
        location: city.location,
        aqi: city.aqi,
        severity: city.severity,
        activity,
        recommendation,
        precautions,
        reason,
        alternative_activity: alternative
      }
    };
  },

  async getDataQuality(location = "Delhi") {
    await delay();
    const city = resolveCity(location);
    return {
      success: true,
      feature: "get_data_quality_report",
      data: {
        location: city.location,
        data_available: true,
        api_available: true,
        completeness_percentage: 100.0,
        missing_pollutants: [],
        last_updated: city.last_updated,
        freshness_warnings: [],
        status: "GOOD",
        metrics: {
          total_requests: 28,
          successful_requests: 28,
          failed_requests: 0
        }
      }
    };
  }
};
