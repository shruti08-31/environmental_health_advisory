import React, { useEffect, useState } from "react";
import { apiService } from "../../services/apiService";
import { MetricCard, LoadingState, ErrorState } from "../common/Cards";
import { AQITrendChart, PollutantHistoryChart } from "../common/Charts";

export function Analytics({ selectedLocation }) {
  const [period, setPeriod] = useState("daily");
  const [startDate, setStartDate] = useState("2026-11-17");
  const [endDate, setEndDate] = useState("2026-11-23");
  const [state, setState] = useState({ loading: true, error: null, data: null });

  const loadAnalytics = async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const res = await apiService.getAQIHistory(selectedLocation, period, {
        start_date: startDate,
        end_date: endDate
      });
      setState({ loading: false, error: null, data: res.data });
    } catch (err) {
      setState({ loading: false, error: err.message, data: null });
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, [selectedLocation, period, startDate, endDate]);

  return (
    <div className="view-stack">
      <section className="card toolbar-card">
        <div className="segmented-control">
          {["daily", "weekly", "monthly"].map((tab) => (
            <button
              key={tab}
              type="button"
              className={`seg-btn ${period === tab ? "active" : ""}`}
              onClick={() => setPeriod(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        <div className="date-filters">
          <label>
            From
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </label>
          <label>
            To
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </label>
        </div>
      </section>

      {state.loading && <LoadingState message="Loading AQI analytics..." />}
      {state.error && <ErrorState message={state.error} onRetry={loadAnalytics} />}

      {!state.loading && !state.error && state.data && (
        <>
          <div className="kpi-grid">
            <MetricCard
              title="Average AQI"
              value={state.data.stats.average_aqi}
              unit="AQI"
              subtitle={`${selectedLocation} (${period})`}
              accent="blue"
            />
            <MetricCard
              title="Maximum AQI"
              value={state.data.stats.max_aqi}
              unit="Peak"
              subtitle="Highest recorded in range"
              accent="teal"
            />
            <MetricCard
              title="Minimum AQI"
              value={state.data.stats.min_aqi}
              unit="Low"
              subtitle="Lowest recorded in range"
              accent="green"
            />
          </div>

          <section className="card">
            <div className="section-header">
              <h3>{period.charAt(0).toUpperCase() + period.slice(1)} AQI Trend</h3>
            </div>
            <AQITrendChart data={state.data.series} height={280} />
          </section>

          <section className="card">
            <div className="section-header">
              <h3>Pollutant-Wise Trends (PM2.5, PM10, NO₂, O₃)</h3>
            </div>
            <PollutantHistoryChart data={state.data.series} height={290} />
          </section>
        </>
      )}
    </div>
  );
}