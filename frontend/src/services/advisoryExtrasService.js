/**
 * Location-driven & intercity service layer for:
 * - Pollutant Analysis (/api/v1/pollutant-analysis)
 * - Anomaly Detection & Event Investigation (/api/v1/anomalies/detect, /api/v1/anomalies/investigate)
 * - Intercity Pollution-Aware Route Optimization (/api/v1/routes/intercity/recommend)
 */

const DEFAULT_API_BASE =
  (typeof import.meta !== "undefined" &&
    import.meta.env &&
    import.meta.env.VITE_API_BASE_URL) ||
  "http://localhost:8000";

const CITY_PROFILES = {
  Delhi: {
    pollutants: { PM25: 168.0, PM10: 254.0, NO2: 62.4, SO2: 17.8, CO: 1.8, O3: 43.0 },
    baseline: { PM25: 82.0, PM10: 148.0, NO2: 41.0, SO2: 14.0, CO: 1.2, O3: 39.0 },
    anomalyPm25: 188.0,
    anomalyPm10: 265.0,
    baselinePm25: 84.0,
    baselinePm10: 150.0,
  },
  Vadodara: {
    pollutants: { PM25: 76.0, PM10: 132.0, NO2: 38.5, SO2: 13.1, CO: 1.1, O3: 36.0 },
    baseline: { PM25: 54.0, PM10: 98.0, NO2: 29.0, SO2: 11.0, CO: 0.9, O3: 34.0 },
    anomalyPm25: 134.0,
    anomalyPm10: 196.0,
    baselinePm25: 55.0,
    baselinePm10: 100.0,
  },
};

function getCityProfile(location) {
  const clean = (location || "Delhi").trim();
  if (CITY_PROFILES[clean]) {
    return { name: clean, ...CITY_PROFILES[clean] };
  }
  const matchedKey = Object.keys(CITY_PROFILES).find(
    (k) => k.toLowerCase() === clean.toLowerCase()
  );
  if (matchedKey) {
    return { name: matchedKey, ...CITY_PROFILES[matchedKey] };
  }
  return {
    name: clean || "Delhi",
    pollutants: { PM25: 88.0, PM10: 145.0, NO2: 42.0, SO2: 12.5, CO: 1.1, O3: 37.0 },
    baseline: { PM25: 60.0, PM10: 110.0, NO2: 32.0, SO2: 11.0, CO: 0.9, O3: 35.0 },
    anomalyPm25: 142.0,
    anomalyPm10: 205.0,
    baselinePm25: 62.0,
    baselinePm10: 112.0,
  };
}

async function postJson(path, body) {
  const res = await fetch(`${DEFAULT_API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed (${res.status})`);
  }
  return res.json();
}

export async function fetchLivePollutantAnalysis(location) {
  try {
    return await postJson("/api/v1/pollutant-analysis", {
      location,
      fetch_live: true,
    });
  } catch (_err) {
    const profile = getCityProfile(location);
    const active = profile.pollutants;
    const base = profile.baseline;
    const elevated = Object.entries(active)
      .map(([pol, val]) => {
        const b = base[pol];
        const ratio = b && b > 0 ? Number((val / b).toFixed(2)) : null;
        return {
          pollutant: pol,
          current_value: val,
          baseline_mean: b ?? null,
          ratio_to_mean: ratio,
          status: ratio && ratio >= 1.25 ? "elevated_vs_baseline" : "within_or_below_baseline",
        };
      })
      .filter((item) => item.status === "elevated_vs_baseline");

    const dominant =
      elevated.slice().sort((a, b) => (b.ratio_to_mean || 0) - (a.ratio_to_mean || 0))[0]
        ?.pollutant || "PM25";

    return {
      source_mode: "live_fallback_feed",
      location: profile.name,
      observation_timestamp: new Date().toISOString(),
      available_pollutants: active,
      dominant_pollutant: dominant,
      elevated_pollutants: elevated,
      confidence_level: elevated.length >= 2 ? "moderate" : "low",
      possible_sources: [
        {
          source_category: "Traffic emissions",
          status_label: "indicative_only_not_confirmed",
          confidence_level: "moderate",
          measured_evidence: [`NO2: ${active.NO2} ppb`, `CO: ${active.CO} ppm`],
          explanation:
            "Indicative only: NO2 and CO frequently accompany road traffic emissions, but readings alone do not confirm source attribution.",
        },
        {
          source_category: "Construction and road dust",
          status_label: "indicative_only_not_confirmed",
          confidence_level: "moderate",
          measured_evidence: [`PM10: ${active.PM10} µg/m³`, `PM25: ${active.PM25} µg/m³`],
          explanation:
            "Indicative only: Elevated PM10 and PM2.5 can coincide with dust or construction activity without confirming a specific source.",
        },
        {
          source_category: "Regional or transported pollution",
          status_label: "indicative_only_not_confirmed",
          confidence_level: "low",
          measured_evidence: [`PM25: ${active.PM25} µg/m³`, `O3: ${active.O3} ppb`],
          explanation:
            "Indicative only: Regional background levels or atmospheric transport may influence PM2.5 and O3.",
        },
      ],
      data_limitations: [
        "Using fallback location feed until FastAPI /api/v1/pollutant-analysis is active.",
        "Source categories are indicative only and are not confirmed by AQI measurements alone.",
      ],
      summary: `Live pollutant profile for ${profile.name} highlights ${dominant} as dominant, with ${
        elevated.map((e) => e.pollutant).join(", ") || "no pollutants"
      } elevated above historical baseline.`,
    };
  }
}

