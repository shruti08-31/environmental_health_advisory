import React, { useEffect, useState } from "react";
import { RefreshCw, Search, Clock } from "lucide-react";
import { apiService } from "../../services/apiService";
import {
  PollutantGrid,
  SeverityBadge,
  LoadingState,
  ErrorState
} from "../common/Cards";

export function AQIMonitoring({ selectedLocation, onLocationChange }) {
  const [query, setQuery] = useState(selectedLocation);
  const [state, setState] = useState({ loading: true, error: null, aqi: null, guidance: null });

  const fetchMonitoringData = async (city) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const [aqiRes, guidanceRes] = await Promise.all([
        apiService.getCurrentAQI(city),
        apiService.getHealthGuidance(city)
      ]);
      setState({
        loading: false,
        error: null,
        aqi: aqiRes.data,
        guidance: guidanceRes.data
      });
    } catch (err) {
      setState({ loading: false, error: err.message, aqi: null, guidance: null });
    }
  };

  useEffect(() => {
    setQuery(selectedLocation);
    fetchMonitoringData(selectedLocation);
  }, [selectedLocation]);

  const handleSearch = (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    onLocationChange(query.trim());
    fetchMonitoringData(query.trim());
  };

  return (
    <div className="view-stack">
      <section className="card toolbar-card">
        <form className="search-form" onSubmit={handleSearch}>
          <div className="input-with-icon">
            <Search size={16} />
            <input
              type="text"
              placeholder="Search city (e.g., Delhi, Mumbai, Bengaluru, Vadodara)..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <button type="submit" className="btn btn-primary">
            Search Location
          </button>
        </form>

        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => fetchMonitoringData(selectedLocation)}
          disabled={state.loading}
        >
          <RefreshCw size={15} className={state.loading ? "spin" : ""} />
          <span>Refresh</span>
        </button>
      </section>

      {state.loading && <LoadingState message={`Fetching live AQI for ${query}...`} />}
      {state.error && (
        <ErrorState message={state.error} onRetry={() => fetchMonitoringData(selectedLocation)} />
      )}

      {!state.loading && !state.error && state.aqi && (
        <>
          <section className="card hero-aqi-card">
            <div>
              <span className="eyebrow">Live Station Telemetry</span>
              <h2>{state.aqi.location}</h2>
              <div className="hero-aqi-score">
                <span className="big-aqi">{state.aqi.aqi}</span>
                <SeverityBadge severity={state.aqi.severity} />
              </div>
            </div>

            <div className="freshness-box">
              <div className="freshness-pill">
                <Clock size={15} />
                <span>{state.aqi.freshness?.label || "Fresh"}</span>
              </div>
              <small>Last Updated: {state.aqi.last_updated}</small>
            </div>
          </section>

          <section className="card">
            <div className="section-header">
              <h3>Pollutant Breakdown</h3>
            </div>
            <PollutantGrid pollutants={state.aqi.pollutants} />
          </section>

          {state.guidance && (
            <section className="card">
              <div className="section-header">
                <h3>Health Guidance Summary</h3>
              </div>
              <p className="lead-text">{state.guidance.summary}</p>
              <ul className="clean-list">
                {state.guidance.precautions?.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}