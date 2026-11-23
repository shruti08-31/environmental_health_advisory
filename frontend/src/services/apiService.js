import axios from "axios";
import { API_CONFIG } from "../config/apiConfig";
import { mockBackendService } from "./mockService";

const apiClient = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT_MS,
  headers: {
    "Content-Type": "application/json"
  }
});

/**
 * Centralized API Service Layer.
 * When USE_MOCK_DATA is switched to false in Part 17, every method automatically
 * calls the FastAPI endpoints with identical response contracts.
 */
export const apiService = {
  async getCurrentAQI(location) {
    if (API_CONFIG.USE_MOCK_DATA) {
      return mockBackendService.getCurrentAQI(location);
    }
    const { data } = await apiClient.get(API_CONFIG.ENDPOINTS.CURRENT_AQI, {
      params: { location }
    });
    return data;
  },

  async getHealthGuidance(location) {
    if (API_CONFIG.USE_MOCK_DATA) {
      return mockBackendService.getHealthGuidance(location);
    }
    const { data } = await apiClient.get(API_CONFIG.ENDPOINTS.HEALTH_GUIDANCE, {
      params: { location }
    });
    return data;
  },

  async sendChatMessage(question, location) {
    if (API_CONFIG.USE_MOCK_DATA) {
      return mockBackendService.sendChatMessage(question, location);
    }
    const { data } = await apiClient.post(API_CONFIG.ENDPOINTS.CHAT, {
      question,
      location
    });
    return data;
  },

  async getAQIHistory(location, period = "daily", dateRange = {}) {
    if (API_CONFIG.USE_MOCK_DATA) {
      return mockBackendService.getAQIHistory(location, period, dateRange);
    }
    const { data } = await apiClient.get(API_CONFIG.ENDPOINTS.AQI_HISTORY, {
      params: { location, period, ...dateRange }
    });
    return data;
  },

  async compareLocations(locations) {
    if (API_CONFIG.USE_MOCK_DATA) {
      return mockBackendService.compareLocations(locations);
    }
    const { data } = await apiClient.post(API_CONFIG.ENDPOINTS.COMPARE_LOCATIONS, {
      locations
    });
    return data;
  },

  async getAlerts() {
    if (API_CONFIG.USE_MOCK_DATA) {
      return mockBackendService.getAlerts();
    }
    const { data } = await apiClient.get(API_CONFIG.ENDPOINTS.ALERTS);
    return data;
  },

  async generateAlerts(payload) {
    if (API_CONFIG.USE_MOCK_DATA) {
      return mockBackendService.generateAlerts(payload);
    }
    const { data } = await apiClient.post(API_CONFIG.ENDPOINTS.GENERATE_ALERTS, payload);
    return data;
  },

  async getActivityAdvice(location, activity) {
    if (API_CONFIG.USE_MOCK_DATA) {
      return mockBackendService.getActivityAdvice(location, activity);
    }
    const { data } = await apiClient.get(API_CONFIG.ENDPOINTS.ACTIVITY_ADVICE, {
      params: { location, activity }
    });
    return data;
  },

  async getDataQuality(location) {
    if (API_CONFIG.USE_MOCK_DATA) {
      return mockBackendService.getDataQuality(location);
    }
    const { data } = await apiClient.get(API_CONFIG.ENDPOINTS.DATA_QUALITY, {
      params: { location }
    });
    return data;
  }
};