import React, { useState } from "react";
import { Sidebar } from "./Sidebar";
import { Navbar } from "./Navbar";

export function Layout({
  activeView,
  onSelectView,
  selectedLocation,
  onLocationChange,
  children
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar
        activeView={activeView}
        onSelectView={onSelectView}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="main-area">
        <Navbar
          activeView={activeView}
          selectedLocation={selectedLocation}
          onLocationChange={onLocationChange}
          onOpenSidebar={() => setSidebarOpen(true)}
        />
        <main className="content-container">{children}</main>
      </div>
    </div>
  );
}