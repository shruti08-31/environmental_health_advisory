import React, { useEffect, useState } from "react";
import {
  fetchLiveAnomalyDetection,
  updateAnomalyInvestigation,
} from "../../services/advisoryExtrasService";

export function AnomalyDetectionView({ selectedLocation = "Delhi" }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    fetchLiveAnomalyDetection(selectedLocation)
      .then((res) => {
        if (active) setData(res);
      })
      .catch((err) => {
        if (active) setError(err.message || "Failed to detect anomalies.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedLocation]);

  const handleStatusChange = async (event, idx) => {
    try {
      const updated = await updateAnomalyInvestigation(event, "under_investigation");
      if (updated?.event && data?.anomalies) {
        const next = data.anomalies.map((item, i) => (i === idx ? updated.event : item));
        setData({ ...data, anomalies: next });
      }
    } catch (err) {
      setError(err.message || "Unable to update investigation status.");
    }
  };

  return (
    <div className="view-stack">
      <div className="page-header-row">
        <div>
          <h2>Anomaly Detection</h2>
          <p className="muted-text">
            Automated rolling-baseline and statistical deviation check for{" "}
            <strong>{selectedLocation}</strong>
          </p>
        </div>
        {data?.classification && (
          <span className="status-badge">{data.classification}</span>
        )}
      </div>

      {loading && <div className="surface-card">Scanning live pollutant series...</div>}
      {error && <div className="surface-card error-card">{error}</div>}

      {!loading && data && (
        <>
          <div className="surface-card">
            <h3>Event Summary</h3>
            <p>{data.event_summary}</p>
            <small className="muted-text">
              Statistical anomalies are indicative only and are not proof of a pollution incident.
            </small>
          </div>

          <div className="card-list">
            {(data.anomalies || []).map((ev, idx) => (
              <div key={ev.event_id || idx} className="surface-card">
                <div className="row-top">
                  <div>
                    <strong>
                      {ev.pollutant} — {ev.classification}
                    </strong>
                    <div className="muted-text">
                      Event ID: {ev.event_id} • Method: {ev.detection_method}
                    </div>
                  </div>
                  <span className="pill-tag">
                    Severity: {ev.severity} • {ev.investigation_status}
                  </span>
                </div>

                <div className="meta-row">
                  <span>
                    <strong>Current:</strong> {ev.current_measurement} {ev.unit || ""}
                  </span>
                  <span>
                    <strong>Baseline:</strong> {ev.historical_baseline ?? "N/A"} {ev.unit || ""}
                  </span>
                  <span>
                    <strong>Deviation:</strong>{" "}
                    {ev.deviation !== null && ev.deviation !== undefined
                      ? `${ev.deviation >= 0 ? "+" : ""}${ev.deviation}`
                      : "N/A"}
                  </span>
                </div>

                <p>{ev.possible_explanation}</p>

                {ev.investigation_status !== "under_investigation" && (
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => handleStatusChange(ev, idx)}
                  >
                    Start Investigation
                  </button>
                )}
              </div>
            ))}
          </div>

          {!!(data.warnings || []).length && (
            <div className="surface-card">
              <h4>Data &amp; Coverage Notes</h4>
              <ul className="clean-list">
                {data.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}