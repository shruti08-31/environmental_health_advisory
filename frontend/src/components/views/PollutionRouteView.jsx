import React, { useEffect, useState } from "react";
import { fetchIntercityRouteRecommendation } from "../../services/advisoryExtrasService";

export function PollutionRouteView({ selectedLocation = "Delhi" }) {
  const [sourceCity, setSourceCity] = useState("Ahmedabad, Gujarat");
  const [destinationCity, setDestinationCity] = useState(
    selectedLocation.toLowerCase().includes("mumbai")
      ? "Ahmedabad, Gujarat"
      : "Mumbai, Maharashtra"
  );
  const [mode, setMode] = useState("car");
  const [preference, setPreference] = useState("lowest_exposure");
  const [routeData, setRouteData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const runPlan = async (src = sourceCity, dst = destinationCity, m = mode, pref = preference) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetchIntercityRouteRecommendation({
        sourceCity: src,
        destinationCity: dst,
        mode: m,
        preference: pref,
      });
      setRouteData(res);
    } catch (err) {
      setError(err.message || "Unable to plan intercity route.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runPlan(sourceCity, destinationCity, mode, preference);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, preference]);

  const handleSubmit = (e) => {
    e.preventDefault();
    runPlan(sourceCity, destinationCity, mode, preference);
  };

  const recommended = routeData?.recommended_route;

  return (
    <div className="view-stack">
      <div className="page-header-row">
        <div>
          <h2>Intercity Pollution-Aware Routes</h2>
          <p className="muted-text">
            Compare intercity corridors across estimated pollution exposure, distance, and
            travel time (no manual lat/lon entry)
          </p>
        </div>
      </div>

      <form className="surface-card controls-bar" onSubmit={handleSubmit}>
        <div className="control-group">
          <label className="tile-label" htmlFor="intercity-source">
            Source City
          </label>
          <input
            id="intercity-source"
            type="text"
            className="text-input"
            value={sourceCity}
            onChange={(e) => setSourceCity(e.target.value)}
            placeholder="e.g. Ahmedabad, Gujarat"
            required
          />
        </div>

        <div className="control-group">
          <label className="tile-label" htmlFor="intercity-dest">
            Destination City
          </label>
          <input
            id="intercity-dest"
            type="text"
            className="text-input"
            value={destinationCity}
            onChange={(e) => setDestinationCity(e.target.value)}
            placeholder="e.g. Mumbai, Maharashtra"
            required
          />
        </div>

        <div className="control-group">
          <span className="tile-label">Transport Mode</span>
          <div className="chip-row">
            {[
              { id: "car", label: "Car" },
              { id: "motorcycle", label: "Motorcycle" },
            ].map((m) => (
              <button
                key={m.id}
                type="button"
                className={`chip-btn ${mode === m.id ? "active" : ""}`}
                onClick={() => setMode(m.id)}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>

        <div className="control-group">
          <span className="tile-label">Route Preference</span>
          <div className="chip-row">
            {[
              { id: "lowest_exposure", label: "Lowest Exposure (Est.)" },
              { id: "balanced", label: "Balanced" },
              { id: "fastest", label: "Fastest" },
              { id: "shortest", label: "Shortest" },
            ].map((p) => (
              <button
                key={p.id}
                type="button"
                className={`chip-btn ${preference === p.id ? "active" : ""}`}
                onClick={() => setPreference(p.id)}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div className="control-group align-end">
          <button type="submit" className="chip-btn active" disabled={loading}>
            {loading ? "Planning..." : "Compare Intercity Routes"}
          </button>
        </div>
      </form>

      {loading && <div className="surface-card">Evaluating intercity segments and nearby stations...</div>}
      {error && <div className="surface-card error-card">{error}</div>}

      {!loading && routeData && (
        <>
          {recommended && (
            <div className="surface-card highlight-card">
              <div className="row-top">
                <div>
                  <span className="tile-label">RECOMMENDED INTERCITY ROUTE</span>
                  <h3>{recommended.route_label || recommended.route_id}</h3>
                </div>
                <span className="status-badge">
                  Score {recommended.preference_score ?? "—"}/100
                </span>
              </div>

              <div className="route-corridor-box">
                <div>
                  <strong>Highways:</strong>{" "}
                  {(recommended.highways || []).length
                    ? recommended.highways.join(" • ")
                    : "Highway metadata unavailable from provider"}
                </div>
                <div>
                  <strong>Cities Along Route:</strong>{" "}
                  {(recommended.cities_along_route || []).length
                    ? recommended.cities_along_route.join(" → ")
                    : `${sourceCity} → ${destinationCity}`}
                </div>
              </div>

              <p>{routeData.recommendation_explanation}</p>
              <div className="meta-row">
                <span>
                  <strong>Distance:</strong> {recommended.distance_km} km
                </span>
                <span>
                  <strong>Duration:</strong> ~{recommended.duration_minutes} min
                </span>
                <span>
                  <strong>Est. Exposure Score:</strong>{" "}
                  {recommended.exposure_analysis?.estimated_exposure_score ?? "Insufficient data"}
                </span>
                <span>
                  <strong>Coverage:</strong>{" "}
                  {recommended.exposure_analysis?.data_coverage_percentage ?? 0}%
                </span>
                <span>
                  <strong>Confidence:</strong>{" "}
                  {recommended.exposure_analysis?.confidence_level || "low"}
                </span>
              </div>
              {!!(routeData.trade_offs || []).length && (
                <p className="muted-text">
                  <strong>Trade-offs:</strong> {routeData.trade_offs.join(" • ")}
                </p>
              )}
            </div>
          )}

          <div className="surface-card">
            <h3>Alternative Intercity Routes</h3>
            <div className="card-list">
              {(routeData.alternative_routes || []).map((rt, i) => {
                const ea = rt.exposure_analysis || {};
                return (
                  <div key={rt.route_id || i} className="list-row-card">
                    <div className="row-top">
                      <strong>{rt.route_label || rt.route_id}</strong>
                      <span className="pill-tag">
                        Preference Score: {rt.preference_score ?? "—"}/100
                      </span>
                    </div>

                    <div className="route-corridor-box">
                      <div>
                        <strong>Highways:</strong>{" "}
                        {(rt.highways || []).length
                          ? rt.highways.join(" • ")
                          : "Highway metadata unavailable"}
                      </div>
                      <div>
                        <strong>Cities Along Route:</strong>{" "}
                        {(rt.cities_along_route || []).length
                          ? rt.cities_along_route.join(" → ")
                          : (rt.waypoints || []).join(" → ") || `${sourceCity} → ${destinationCity}`}
                      </div>
                    </div>

                    <div className="meta-row">
                      <span>Distance: {rt.distance_km} km</span>
                      <span>Duration: ~{rt.duration_minutes} min</span>
                      <span>Est. Exposure: {ea.estimated_exposure_score ?? "N/A"}</span>
                      <span>Coverage: {ea.data_coverage_percentage ?? 0}%</span>
                      <span>Freshness: {ea.data_freshness || "unknown"}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {!!(routeData.data_limitations || []).length && (
            <div className="surface-card">
              <h4>Data Limitations &amp; Methodology Notes</h4>
              <ul className="clean-list">
                {routeData.data_limitations.map((lim, i) => (
                  <li key={i}>{lim}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}