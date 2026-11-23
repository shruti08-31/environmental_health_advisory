import React, { useEffect, useState } from "react";
import { apiService } from "../../services/apiService";
import { SeverityBadge, LoadingState, ErrorState } from "../common/Cards";

const ACTIVITIES = [
  "Walking",
  "Running",
  "Cycling",
  "Outdoor exercise",
  "Indoor exercise"
];

export function ActivityAdvisor({ selectedLocation }) {
  const [activity, setActivity] = useState("Walking");
  const [state, setState] = useState({ loading: true, error: null, data: null });

  const fetchAdvice = async (chosenActivity) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const res = await apiService.getActivityAdvice(selectedLocation, chosenActivity);
      setState({ loading: false, error: null, data: res.data });
    } catch (err) {
      setState({ loading: false, error: err.message, data: null });
    }
  };

  useEffect(() => {
    fetchAdvice(activity);
  }, [selectedLocation, activity]);

  return (
    <div className="view-stack">
      <section className="card">
        <div className="section-header">
          <h3>Select Planned Activity ({selectedLocation})</h3>
        </div>
        <div className="city-toggle-row">
          {ACTIVITIES.map((item) => (
            <button
              key={item}
              type="button"
              className={`chip-btn ${activity === item ? "chip-selected" : ""}`}
              onClick={() => setActivity(item)}
            >
              {item}
            </button>
          ))}
        </div>
      </section>

      {state.loading && <LoadingState message="Evaluating exposure guidance..." />}
      {state.error && <ErrorState message={state.error} onRetry={() => fetchAdvice(activity)} />}

      {!state.loading && !state.error && state.data && (
        <section className="card">
          <div className="section-header">
            <div>
              <span className="eyebrow">{state.data.activity} in {state.data.location}</span>
              <h2>Recommendation: {state.data.recommendation}</h2>
            </div>
            <SeverityBadge severity={state.data.severity} />
          </div>

          <div className="two-col-grid" style={{ marginTop: "1rem" }}>
            <div>
              <h4>Reason</h4>
              <p className="body-text">{state.data.reason}</p>

              <h4 style={{ marginTop: "1rem" }}>Alternative Activity</h4>
              <p className="highlight-box">{state.data.alternative_activity}</p>
            </div>

            <div>
              <h4>Precautions</h4>
              <ul className="clean-list">
                {state.data.precautions?.map((p, idx) => (
                  <li key={idx}>{p}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}