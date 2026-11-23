import React, { useState } from "react";
import {
  fetchPollutantAnalysis,
  fetchPollutionRoute,
  investigateAnomalyItem,
  runAnomalyScan,
} from "../../services/advisoryExtrasService";

export default function AdvancedModulesView({
  defaultLocation = "Delhi",
  initialTab = "pollutants",
}) {
  const [activeTab, setActiveTab] = useState(initialTab);

  // 1. Pollutant Analysis state
  const [polLocation, setPolLocation] = useState(defaultLocation);
  const [pm25, setPm25] = useState("94.0");
  const [pm10, setPm10] = useState("158.0");
  const [no2, setNo2] = useState("46.5");
  const [so2, setSo2] = useState("14.2");
  const [co, setCo] = useState("1.3");
  const [o3, setO3] = useState("37.0");
  const [polReport, setPolReport] = useState(null);
  const [polLoading, setPolLoading] = useState(false);

  // 2. Anomaly Detection state
  const [anomLocation, setAnomLocation] = useState(defaultLocation);
  const [anomPm25, setAnomPm25] = useState("175.0");
  const [anomPm10, setAnomPm10] = useState("240.0");
  const [contextNote, setContextNote] = useState("");
  const [anomResult, setAnomResult] = useState(null);
  const [anomLoading, setAnomLoading] = useState(false);

  // 3. Pollution-Aware Route Optimizer state (defaulting around Vadodara coordinates)
  const [originLat, setOriginLat] = useState("22.3072");
  const [originLon, setOriginLon] = useState("73.1812");
  const [destLat, setDestLat] = useState("22.3180");
  const [destLon, setDestLon] = useState("73.1980");
  const [mode, setMode] = useState("walking");
  const [preference, setPreference] = useState("lowest_exposure");
  const [routeResult, setRouteResult] = useState(null);
  const [routeLoading, setRouteLoading] = useState(false);

  const [errorMsg, setErrorMsg] = useState("");

  const handlePollutantSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    setPolLoading(true);
    try {
      const parseVal = (v) => (v === "" ? null : Number(v));
      const data = await fetchPollutantAnalysis({
        location: polLocation,
        pollutants: {
          PM25: parseVal(pm25),
          PM10: parseVal(pm10),
          NO2: parseVal(no2),
          SO2: parseVal(so2),
          CO: parseVal(co),
          O3: parseVal(o3),
        },
      });
      setPolReport(data);
    } catch (err) {
      setErrorMsg(err.message || "Pollutant analysis failed.");
    } finally {
      setPolLoading(false);
    }
  };

  const handleAnomalySubmit = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    setAnomLoading(true);
    try {
      const data = await runAnomalyScan({
        location: anomLocation,
        currentReading: {
          location: anomLocation,
          timestamp: new Date().toISOString(),
          pollutants: {
            PM25: anomPm25 === "" ? null : Number(anomPm25),
            PM10: anomPm10 === "" ? null : Number(anomPm10),
          },
        },
      });
      setAnomResult(data);
    } catch (err) {
      setErrorMsg(err.message || "Anomaly detection failed.");
    } finally {
      setAnomLoading(false);
    }
  };

  const handleInvestigate = async (item, index) => {
    setErrorMsg("");
    try {
      const updated = await investigateAnomalyItem(item, contextNote);
      if (anomResult && updated?.event) {
        const nextAnomalies = anomResult.anomalies.map((ev, idx) =>
          idx === index ? updated.event : ev
        );
        setAnomResult({ ...anomResult, anomalies: nextAnomalies });
      }
    } catch (err) {
      setErrorMsg(err.message || "Event investigation update failed.");
    }
  };

  const handleRouteSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    setRouteLoading(true);
    try {
      const data = await fetchPollutionRoute({
        originLat,
        originLon,
        destLat,
        destLon,
        mode,
        preference,
      });
      setRouteResult(data);
    } catch (err) {
      setErrorMsg(err.message || "Route optimization failed.");
    } finally {
      setRouteLoading(false);
    }
  };

  return (
    <section className="adv-modules-view">
      <header className="adv-header">
        <h2>Pollutant Insights, Anomaly Monitor &amp; Exposure Route Planner</h2>
        <p className="adv-subtitle">
          Source insights are indicative only; statistical anomalies are not confirmed
          incidents; route exposure values are proximity estimates, not medical readings.
        </p>
        <div className="adv-tabs" role="tablist">
          <button
            type="button"
            className={activeTab === "pollutants" ? "adv-tab active" : "adv-tab"}
            onClick={() => setActiveTab("pollutants")}
          >
            Pollutant Analysis
          </button>
          <button
            type="button"
            className={activeTab === "anomalies" ? "adv-tab active" : "adv-tab"}
            onClick={() => setActiveTab("anomalies")}
          >
            Anomaly Detection
          </button>
          <button
            type="button"
            className={activeTab === "routes" ? "adv-tab active" : "adv-tab"}
            onClick={() => setActiveTab("routes")}
          >
            Pollution-Aware Routes
          </button>
        </div>
      </header>

      {errorMsg && <div className="adv-alert-error">{errorMsg}</div>}

      {activeTab === "pollutants" && (
        <div className="adv-panel">
          <form className="adv-form-grid" onSubmit={handlePollutantSubmit}>
            <label>
              Location
              <input value={polLocation} onChange={(e) => setPolLocation(e.target.value)} required />
            </label>
            <label>
              PM2.5 (µg/m³)
              <input type="number" step="any" value={pm25} onChange={(e) => setPm25(e.target.value)} />
            </label>
            <label>
              PM10 (µg/m³)
              <input type="number" step="any" value={pm10} onChange={(e) => setPm10(e.target.value)} />
            </label>
            <label>
              NO2 (ppb)
              <input type="number" step="any" value={no2} onChange={(e) => setNo2(e.target.value)} />
            </label>
            <label>
              SO2 (ppb)
              <input type="number" step="any" value={so2} onChange={(e) => setSo2(e.target.value)} />
            </label>
            <label>
              CO (ppm)
              <input type="number" step="any" value={co} onChange={(e) => setCo(e.target.value)} />
            </label>
            <label>
              O3 (ppb)
              <input type="number" step="any" value={o3} onChange={(e) => setO3(e.target.value)} />
            </label>
            <div className="adv-form-actions">
              <button type="submit" disabled={polLoading}>
                {polLoading ? "Analysing..." : "Analyse Pollutants"}
              </button>
            </div>
          </form>

          {polReport && (
            <div className="adv-results">
              <div className="adv-card">
                <h3>Summary ({polReport.location})</h3>
                <p>{polReport.summary}</p>
                <p>
                  <strong>Dominant Pollutant:</strong> {polReport.dominant_pollutant || "None"} |{" "}
                  <strong>Evidence Confidence:</strong> {polReport.confidence_level}
                </p>
              </div>

              <div className="adv-card">
                <h3>Possible Contributing Sources (Indicative Only)</h3>
                {(polReport.possible_sources || []).map((src, i) => (
                  <div key={i} className="adv-subitem">
                    <strong>{src.source_category}</strong> — <em>{src.confidence_level}</em> (
                    {src.status_label || "indicative"})
                    <p>{src.explanation}</p>
                  </div>
                ))}
              </div>

              {!!(polReport.data_limitations || []).length && (
                <div className="adv-card adv-limitations">
                  <h4>Data Limitations</h4>
                  <ul>
                    {polReport.data_limitations.map((lim, i) => (
                      <li key={i}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === "anomalies" && (
        <div className="adv-panel">
          <form className="adv-form-grid" onSubmit={handleAnomalySubmit}>
            <label>
              Location
              <input value={anomLocation} onChange={(e) => setAnomLocation(e.target.value)} required />
            </label>
            <label>
              Current PM2.5 (µg/m³)
              <input type="number" step="any" value={anomPm25} onChange={(e) => setAnomPm25(e.target.value)} />
            </label>
            <label>
              Current PM10 (µg/m³)
              <input type="number" step="any" value={anomPm10} onChange={(e) => setAnomPm10(e.target.value)} />
            </label>
            <label>
              Investigation Note (Optional)
              <input
                placeholder="e.g. light wind / evening traffic window"
                value={contextNote}
                onChange={(e) => setContextNote(e.target.value)}
              />
            </label>
            <div className="adv-form-actions">
              <button type="submit" disabled={anomLoading}>
                {anomLoading ? "Scanning..." : "Detect Anomalies"}
              </button>
            </div>
          </form>

          {anomResult && (
            <div className="adv-results">
              <div className="adv-card">
                <h3>
                  Status: {anomResult.status} — {anomResult.classification}
                </h3>
                <p>{anomResult.event_summary}</p>
              </div>

              {(anomResult.anomalies || []).map((ev, idx) => (
                <div key={ev.event_id || idx} className="adv-card">
                  <div className="adv-row-between">
                    <strong>
                      {ev.event_id} • {ev.pollutant} ({ev.classification})
                    </strong>
                    <span>
                      Severity: <strong>{ev.severity}</strong> | Status:{" "}
                      <strong>{ev.investigation_status}</strong>
                    </span>
                  </div>
                  <p>
                    Current: {ev.current_measurement} {ev.unit || ""} | Baseline:{" "}
                    {ev.historical_baseline ?? "N/A"} | Deviation: {ev.deviation ?? "N/A"} | Method:{" "}
                    {ev.detection_method}
                  </p>
                  <p>{ev.possible_explanation}</p>
                  <button type="button" onClick={() => handleInvestigate(ev, idx)}>
                    Mark Under Investigation
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "routes" && (
        <div className="adv-panel">
          <form className="adv-form-grid" onSubmit={handleRouteSubmit}>
            <label>
              Origin Lat
              <input type="number" step="any" value={originLat} onChange={(e) => setOriginLat(e.target.value)} required />
            </label>
            <label>
              Origin Lon
              <input type="number" step="any" value={originLon} onChange={(e) => setOriginLon(e.target.value)} required />
            </label>
            <label>
              Destination Lat
              <input type="number" step="any" value={destLat} onChange={(e) => setDestLat(e.target.value)} required />
            </label>
            <label>
              Destination Lon
              <input type="number" step="any" value={destLon} onChange={(e) => setDestLon(e.target.value)} required />
            </label>
            <label>
              Transport Mode
              <select value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="walking">Walking</option>
                <option value="cycling">Cycling</option>
              </select>
            </label>
            <label>
              Preference
              <select value={preference} onChange={(e) => setPreference(e.target.value)}>
                <option value="lowest_exposure">Lowest Estimated Exposure</option>
                <option value="balanced">Balanced Route</option>
                <option value="fastest">Fastest Route</option>
                <option value="shortest">Shortest Route</option>
              </select>
            </label>
            <div className="adv-form-actions">
              <button type="submit" disabled={routeLoading}>
                {routeLoading ? "Optimising..." : "Compare Routes"}
              </button>
            </div>
          </form>

          {routeResult && (
            <div className="adv-results">
              <div className="adv-card">
                <h3>Recommended Route: {routeResult.recommended_route?.route_id}</h3>
                <p>{routeResult.recommendation_explanation}</p>
              </div>

              <div className="adv-card">
                <h3>Alternative Routes (Estimated Exposure)</h3>
                {(routeResult.alternative_routes || []).map((rt, i) => (
                  <div key={rt.route_id || i} className="adv-subitem">
                    <strong>{rt.route_id}</strong> — {rt.distance_km} km | ~{rt.duration_minutes} min |
                    Estimated Exposure Score: {rt.exposure?.estimated_exposure_score ?? "N/A"} |
                    Coverage: {rt.exposure?.data_coverage || "insufficient"} | Preference Score:{" "}
                    {rt.scoring?.preference_score ?? "N/A"}
                  </div>
                ))}
              </div>

              {!!(routeResult.data_limitations || []).length && (
                <div className="adv-card adv-limitations">
                  <h4>Data Limitations</h4>
                  <ul>
                    {routeResult.data_limitations.map((lim, i) => (
                      <li key={i}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}