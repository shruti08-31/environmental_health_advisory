import React from "react";

export function SeverityBadge({ severity }) {
  const normalized = (severity || "").toLowerCase();
  let badgeClass = "badge-neutral";

  if (normalized === "good") badgeClass = "badge-good";
  else if (normalized === "moderate") badgeClass = "badge-moderate";
  else if (normalized.includes("sensitive")) badgeClass = "badge-sensitive";
  else if (normalized.includes("unhealthy") || normalized.includes("hazardous")) {
    badgeClass = "badge-unhealthy";
  }

  return <span className={`status-badge ${badgeClass}`}>{severity || "Unknown"}</span>;
}

export function MetricCard({ title, value, unit, subtitle, accent = "teal", badge }) {
  return (
    <div className={`card metric-card accent-${accent}`}>
      <div className="metric-card-header">
        <span className="metric-title">{title}</span>
        {badge}
      </div>
      <div className="metric-value-row">
        <span className="metric-value">{value ?? "--"}</span>
        {unit && <span className="metric-unit">{unit}</span>}
      </div>
      {subtitle && <p className="metric-subtitle">{subtitle}</p>}
    </div>
  );
}

export function PollutantGrid({ pollutants }) {
  const order = [
    { key: "PM25", label: "PM2.5" },
    { key: "PM10", label: "PM10" },
    { key: "NO2", label: "NO₂" },
    { key: "SO2", label: "SO₂" },
    { key: "CO", label: "CO" },
    { key: "O3", label: "O₃" }
  ];

  return (
    <div className="pollutant-grid">
      {order.map(({ key, label }) => {
        const item = pollutants?.[key];
        return (
          <div key={key} className="card pollutant-card">
            <span className="pollutant-label">{label}</span>
            <div className="pollutant-reading">
              <strong>{item?.value ?? "N/A"}</strong>
              <span>{item?.unit || ""}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function LoadingState({ message = "Loading environmental data..." }) {
  return (
    <div className="state-box">
      <div className="spinner" />
      <span>{message}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="state-box state-error">
      <p>{message || "Unable to load data."}</p>
      {onRetry && (
        <button type="button" className="btn btn-secondary" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}