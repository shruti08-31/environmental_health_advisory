import React from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from "recharts";

export function AQITrendChart({ data = [], height = 280 }) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 10, right: 16, left: -12, bottom: 0 }}>
          <defs>
            <linearGradient id="aqiGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0d9488" stopOpacity={0.32} />
              <stop offset="95%" stopColor="#0284c7" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="label" tick={{ fill: "#475569", fontSize: 12 }} />
          <YAxis tick={{ fill: "#475569", fontSize: 12 }} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#ffffff",
              borderColor: "#cbd5e1",
              borderRadius: "8px"
            }}
          />
          <Area
            type="monotone"
            dataKey="aqi"
            name="AQI"
            stroke="#0d9488"
            strokeWidth={2.5}
            fill="url(#aqiGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function PollutantHistoryChart({ data = [], height = 290 }) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 10, right: 16, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="label" tick={{ fill: "#475569", fontSize: 12 }} />
          <YAxis tick={{ fill: "#475569", fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="PM25" name="PM2.5" stroke="#0d9488" strokeWidth={2} />
          <Line type="monotone" dataKey="PM10" name="PM10" stroke="#0284c7" strokeWidth={2} />
          <Line type="monotone" dataKey="NO2" name="NO₂" stroke="#16a34a" strokeWidth={2} />
          <Line type="monotone" dataKey="O3" name="O₃" stroke="#6366f1" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LocationPollutantBarChart({ locations = [], height = 300 }) {
  const chartData = locations.map((item) => ({
    location: item.location,
    AQI: item.aqi,
    PM25: item.pollutants?.PM25?.value || 0,
    PM10: item.pollutants?.PM10?.value || 0,
    NO2: item.pollutants?.NO2?.value || 0
  }));

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <BarChart data={chartData} margin={{ top: 10, right: 16, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="location" tick={{ fill: "#475569", fontSize: 12 }} />
          <YAxis tick={{ fill: "#475569", fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Bar dataKey="AQI" fill="#0284c7" radius={[4, 4, 0, 0]} />
          <Bar dataKey="PM25" name="PM2.5" fill="#0d9488" radius={[4, 4, 0, 0]} />
          <Bar dataKey="PM10" name="PM10" fill="#22c55e" radius={[4, 4, 0, 0]} />
          <Bar dataKey="NO2" name="NO₂" fill="#64748b" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}