import React, { useEffect, useState } from "react";
import { apiService } from "../../services/apiService";
import {
  MetricCard,
  SeverityBadge,
  LoadingState,
  ErrorState
} from "../common/Cards";
import { LocationPollutantBarChart } from "../common/Charts";

const AVAILABLE_CITIES = ["Delhi", "Mumbai", "Bengaluru", "Vadodara", "Chennai"];

export function LocationComparison() {
  const [selectedCities, setSelectedCities] = useState(["Delhi", "Mumbai", "Bengaluru"]);
  const [state, setState] = useState({ loading: true, error: null, data: null });

  const toggleCity = (city) => {
    setSelectedCities((prev) => {
      if (prev.includes(city)) {
        return prev.length > 2 ? prev.filter((c) => c !== city) : prev;
      }
      return [...prev, city];
    });
  };

  const runComparison = async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const res = await apiService.compareLocations(selectedCities);
      setState({ loading: false, error: null, data: res.data });
    } catch (err) {
      setState({ loading: false, error: err.message, data: null });
    }
  };

  useEffect(() => {
    runComparison();
  }, [selectedCities]);

  return (
    <div className="view-stack">
      <section className="card">
        <div className="section-header">
          <h3>Select Locations to Compare (Min 2)</h3>
        </div>
        <div className="city-toggle-row">
          {AVAILABLE_CITIES.map((city) => {
            const active = selectedCities.includes(city);
            return (
              <button
                key={city}
                type="button"
                className={`chip-btn ${active ? "chip-selected" : ""}`}
                onClick={() => toggleCity(city)}
              >
                {city}
              </button>
            );
          })}
        </div>
      </section>

      {state.loading && <LoadingState message="Comparing multi-location AQI..." />}
      {state.error && <ErrorState message={state.error} onRetry={runComparison} />}

      {!state.loading && !state.error && state.data && (
        <>
          <div className="two-col-grid">
            <MetricCard
              title="Highest AQI Location"
              value={`${state.data.highest_location.location} (${state.data.highest_location.aqi})`}
              accent="teal"
              badge={<SeverityBadge severity={state.data.highest_location.severity} />}
            />
            <MetricCard
              title="Lowest AQI Location"
              value={`${state.data.lowest_location.location} (${state.data.lowest_location.aqi})`}
              accent="green"
              badge={<SeverityBadge severity={state.data.lowest_location.severity} />}
            />
          </div>

          <section className="card">
            <div className="section-header">
              <h3>Comparison Summary</h3>
            </div>
            <p className="lead-text">{state.data.summary}</p>
          </section>

          <div className="kpi-grid">
            {state.data.locations.map((loc) => (
              <MetricCard
                key={loc.location}
                title={loc.location}
                value={loc.aqi}
                unit="AQI"
                subtitle={`PM2.5: ${loc.pollutants.PM25.value} ${loc.pollutants.PM25.unit}`}
                badge={<SeverityBadge severity={loc.severity} />}
              />
            ))}
          </div>

          <section className="card">
            <div className="section-header">
              <h3>Pollutant & AQI Comparison Chart</h3>
            </div>
            <LocationPollutantBarChart locations={state.data.locations} height={310} />
          </section>
        </>
      )}
    </div>
  );
}