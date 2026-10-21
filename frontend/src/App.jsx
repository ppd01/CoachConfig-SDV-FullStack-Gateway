import React, { useState, useEffect } from "react";
import {
  BatteryCharging,
  Gauge,
  Thermometer,
  Zap,
  AlertTriangle,
  CheckCircle2,
  GitCompare,
  Sliders,
  TrendingUp,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function App() {
  const [telemetry, setTelemetry] = useState({
    soc_pct: 0,
    dc_voltage_v: 0,
    dc_current_a: 0,
    cell_temp_c: 0,
    vehicle_speed_kmh: 0,
    motor_torque_nm: 0,
    traction_power_kw: 0,
    cabin_temp_c: 0,
    hvac_power_kw: 0,
    thermal_derate_active: false,
  });

  const [history, setHistory] = useState([]);
  const [diffData, setDiffData] = useState(null);
  const [validationData, setValidationData] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);

  // Derive host dynamically so this works on both PC and iPad
  const host = window.location.hostname || "localhost";
  const apiBase = `http://${host}:8000`;
  const wsUrl = `ws://${host}:8000/ws/telemetry`;

  // 1. Establish WebSocket Stream for CAN Telemetry
  useEffect(() => {
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setTelemetry(payload);

        // Keep rolling buffer of last 25 samples
        setHistory((prev) => {
          const timestamp = new Date().toLocaleTimeString().split(" ")[0];
          const next = [
            ...prev,
            {
              time: timestamp,
              power: payload.traction_power_kw,
              temp: payload.cell_temp_c,
              speed: payload.vehicle_speed_kmh,
            },
          ];
          return next.slice(-25);
        });
      } catch (err) {
        console.error("Failed to parse telemetry frame:", err);
      }
    };

    return () => ws.close();
  }, [wsUrl]);

  // 2. Poll Analytical Calibration Data & Deployment Gate every 1 second
