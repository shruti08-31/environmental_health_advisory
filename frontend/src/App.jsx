import React, { useState } from "react";
import { Layout } from "./components/layout/Layout";
import { Overview } from "./components/views/Overview";
import { AQIMonitoring } from "./components/views/AQIMonitoring";
import { HealthAdvisor } from "./components/views/HealthAdvisor";
import { AIAssistant } from "./components/views/AIAssistant";
import { Analytics } from "./components/views/Analytics";
import { LocationComparison } from "./components/views/LocationComparison";
import { Alerts } from "./components/views/Alerts";
import { ActivityAdvisor } from "./components/views/ActivityAdvisor";
import { DataQuality } from "./components/views/DataQuality";
import { PollutantAnalysisView } from "./components/views/PollutantAnalysisView";
import { AnomalyDetectionView } from "./components/views/AnomalyDetectionView";
import { PollutionRouteView } from "./components/views/PollutionRouteView";
import "./styles/advancedModules.css";

export default function App() {
  const [activeView, setActiveView] = useState("overview");
  const [selectedLocation, setSelectedLocation] = useState("Delhi");

  const renderActiveView = () => {
    switch (activeView) {
      case "overview":
        return (
          <Overview
            selectedLocation={selectedLocation}
            onNavigate={setActiveView}
          />
        );
      case "live-aqi":
        return (
          <AQIMonitoring
            selectedLocation={selectedLocation}
            onLocationChange={setSelectedLocation}
          />
        );
      case "health-advisor":
        return <HealthAdvisor selectedLocation={selectedLocation} />;
      case "ai-assistant":
        return <AIAssistant selectedLocation={selectedLocation} />;
      case "analytics":
        return <Analytics selectedLocation={selectedLocation} />;
      case "comparison":
        return <LocationComparison />;
      case "alerts":
        return <Alerts />;
      case "activity":
        return <ActivityAdvisor selectedLocation={selectedLocation} />;
      case "data-quality":
        return <DataQuality selectedLocation={selectedLocation} />;
      case "pollutant-analysis":
        return <PollutantAnalysisView selectedLocation={selectedLocation} />;
      case "anomaly-detection":
        return <AnomalyDetectionView selectedLocation={selectedLocation} />;
      case "route-optimizer":
        return <PollutionRouteView selectedLocation={selectedLocation} />;
      default:
        return (
          <Overview
            selectedLocation={selectedLocation}
            onNavigate={setActiveView}
          />
        );
    }
  };

  return (
    <Layout
      activeView={activeView}
      onSelectView={setActiveView}
      selectedLocation={selectedLocation}
      onLocationChange={setSelectedLocation}
    >
      {renderActiveView()}
    </Layout>
  );
}