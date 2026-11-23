import React, { useEffect, useState } from "react";
import { apiService } from "../../services/apiService";
import { SeverityBadge, LoadingState, ErrorState } from "../common/Cards";

export function Alerts() {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [thresholdInput, setThresholdInput] = useState(150);
  const [locationFilter, setLocationFilter] = useState("ALL");

  const loadAlerts = async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const res = await apiService.getAlerts();
      setThresholdInput(res.data.threshold);
      setState({ loading: false, error: null, data: res.data });
    } catch (err) {
      setState({ loading: false, error: err.message, data: null });
    }
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    try {
      const res = await apiService.generateAlerts({
        locations: ["Delhi", "Mumbai", "Vadodara", "Bengaluru"],
        threshold: Number(thresholdInput),
        enabled: state.data?.enabled ?? true
      });
      setState({ loading: false, error: null, data: res.data });
    } catch (err) {
      setState((prev) => ({ ...prev, error: err.message }));
    }
  };

  const handleToggleEnabled = async () => {
    const nextEnabled = !(state.data?.enabled ?? true);
    try {
      const res = await apiService.generateAlerts({
        locations: ["Delhi", "Mumbai", "Vadodara", "Bengaluru"],
        threshold: Number(thresholdInput),
        enabled: nextEnabled
      });
      setState({ loading: false, error: null, data: res.data });
    } catch (err) {
      setState((prev) => ({ ...prev, error: err.message }));
    }
  };

  if (state.loading) return <LoadingState message="Loading smart alerts..." />;
  if (state.error) return <ErrorState message={state.error} onRetry={loadAlerts} />;

  const { data } = state;
  const locations = ["ALL", ...new Set(data.alert_history.map((a) => a.location))];
  const filteredHistory =
    locationFilter === "ALL"
      ? data.alert_history
      : data.alert_history.filter((a) => a.location === locationFilter);

  return (
    <div className="view-stack">
      <section className="card toolbar-card">
        <form className="threshold-form" onSubmit={handleSaveConfig}>
          <label>
            <strong>AQI Alert Threshold</strong>
            <input
              type="number"
              min="25"
              max="500"
              value={thresholdInput}
              onChange={(e) => setThresholdInput(e.target.value)}
            />
          </label>
          <button type="submit" className="btn btn-primary">
            Apply & Evaluate Alerts
          </button>
        </form>

        <button
          type="button"
          className={`btn ${data.enabled ? "btn-secondary" : "btn-primary"}`}
          onClick={handleToggleEnabled}
        >
          {data.enabled ? "Disable Alerts" : "Enable Alerts"}
        </button>
      </section>

      <section className="card">
        <div className="section-header">
          <h3>Active Alerts ({data.active_alerts.length})</h3>
          <span className="muted-text">
            Status: {data.enabled ? "Monitoring Enabled" : "Monitoring Paused"}
          </span>
        </div>

        {data.active_alerts.length === 0 ? (
          <p className="muted-text">No active alerts matching current configuration.</p>
        ) : (
          <div className="alerts-list">
            {data.active_alerts.map((alert) => (
              <div key={alert.id} className="alert-row active-alert-row">
                <div>
                  <span className="alert-type">{alert.type}</span>
                  <h4>
                    {alert.location} — {alert.message}
                  </h4>
                  <small>{alert.timestamp}</small>
                </div>
                <SeverityBadge severity={alert.severity} />
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="card">
        <div className="section-header">
          <h3>Alert History</h3>
          <select
            aria-label="Filter alert history by location"
            value={locationFilter}
            onChange={(e) => setLocationFilter(e.target.value)}
          >
            {locations.map((loc) => (
              <option key={loc} value={loc}>
                {loc === "ALL" ? "All Locations" : loc}
              </option>
            ))}
          </select>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Location</th>
                <th>Severity</th>
                <th>Message</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {filteredHistory.map((item) => (
                <tr key={item.id}>
                  <td>{item.type}</td>
                  <td><strong>{item.location}</strong></td>
                  <td><SeverityBadge severity={item.severity} /></td>
                  <td>{item.message}</td>
                  <td>{item.timestamp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}