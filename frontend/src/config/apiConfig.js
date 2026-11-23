export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1",
  TIMEOUT_MS: 10000,
  // Toggle to false in Part 17 once FastAPI endpoints are live
  USE_MOCK_DATA: import.meta.env.VITE_USE_MOCK !== "false",
  ENDPOINTS: {
    CURRENT_AQI: "/aqi/current",
    HEALTH_GUIDANCE: "/health/advisory",
    CHAT: "/assistant/ask",
    AQI_HISTORY: "/aqi/history",
    COMPARE_LOCATIONS: "/aqi/compare",
    ALERTS: "/alerts",
    GENERATE_ALERTS: "/alerts/generate",
    ACTIVITY_ADVICE: "/activity/advice",
    DATA_QUALITY: "/monitoring/quality"
  }
};