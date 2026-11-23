import React, { useEffect, useState } from "react";
import { fetchLivePollutantAnalysis } from "../../services/advisoryExtrasService";

const UNITS = {
  PM25: "µg/m³",
  PM10: "µg/m³",
  NO2: "ppb",
  SO2: "ppb",
  CO: "ppm",
  O3: "ppb",
};

export function PollutantAnalysisView({ selectedLocation = "Delhi" }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    fetchLivePollutantAnalysis(selectedLocation)
      .then((data) => {
        if (active) setReport(data);
      })
      .catch((err) => {
        if (active) setError(err.message || "Failed to load pollutant analysis.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedLocation]);

  const entries = Object.entries(report?.available_pollutants || {});

  return (
    <div className="view-stack">
      <div className="page-header-row">
        <div>
          <h2>Pollutant Analysis</h2>
          <p className="muted-text">
            Dominant species, baseline comparisons, and indicative source insights for{" "}
            <strong>{selectedLocation}</strong>
          </p>
        </div>
        {report?.dominant_pollutant && (
          <span className="status-badge">Dominant: {report.dominant_pollutant}</span>
        )}
      </div>

      {loading && <div className="surface-card">Loading live pollutant analysis...</div>}
      {error && <div className="surface-card error-card">{error}</div>}

      {!loading && report && (
        <>
          <div className="surface-card">
            <h3>Overview &amp; Summary</h3>
            <p>{report.summary}</p>
            <div className="meta-row">
              <span>
                <strong>Confidence:</strong> {report.confidence_level || "low"}
              </span>
              <span>
                <strong>Elevated vs. Baseline:</strong>{" "}
                {(report.elevated_pollutants || []).map((e) => e.pollutant).join(", ") || "None"}
              </span>
            </div>
          </div>

          <div className="metric-grid">
            {entries.map(([pol, val]) => (
              <div key={pol} className="surface-card metric-tile">
                <span className="tile-label">{pol}</span>
                <strong className="tile-value">
                  {val !== null && val !== undefined ? `${val} ${UNITS[pol] || ""}` : "Missing"}
                </strong>
              </div>
            ))}
          </div>

          <div className="surface-card">
            <h3>Possible Contributing Sources (Indicative Only)</h3>
            <p className="muted-text">
              Indicative hypotheses only—not confirmed by AQI or pollutant measurements alone.
            </p>
            <div className="card-list">
              {(report.possible_sources || []).map((src, idx) => (
                <div key={idx} className="list-row-card">
                  <div className="row-top">
                    <strong>{src.source_category}</strong>
                    <span className="pill-tag">
                      Indicative • {src.confidence_level || "low"} confidence
                    </span>
                  </div>
                  <p>{src.explanation}</p>
                  {!!(src.measured_evidence || []).length && (
                    <small className="muted-text">
                      Measured facts: {src.measured_evidence.join(" • ")}
                    </small>
                  )}
                </div>
              ))}
            </div>
          </div>

          {!!(report.data_limitations || []).length && (
            <div className="surface-card">
              <h4>Data Limitations</h4>
              <ul className="clean-list">
                {report.data_limitations.map((lim, i) => (
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