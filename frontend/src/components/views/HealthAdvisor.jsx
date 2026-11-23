import React, { useEffect, useState } from "react";
import { ShieldAlert, Users, Info } from "lucide-react";
import { apiService } from "../../services/apiService";
import { SeverityBadge, LoadingState, ErrorState } from "../common/Cards";

export function HealthAdvisor({ selectedLocation }) {
  const [state, setState] = useState({ loading: true, error: null, data: null });

  const loadGuidance = async () => {
    setState({ loading: true, error: null, data: null });
    try {
      const res = await apiService.getHealthGuidance(selectedLocation);
      setState({ loading: false, error: null, data: res.data });
    } catch (err) {
      setState({ loading: false, error: err.message, data: null });
    }
  };

  useEffect(() => {
    loadGuidance();
  }, [selectedLocation]);

  if (state.loading) return <LoadingState message="Generating health advisory..." />;
  if (state.error) return <ErrorState message={state.error} onRetry={loadGuidance} />;

  const { data } = state;

  return (
    <div className="view-stack">
      <section className="card advisory-banner">
        <div>
          <span className="eyebrow">Advisory for {data.location} (AQI {data.aqi})</span>
          <h2>{data.summary}</h2>
        </div>
        <div className="advisory-badges">
          <SeverityBadge severity={data.severity} />
          <span className="urgency-chip">
            <ShieldAlert size={14} />
            Urgency: {data.urgency}
          </span>
        </div>
      </section>

      <div className="two-col-grid">
        <section className="card">
          <div className="section-header">
            <h3>Precautionary Recommendations</h3>
          </div>
          <ul className="clean-list">
            {data.precautions?.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </section>

        <section className="card">
          <div className="section-header">
            <h3>
              <Users size={17} style={{ verticalAlign: "text-bottom", marginRight: 6 }} />
              Sensitive-Group Guidance
            </h3>
          </div>
          <p className="body-text">{data.sensitive_groups}</p>
        </section>
      </div>

      <section className="card">
        <div className="section-header">
          <h3>
            <Info size={17} style={{ verticalAlign: "text-bottom", marginRight: 6 }} />
            Explanation of Recommendations
          </h3>
        </div>
        <p className="body-text">{data.explanation}</p>
      </section>
    </div>
  );
}