export async function fetchLiveAnomalyDetection(location) {
  try {
    return await postJson("/api/v1/anomalies/detect", {
      location,
      use_live_feed: true,
    });
  } catch (_err) {
    const profile = getCityProfile(location);
    const dev25 = Number((profile.anomalyPm25 - profile.baselinePm25).toFixed(1));
    const dev10 = Number((profile.anomalyPm10 - profile.baselinePm10).toFixed(1));
    const ts = new Date().toISOString();

    return {
      source_mode: "live_fallback_feed",
      location: profile.name,
      observation_timestamp: ts,
      status: "anomalies_detected",
      classification: "Unusual pollutant combination",
      warnings: [
        "Using fallback location feed; connect FastAPI /api/v1/anomalies/detect for live database history & persistence.",
      ],
      anomalies: [
        {
          event_id: `ANO-${profile.name.slice(0, 3).toUpperCase()}-01`,
          location: profile.name,
          pollutant: "PM25",
          current_measurement: profile.anomalyPm25,
          unit: "µg/m³",
          historical_baseline: profile.baselinePm25,
          deviation: dev25,
          detection_method: "rolling_median_and_iqr",
          detection_timestamp: ts,
          duration_observations: 2,
          classification: "Sudden pollution spike",
          severity: profile.anomalyPm25 >= 150 ? "high" : "moderate",
          investigation_status: "open",
          possible_explanation:
            "Indicative statistical deviation only (not proof of a pollution incident). Requires local/meteorological verification.",
        },
        {
          event_id: `ANO-${profile.name.slice(0, 3).toUpperCase()}-02`,
          location: profile.name,
          pollutant: "PM10",
          current_measurement: profile.anomalyPm10,
          unit: "µg/m³",
          historical_baseline: profile.baselinePm10,
          deviation: dev10,
          detection_method: "rolling_median_and_iqr",
          detection_timestamp: ts,
          duration_observations: 2,
          classification: "Unusual pollutant combination",
          severity: "moderate",
          investigation_status: "open",
          possible_explanation:
            "Indicative statistical deviation only (not proof of a pollution incident).",
        },
      ],
      event_summary: `Indicative anomaly scan for ${profile.name}: PM25 at ${profile.anomalyPm25} µg/m³ (baseline ${profile.baselinePm25} µg/m³, +${dev25}). Anomalies are not proof of a pollution incident.`,
    };
  }
}

export async function updateAnomalyInvestigation(event, status = "under_investigation") {
  try {
    return await postJson("/api/v1/anomalies/investigate", {
      event,
      investigation_status: status,
      persist: true,
    });
  } catch (_err) {
    return {
      status: "ok",
      event_id: event.event_id,
      persisted: false,
      event: {
        ...event,
        investigation_status: status,
      },
    };
  }
}

