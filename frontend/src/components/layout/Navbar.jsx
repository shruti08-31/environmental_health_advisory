import React from "react";
import { Menu, MapPin } from "lucide-react";
import { NAV_ITEMS } from "./Sidebar";

const PRESET_CITIES = ["Delhi", "Mumbai", "Bengaluru", "Vadodara", "Chennai"];

export function Navbar({ activeView, selectedLocation, onLocationChange, onOpenSidebar }) {
  const currentTab = NAV_ITEMS.find((item) => item.id === activeView);

  return (
    <header className="navbar">
      <div className="navbar-left">
        <button
          type="button"
          className="icon-btn mobile-only"
          onClick={onOpenSidebar}
          aria-label="Open navigation"
        >
          <Menu size={20} />
        </button>
        <div>
          <h1 className="page-title">{currentTab?.label || "Overview"}</h1>
          <p className="page-subtitle">Environmental Health Advisory & Monitoring System</p>
        </div>
      </div>

      <div className="navbar-right">
        <div className="location-selector">
          <MapPin size={16} />
          <select
            aria-label="Active monitoring city"
            value={PRESET_CITIES.includes(selectedLocation) ? selectedLocation : ""}
            onChange={(e) => e.target.value && onLocationChange(e.target.value)}
          >
            {!PRESET_CITIES.includes(selectedLocation) && (
              <option value="">{selectedLocation}</option>
            )}
            {PRESET_CITIES.map((city) => (
              <option key={city} value={city}>
                {city}
              </option>
            ))}
          </select>
        </div>
      </div>
    </header>
  );
}