import React, { useEffect, useState } from "react";
import { apiService } from "../../services/apiService";
import {
  MetricCard,
  PollutantGrid,
  SeverityBadge,
  LoadingState,
  ErrorState
} from "../common/Cards";
import { AQITrendChart } from "../common/Charts";

export function Overview({ selectedLocation, onNavigate }) {
  const [state, setState] = useState({ loading: true, error: null, payload: null });

  const loadOverview = async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const [aqiRes, healthRes, historyRes, alertsRes] = await Promise.all([
        apiService.getCurrentAQI(selectedLocation),
        apiService.getHealthGuidance(selectedLocation),
        apiService.getAQIHistory(selectedLocation, "daily"),
        apiService.getAlerts()
      ]);

      setState({
        loading: false,
        error: null,
        payload: {
          aqi: aqiRes.data,
          health: healthRes.data,
          history: historyRes.data,
          alerts: alertsRes.data
        }
      });
    } catch (err) {
      setState({ loading: false, error: err.message, payload: null });
    }
  };

  useEffect(() => {
    loadOverview();
  }, [selectedLocation]);

  if (state.loading) return <LoadingState message="Loading overview metrics..." />;
  if (state.error) return <ErrorState message={state.error} onRetry={loadOverview} />;

  const { aqi, health, history, alerts } = state.payload;

  return (
    <div className="view-stack">
      <div className="kpi-grid">
        <MetricCard
          title="Current AQI"
          value={aqi.aqi}
          unit="US AQI"
          subtitle={`Station: ${aqi.location}`}
          accent="teal"
          badge={<SeverityBadge severity={aqi.severity} />}
        />
        <MetricCard
          title="Selected Location"
          value={aqi.location}
          subtitle={`Last updated: ${aqi.last_updated}`}
          accent="blue"
        />
        <MetricCard
          title="Active Alerts"
          value={alerts.active_alerts?.length ?? 0}
          unit="Alerts"
          subtitle={`Threshold set at AQI ${alerts.threshold}`}
          accent="green"
        />
      </div>

      <section className="card">
        <div className="section-header">
          <h3>Pollutant Concentrations</h3>
          <span className="muted-text">Updated {aqi.last_updated}</span>
        </div>
        <PollutantGrid pollutants={aqi.pollutants} />
      </section>

      <div className="two-col-grid">
        <section className="card">
          <div className="section-header">
            <h3>7-Day AQI Trend</h3>
            <button
              type="button"
              className="link-btn"
              onClick={() => onNavigate("analytics")}
            >
              Full Analytics →
            </button>
          </div>
          <AQITrendChart data={history.series} height={240} />
        </section>

        <div className="view-stack">
          <section className="card">
            <div className="section-header">
              <h3>Health Recommendation Summary</h3>
              <button
                type="button"
                className="link-btn"
                onClick={() => onNavigate("health-advisor")}
              >
                Details →
              </button>
            </div>
            <p className="lead-text">{health.summary}</p>
            <ul className="clean-list">
              {health.precautions?.slice(0, 2).map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </section>

          <section className="card">
            <div className="section-header">
              <h3>Recent Alerts</h3>
              <button
                type="button"
                className="link-btn"
                onClick={() => onNavigate("alerts")}
              >
                Manage →
              </button>
            </div>
            {alerts.active_alerts?.length ? (
              <div className="alert-mini-list">
                {alerts.active_alerts.slice(0, 2).map((alert) => (
                  <div key={alert.id} className="alert-mini-item">
                    <div>
                      <strong>{alert.location}</strong> — {alert.message}
                    </div>
                    <SeverityBadge severity={alert.severity} />
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted-text">No active threshold alerts at this time.</p>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}