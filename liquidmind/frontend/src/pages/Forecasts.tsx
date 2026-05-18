import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from "recharts";
import { getAccounts, getAccountForecast, getForecastAccuracy } from "../api/client";
import { AnimatedNumber, PulseIndicator } from "../components";
import clsx from "clsx";

function formatCurrency(val: number) {
  if (Math.abs(val) >= 1_000_000) return `$${(val / 1_000_000).toFixed(2)}M`;
  if (Math.abs(val) >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
  return `$${val.toFixed(0)}`;
}

const TOOLTIP_STYLE = {
  backgroundColor: "#ffffff",
  border: "1px solid rgba(0,0,0,0.1)",
  borderRadius: "10px",
  boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
  color: "#111111",
};

export default function Forecasts() {
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [chartView, setChartView] = useState<"bar" | "area">("bar");

  const { data: accountsData } = useQuery({
    queryKey: ["accounts"],
    queryFn: getAccounts,
  });

  const { data: forecastData, isLoading: loadingForecast } = useQuery({
    queryKey: ["forecast", selectedAccount],
    queryFn: () => getAccountForecast(selectedAccount!),
    enabled: !!selectedAccount,
  });

  const { data: accuracy } = useQuery({
    queryKey: ["forecast-accuracy"],
    queryFn: getForecastAccuracy,
  });

  const accounts = accountsData?.accounts || [];
  const forecasts = forecastData?.forecasts || [];
  const historical = forecastData?.historical_30d || [];

  const chartData = historical.map((day: any) => {
    const totalIn = Object.values(day.inflows || {}).reduce(
      (s: number, ch: any) => s + (ch.total || 0),
      0
    );
    const totalOut = Object.values(day.outflows || {}).reduce(
      (s: number, ch: any) => s + (ch.total || 0),
      0
    );
    return {
      date: day.date?.split("T")[0]?.slice(5),
      inflows: totalIn,
      outflows: -totalOut,
      net: totalIn - totalOut,
    };
  });

  const latestDay = historical[historical.length - 1];
  const channelBreakdown = latestDay ? [
    ...Object.entries(latestDay.inflows || {}).map(([ch, data]: [string, any]) => ({
      channel: ch, direction: "in", total: data.total || 0, count: data.count || 0,
    })),
    ...Object.entries(latestDay.outflows || {}).map(([ch, data]: [string, any]) => ({
      channel: ch, direction: "out", total: data.total || 0, count: data.count || 0,
    })),
  ].sort((a, b) => b.total - a.total) : [];
  const channelMax = channelBreakdown.length > 0 ? Math.max(...channelBreakdown.map(c => c.total)) : 1;

  const forecastChart = forecasts.map((f: any) => ({
    date: f.horizon_date,
    predicted: f.predicted_net,
    low: f.confidence_low,
    high: f.confidence_high,
  }));

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-base font-semibold text-ink">Cash Flow Forecasts</h1>
        <div className="flex items-center gap-4">
          {accuracy && accuracy.sample_count > 0 && (
            <div className="flex gap-4 text-xs bg-surface rounded-pill px-4 py-2 border border-black/[0.07] shadow-card">
              <div className="flex items-center gap-2">
                <PulseIndicator status="ok" size="sm" />
                <span className="text-ink-3">
                  MAE: <span className="text-ink font-mono">{formatCurrency(accuracy.mae)}</span>
                </span>
              </div>
              <div className="border-l border-black/[0.07]" />
              <span className="text-ink-3">
                Direction: <span className="text-ink font-mono">{(accuracy.directional_accuracy * 100).toFixed(1)}%</span>
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Account selector */}
      <div className="flex gap-1.5 flex-wrap">
        {accounts.map((acct: any) => (
          <button
            key={acct.id}
            onClick={() => setSelectedAccount(acct.id)}
            className={clsx(
              "h-[34px] px-4 rounded-pill text-xs font-medium transition-all",
              selectedAccount === acct.id
                ? "bg-ink text-lime"
                : "bg-surface border border-black/[0.07] text-ink-3 hover:text-ink hover:border-black/[0.15] shadow-card"
            )}
          >
            {acct.bank_name} ({acct.currency})
          </button>
        ))}
      </div>

      {!selectedAccount ? (
        <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-16 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-surface2 flex items-center justify-center">
            <svg className="w-8 h-8 text-ink-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
            </svg>
          </div>
          <p className="text-ink-2 text-sm">Select an account to view its cash flow forecast</p>
          <p className="text-ink-3 text-2xs mt-2">Forecasts generated using LightGBM with 50+ engineered features</p>
        </div>
      ) : loadingForecast ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-ink-4 border-t-ink rounded-full animate-spin" />
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Historical flows */}
            <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-semibold text-ink uppercase tracking-wider">Historical Flows (30d)</h3>
                <div className="flex gap-1">
                  <button
                    onClick={() => setChartView("bar")}
                    className={clsx("px-2.5 py-0.5 rounded-pill text-2xs transition-colors", chartView === "bar" ? "bg-ink text-lime" : "text-ink-3 hover:text-ink")}
                  >
                    Bar
                  </button>
                  <button
                    onClick={() => setChartView("area")}
                    className={clsx("px-2.5 py-0.5 rounded-pill text-2xs transition-colors", chartView === "area" ? "bg-ink text-lime" : "text-ink-3 hover:text-ink")}
                  >
                    Area
                  </button>
                </div>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                {chartView === "bar" ? (
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                    <XAxis dataKey="date" stroke="#999999" fontSize={10} />
                    <YAxis stroke="#999999" fontSize={10} tickFormatter={(v) => formatCurrency(Math.abs(v))} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => [formatCurrency(Math.abs(v)), ""]} />
                    <Legend />
                    <Bar dataKey="inflows" fill="#28a828" name="Inflows" radius={[2, 2, 0, 0]} />
                    <Bar dataKey="outflows" fill="#e03030" name="Outflows" radius={[2, 2, 0, 0]} />
                    <ReferenceLine y={0} stroke="#999999" />
                  </BarChart>
                ) : (
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="inGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#28a828" stopOpacity={0.15} />
                        <stop offset="100%" stopColor="#28a828" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="outGrad" x1="0" y1="1" x2="0" y2="0">
                        <stop offset="0%" stopColor="#e03030" stopOpacity={0.15} />
                        <stop offset="100%" stopColor="#e03030" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                    <XAxis dataKey="date" stroke="#999999" fontSize={10} />
                    <YAxis stroke="#999999" fontSize={10} tickFormatter={(v) => formatCurrency(Math.abs(v))} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => [formatCurrency(Math.abs(v)), ""]} />
                    <Area type="monotone" dataKey="inflows" stroke="#28a828" fill="url(#inGrad)" name="Inflows" />
                    <Area type="monotone" dataKey="outflows" stroke="#e03030" fill="url(#outGrad)" name="Outflows" />
                    <ReferenceLine y={0} stroke="#999999" />
                  </AreaChart>
                )}
              </ResponsiveContainer>
            </div>

            {/* Forecast with confidence band */}
            <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
              <h3 className="text-xs font-semibold text-ink uppercase tracking-wider mb-4">Predicted Net Flow (5-day horizon)</h3>
              {forecastChart.length === 0 ? (
                <div className="flex items-center justify-center h-[300px] text-ink-3">
                  <div className="text-center">
                    <p className="text-sm">No forecast data available</p>
                    <p className="text-2xs text-ink-4 mt-1">Run the forecast engine to generate predictions</p>
                  </div>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={forecastChart}>
                    <defs>
                      <linearGradient id="confGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#c8f03a" stopOpacity={0.2} />
                        <stop offset="100%" stopColor="#c8f03a" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                    <XAxis dataKey="date" stroke="#999999" fontSize={10} />
                    <YAxis stroke="#999999" fontSize={10} tickFormatter={(v) => formatCurrency(v)} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number, name: string) => [formatCurrency(v), name]} />
                    <Area type="monotone" dataKey="high" stroke="none" fill="url(#confGrad)" name="Upper Bound" />
                    <Line type="monotone" dataKey="predicted" stroke="#111111" strokeWidth={2.5} name="Predicted" dot={{ fill: "#111111", r: 4 }} />
                    <Line type="monotone" dataKey="high" stroke="#c8f03a" strokeDasharray="3 3" strokeWidth={1} dot={false} name="P95" />
                    <Line type="monotone" dataKey="low" stroke="#c8f03a" strokeDasharray="3 3" strokeWidth={1} dot={false} name="P5" />
                    <ReferenceLine y={0} stroke="#999999" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Bottom row */}
          <div className="grid grid-cols-3 gap-4">
            {/* Channel breakdown */}
            <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
              <h3 className="text-xs font-semibold text-ink uppercase tracking-wider mb-3">Channel Breakdown (Latest)</h3>
              {channelBreakdown.length === 0 ? (
                <p className="text-ink-3 text-xs">No channel data</p>
              ) : (
                <div className="space-y-2">
                  {channelBreakdown.slice(0, 8).map((ch, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={clsx("w-1.5 h-1.5 rounded-full", ch.direction === "in" ? "bg-accent-green" : "bg-accent-red")} />
                        <span className="text-2xs text-ink-2 capitalize">{ch.channel}</span>
                        <span className="text-[10px] text-ink-4">({ch.direction})</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-black/[0.04] rounded-full overflow-hidden">
                          <div
                            className={clsx("h-full rounded-full transition-all duration-500", ch.direction === "in" ? "bg-accent-green" : "bg-accent-red")}
                            style={{ width: `${Math.min(100, (ch.total / channelMax) * 100)}%` }}
                          />
                        </div>
                        <span className="text-2xs font-mono text-ink-2 w-14 text-right">{formatCurrency(ch.total)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Forecast summary cards */}
            {forecasts.length > 0 && (
              <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
                <h3 className="text-xs font-semibold text-ink uppercase tracking-wider mb-3">Forecast Summary</h3>
                <div className="space-y-2">
                  {forecasts.slice(0, 5).map((f: any, i: number) => (
                    <div key={i} className="flex items-center justify-between p-2 bg-surface2 rounded-sm hover:bg-black/[0.04] transition-colors">
                      <div>
                        <div className="text-2xs text-ink-3">Day {i + 1}</div>
                        <div className="text-[10px] text-ink-4">{f.horizon_date}</div>
                      </div>
                      <div className="text-right">
                        <div className={clsx("text-xs font-mono font-bold", f.predicted_net >= 0 ? "text-accent-green" : "text-accent-red")}>
                          {f.predicted_net >= 0 ? "+" : ""}{formatCurrency(f.predicted_net)}
                        </div>
                        <div className="text-[10px] text-ink-4">
                          [{formatCurrency(f.confidence_low)} / {formatCurrency(f.confidence_high)}]
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Feature Importance */}
            {forecasts.length > 0 && forecasts[0].features_json && (
              <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
                <h3 className="text-xs font-semibold text-ink uppercase tracking-wider mb-3">Key Forecast Drivers</h3>
                <div className="space-y-2">
                  {Object.entries(forecasts[0].features_json)
                    .slice(0, 5)
                    .map(([key, value]: [string, any], i: number) => (
                      <div key={key} className="flex items-center justify-between p-2 bg-surface2 rounded-sm">
                        <div className="flex items-center gap-2">
                          <div className="w-5 h-5 rounded bg-lime/30 flex items-center justify-center text-[9px] text-ink font-bold">
                            {i + 1}
                          </div>
                          <span className="text-2xs text-ink-2">{key.replace(/_/g, " ")}</span>
                        </div>
                        <span className="text-2xs font-mono text-ink">
                          {typeof value === "number"
                            ? (Math.abs(value) >= 1000 ? formatCurrency(value) : value.toFixed(4))
                            : String(value)}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
