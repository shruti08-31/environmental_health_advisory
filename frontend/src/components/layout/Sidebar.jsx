import React from "react";
import {
  LayoutDashboard,
  Activity,
  HeartPulse,
  Bot,
  BarChart3,
  GitCompareArrows,
  BellRing,
  Bike,
  ShieldCheck,
  Leaf,
  X
} from "lucide-react";

export const NAV_ITEMS = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "live-aqi", label: "Live AQI", icon: Activity },
  { id: "health-advisor", label: "Health Advisor", icon: HeartPulse },
  { id: "ai-assistant", label: "AI Assistant", icon: Bot },
  { id: "analytics", label: "AQI Analytics", icon: BarChart3 },
  { id: "comparison", label: "Location Comparison", icon: GitCompareArrows },
  { id: "alerts", label: "Smart Alerts", icon: BellRing },
  { id: "activity", label: "Activity Advisor", icon: Bike },
  { id: "data-quality", label: "Data Quality", icon: ShieldCheck }
];

export function Sidebar({ activeView, onSelectView, isOpen, onClose }) {
  return (
    <>
      {isOpen && <div className="sidebar-backdrop" onClick={onClose} />}
      <aside className={`sidebar ${isOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-brand">
          <div className="brand-icon">
            <Leaf size={20} />
          </div>
          <div>
            <h2>EcoHealth</h2>
            <span>Air & Health Monitor</span>
          </div>
          <button
            type="button"
            className="icon-btn mobile-only"
            onClick={onClose}
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              className={`nav-item ${activeView === id ? "active" : ""}`}
              onClick={() => {
                onSelectView(id);
                onClose();
              }}
            >
              <Icon size={18} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="mode-pill">Service Layer Ready</span>
          <small>Part 16 • Pre-FastAPI UI</small>
        </div>
      </aside>
    </>
  );
}