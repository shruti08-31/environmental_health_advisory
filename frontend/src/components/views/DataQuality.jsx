import React, { useEffect, useState } from "react";
import { CheckCircle2, AlertTriangle } from "lucide-react";
import { apiService } from "../../services/apiService";
import { MetricCard, LoadingState, ErrorState } from "../common/Cards";

export function DataQuality({ selectedLocation }) {
  const [state, setState] = useState({ loading: true, error: null, data: null });

  const loadQuality = async () => {
    setState({ loading: true, error: null, data: null });
    try {
      const res = await apiService.getDataQuality(selectedLocation);
      setState({ loading: false, error: null, data: res.data });
    } catch (err) {
      setState({ loading: false, error: err.message, data: null });
    }
  };

  useEffect(() => {
    loadQuality();
  }, [selectedLocation]);

  if (state.loading) return <LoadingState message="Checking telemetry data quality..." />;
  if (state.error) return <ErrorState message={state.error} onRetry={loadQuality} />;

  const { data } = state;

  return (
    <div className="view-stack">
      <div className="kpi-grid">
        <MetricCard
          title="Completeness"
          value={`${data.completeness_percentage}%`}
          subtitle={`Status: ${data.status}`}
          accent="green"
        />
        <MetricCard
          title="Data Availability"
          value={data.data_available ? "Available" : "Unavailable"}
          subtitle={`Last updated: ${data.last_updated}`}
          accent="teal"
        />
        <MetricCard
          title="API Availability"
          value={data.api_available ? "Online" : "Degraded"}
          subtitle={`${data.metrics?.successful_requests ?? 0}/${data.metrics?.total_requests ?? 0} successful checks`}
          accent="blue"
        />
      </div>

      <div className="two-col-grid">
        <section className="card">
          <div className="section-header">
            <h3>Missing Pollutant Values</h3>
          </div>
          {data.missing_pollutants?.length ? (
            <ul className="clean-list">
              {data.missing_pollutants.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          ) : (
            <p className="ok-status">
              <CheckCircle2 size={16} />
              <span>All core pollutants (PM2.5, PM10, NO₂, SO₂, CO, O₃) are present.</span>
            </p>
          )}
        </section>

        <section className="card">
          <div className="section-header">
            <h3>Data Freshness Warnings</h3>
          </div>
          {data.freshness_warnings?.length ? (
            <ul className="clean-list">
              {data.freshness_warnings.map((w, idx) => (
                <li key={idx}>
                  <AlertTriangle size={15} /> {w}
                </li>
              ))}
            </ul>
          ) : (
            <p className="ok-status">
              <CheckCircle2 size={16} />
              <span>No stale reading warnings. Telemetry timestamps are within tolerance.</span>
            </p>
          )}
        </section>
      </div>
    </div>
  );
}