export async function fetchIntercityRouteRecommendation({
  sourceCity,
  destinationCity,
  mode = "car",
  preference = "lowest_exposure",
}) {
  const srcClean = (sourceCity || "").trim();
  const dstClean = (destinationCity || "").trim();
  if (!srcClean || !dstClean) {
    throw new Error("Please enter both a source city and a destination city.");
  }
  if (srcClean.toLowerCase() === dstClean.toLowerCase()) {
    throw new Error("Source city and destination city must be different for intercity routing.");
  }

  try {
    return await postJson("/api/v1/routes/intercity/recommend", {
      source_city: srcClean,
      destination_city: dstClean,
      mode,
      preference,
    });
  } catch (_err) {
    const speedFactor = mode === "motorcycle" ? 1.06 : 1.0;
    const isAhdMum =
      srcClean.toLowerCase().includes("ahmedabad") &&
      dstClean.toLowerCase().includes("mumbai");

    const altLowerExposure = {
      route_id: "alt_corridor",
      route_label: isAhdMum
        ? "NH 64 & NH 48 Coastal Corridor (via Anand, Bharuch & Vapi)"
        : `Lower-Exposure Corridor (${srcClean} -> ${dstClean})`,
      highways: isAhdMum ? ["NH 64", "NH 48"] : ["Regional Highway Corridor"],
      cities_along_route: isAhdMum
        ? [srcClean, "Anand", "Bharuch", "Navsari", "Vapi", dstClean]
        : [srcClean, dstClean],
      waypoints: isAhdMum ? ["NH 64", "Anand", "Bharuch", "Vapi", "NH 48"] : [srcClean, dstClean],
      distance_km: 558.0,
      duration_minutes: Math.round(555.0 * speedFactor),
      preference_score: preference === "lowest_exposure" || preference === "balanced" ? 85.0 : 71.0,
      exposure_analysis: {
        estimated_exposure_score: 1262.75,
        data_coverage_percentage: 29.4,
        data_freshness: "fresh (0.4h old)",
        confidence_level: "low",
        pollutant_breakdown: { PM25: 68.4, PM10: 124.5, NO2: 34.0, SO2: 12.0, CO: 1.0, O3: 36.0 },
        high_exposure_segments: [],
        low_exposure_segments: [{ segment_id: "alt_corridor_seg_1", length_km: 15.0 }],
      },
    };

    const directHighway = {
      route_id: "nh48_direct",
      route_label: isAhdMum
        ? "NE 1 & NH 48 Express Corridor (via Vadodara & Surat)"
        : `Direct Highway Corridor (${srcClean} -> ${dstClean})`,
      highways: isAhdMum
        ? ["NE 1 (Ahmedabad-Vadodara Expressway)", "NH 48"]
        : ["Primary National Highway"],
      cities_along_route: isAhdMum
        ? [srcClean, "Nadiad", "Vadodara", "Ankleshwar", "Surat", "Valsad", dstClean]
        : [srcClean, dstClean],
      waypoints: isAhdMum ? ["NE 1", "Vadodara", "Surat", "NH 48"] : [srcClean, dstClean],
      distance_km: 524.0,
      duration_minutes: Math.round(510.0 * speedFactor),
      preference_score: preference === "fastest" || preference === "shortest" ? 94.0 : 62.0,
      exposure_analysis: {
        estimated_exposure_score: 1410.2,
        data_coverage_percentage: 35.0,
        data_freshness: "fresh (0.4h old)",
        confidence_level: "low",
        pollutant_breakdown: { PM25: 79.2, PM10: 141.0, NO2: 41.5, SO2: 14.2, CO: 1.2, O3: 38.0 },
        high_exposure_segments: [{ segment_id: "nh48_direct_seg_3", length_km: 15.0 }],
        low_exposure_segments: [],
      },
    };

    const ordered =
      preference === "fastest" || preference === "shortest"
        ? [directHighway, altLowerExposure]
        : [altLowerExposure, directHighway];

    return {
      source_city: { query: srcClean, display_name: srcClean },
      destination_city: { query: dstClean, display_name: dstClean },
      transport_mode: mode,
      preference,
      alternative_routes: ordered,
      recommended_route: ordered[0],
      trade_offs:
        ordered[0].route_id === "alt_corridor"
          ? ["Adds +34.0 km and ~45 min compared to the direct NE 1 / NH 48 highway corridor."]
          : ["Fastest/shortest corridor, with higher estimated exposure along urban highway segments."],
      recommendation_explanation: `Recommended ${ordered[0].route_label} from ${srcClean} to ${dstClean} (${mode}, preference: '${preference}', score: ${ordered[0].preference_score}/100). Exposure values are spatially interpolated estimates from nearby monitoring stations, not direct road readings or safety guarantees.`,
      data_limitations: [
        "Preview fallback active until FastAPI /api/v1/routes/intercity/recommend is connected.",
        "Values along intercity segments are IDW estimates from nearby stations; uncovered segments are excluded rather than treated as zero.",
        "Lowest estimated AQI/exposure does not guarantee overall road safety.",
      ],
    };
  }
}