useEffect(() => {
  const fetchAnalytics = () => {
    fetch('http://192.168.0.66:8000/api/v1/diff?variant_a_id=SETRA-S515-BEV-EXT-RANGE&variant_b_id=SETRA-H2COACH-FCEV-PROTOTYPE')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => setDiffData(data))
      .catch((err) => console.error("Error fetching diff:", err));

    fetch('http://192.168.0.66:8000/api/v1/validate/SETRA-S515-BEV-EXT-RANGE')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => setValidationData(data))
      .catch((err) => console.error("Error fetching validation:", err));
  };

  fetchAnalytics(); // Immediate run on mount
  const interval = setInterval(fetchAnalytics, 1000); // Poll every 1000ms

  return () => clearInterval(interval);
}, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 font-sans">
      {/* Top Banner / System Bar */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center pb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white">
              CoachConfig-AI
            </h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800">
              SDV Gateway POC
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Daimler Buses Calibration & Real-Time In-Vehicle SocketCAN Interface
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-900 border border-slate-800 text-xs">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                wsConnected ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
              }`}
            />
            <span className="text-slate-300 font-medium">
              {wsConnected ? "CAN Bus Online (vcan0)" : "Bus Disconnected"}
            </span>
          </div>
        </div>
      </header>

      {/* Primary Telemetry Grid */}
      <section className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric: SoC */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs uppercase tracking-wider font-semibold">
              Traction Battery SoC
            </span>
            <BatteryCharging className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">
              {telemetry.soc_pct.toFixed(1)}
            </span>
            <span className="text-sm text-slate-400">%</span>
          </div>
          <div className="w-full bg-slate-800 h-2 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-emerald-500 h-full rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, telemetry.soc_pct)}%` }}
            />
          </div>
        </div>

        {/* Metric: Vehicle Speed */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs uppercase tracking-wider font-semibold">
              Vehicle Speed
            </span>
            <Gauge className="w-5 h-5 text-sky-400" />
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">
              {telemetry.vehicle_speed_kmh.toFixed(1)}
            </span>
            <span className="text-sm text-slate-400">km/h</span>
          </div>
          <p className="text-xs text-slate-500 mt-3">
            Torque: {telemetry.motor_torque_nm} Nm
          </p>
        </div>

        {/* Metric: Traction Power */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs uppercase tracking-wider font-semibold">
              Inverter Draw
            </span>
            <Zap className="w-5 h-5 text-amber-400" />
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">
              {telemetry.traction_power_kw.toFixed(1)}
            </span>
            <span className="text-sm text-slate-400">kW</span>
          </div>
          <p className="text-xs text-slate-500 mt-3">
            DC Bus: {telemetry.dc_voltage_v} V | {telemetry.dc_current_a} A
          </p>
        </div>

        {/* Metric: Thermal Battery Monitor */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs uppercase tracking-wider font-semibold">
              Cell Core Temp
            </span>
            <Thermometer
              className={`w-5 h-5 ${
                telemetry.thermal_derate_active
                  ? "text-rose-500 animate-bounce"
                  : "text-sky-400"
              }`}
            />
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">
              {telemetry.cell_temp_c.toFixed(1)}
            </span>
            <span className="text-sm text-slate-400">°C</span>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <span
              className={`text-xs px-2 py-0.5 rounded font-medium ${
                telemetry.thermal_derate_active
                  ? "bg-rose-950 text-rose-300 border border-rose-800"
                  : "bg-emerald-950 text-emerald-300 border border-emerald-800"
              }`}
            >
              {telemetry.thermal_derate_active ? "DERATE ACTIVE" : "OPTIMAL"}
            </span>
            <span className="text-xs text-slate-400">
              HVAC: {telemetry.hvac_power_kw} kW
            </span>
          </div>
        </div>
      </section>

      {/* Real-Time Transient Power & Thermal Graph */}
      <section className="mt-6 bg-slate-900/90 border border-slate-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-amber-400" />
            <h2 className="font-semibold text-white">
              Live Transient Waveform: Inverter Traction vs. Thermal Response
            </h2>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono">
            <span className="flex items-center gap-1.5 text-amber-400">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400" /> Traction (kW)
            </span>
            <span className="flex items-center gap-1.5 text-sky-400">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-400" /> Cell Temp (°C)
            </span>
          </div>
        </div>

        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history}>
              <defs>
                <linearGradient id="powerGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" stroke="#475569" tick={{ fontSize: 10 }} />
              <YAxis stroke="#475569" tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#020617",
                  borderColor: "#334155",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              />
              <Area
                type="monotone"
                dataKey="power"
                stroke="#f59e0b"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#powerGrad)"
                isAnimationActive={false}
              />
              <Area
                type="monotone"
                dataKey="temp"
                stroke="#38bdf8"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#tempGrad)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Analytics & Configuration Intelligence View */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Variant Diff Engine */}
        <div className="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <GitCompare className="w-5 h-5 text-sky-400" />
              <h2 className="font-semibold text-white">
                Variant Delta: Setra S 515 BEV vs. FCEV
              </h2>
            </div>
            {diffData && (
              <span className="text-xs font-semibold px-2 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
                {diffData.differences_count} parameters differing
              </span>
            )}
          </div>

          <div className="mt-4 overflow-x-auto max-h-[380px] overflow-y-auto pr-1">
            <table className="w-full text-left text-xs">
              <thead className="text-slate-400 bg-slate-950/60 sticky top-0">
                <tr>
                  <th className="py-2.5 px-3 rounded-l">Parameter</th>
                  <th className="py-2.5 px-3">Setra BEV</th>
                  <th className="py-2.5 px-3">Setra FCEV</th>
                  <th className="py-2.5 px-3 rounded-r text-right">Impact</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {diffData ? (
                  diffData.differences.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/40">
                      <td className="py-2.5 px-3 text-slate-300 font-sans font-medium">
                        {item.parameter_path}
                      </td>
                      <td className="py-2.5 px-3 text-emerald-400">
                        {item.variant_a_val !== null
                          ? String(item.variant_a_val)
                          : "—"}
                      </td>
                      <td className="py-2.5 px-3 text-sky-400">
                        {item.variant_b_val !== null
                          ? String(item.variant_b_val)
                          : "—"}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            item.impact_level === "CRITICAL"
                              ? "bg-rose-950 text-rose-300 border border-rose-800"
                              : item.impact_level === "WARN"
                              ? "bg-amber-950 text-amber-300 border border-amber-800"
                              : "bg-slate-800 text-slate-400"
                          }`}
                        >
                          {item.impact_level}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="4" className="text-center py-6 text-slate-500">
                      Loading calibration delta matrix...
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Col: Safety & Deployment Gate */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 pb-4 border-b border-slate-800">
              <Sliders className="w-5 h-5 text-indigo-400" />
              <h2 className="font-semibold text-white">Deployment Gate</h2>
            </div>

            <div className="mt-4">
              {validationData ? (
                <>
                  <div
                    className={`flex items-center gap-3 p-3 rounded-lg border ${
                      validationData.is_valid_for_deployment
                        ? "bg-emerald-950/40 border-emerald-800/60 text-emerald-300"
                        : "bg-rose-950/40 border-rose-800/60 text-rose-300"
                    }`}
                  >
                    {validationData.is_valid_for_deployment ? (
                      <CheckCircle2 className="w-5 h-5 shrink-0" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 shrink-0" />
                    )}
                    <div>
                      <p className="text-xs font-bold uppercase tracking-wider">
                        {validationData.is_valid_for_deployment
                          ? "Ready For Bench Deployment"
                          : "Deployment Blocked"}
                      </p>
                      <p className="text-[11px] opacity-80 mt-0.5">
                        Target Variant: {validationData.config_id}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 space-y-3">
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      System Observations ({validationData.issues.length})
                    </p>
                    {validationData.issues.map((issue, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs"
                      >
                        <div className="flex items-center gap-2 text-amber-400 font-semibold mb-1">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          <span>{issue.rule}</span>
                        </div>
                        <p className="text-slate-300 text-[11px] leading-relaxed">
                          {issue.message}
                        </p>
                        <p className="text-slate-500 text-[10px] mt-1.5 font-mono">
                          Action: {issue.suggested_action}
                        </p>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p className="text-slate-500 text-xs text-center py-6">
                  Running automated verification rules...
                </p>
              )}
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 mt-4 text-[11px] text-slate-500 flex justify-between">
            <span>Core: Raspberry Pi 5 Edge Gateway</span>
            <span>AUTOSAR-Aligned</span>
          </div>
        </div>
      </div>
    </div>
  );
}