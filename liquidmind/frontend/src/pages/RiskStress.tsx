import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from "recharts";
import { getAlerts, getStressScenarios, runStressTest } from "../api/client";
import { HeatmapGrid, PulseIndicator } from "../components";
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

export default function RiskStress() {
  const [stressResult, setStressResult] = useState<any>(null);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);

  const { data: alertsData } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => getAlerts(),
  });

  const { data: scenariosData } = useQuery({
    queryKey: ["scenarios"],
    queryFn: getStressScenarios,
  });

  const stressMut = useMutation({
    mutationFn: runStressTest,
    onSuccess: (data) => setStressResult(data),
  });

  const alerts = alertsData?.alerts || [];
  const scenarios = scenariosData?.scenarios || [];

  const alertHeatmap = alerts.slice(0, 8).map((a: any) => ({
    label: a.title?.split(" ").slice(0, 3).join(" ") || "Alert",
    value: a.projected_impact || 0,
    maxValue: Math.max(...alerts.map((x: any) => x.projected_impact || 0), 1),
    sublabel: a.severity,
  }));

  const alertTypes: Record<string, number> = {};
  alerts.forEach((a: any) => {
    alertTypes[a.alert_type] = (alertTypes[a.alert_type] || 0) + 1;
  });
  const radarData = Object.entries(alertTypes).map(([type, count]) => ({
    type: type.replace(/_/g, " "),
    count,
    fullMark: Math.max(...Object.values(alertTypes), 3),
  }));

  const stressChartData =
    stressResult?.baseline?.map((base: any, i: number) => {
      const stressed = stressResult.stressed[i];
      const days = base.trajectory?.length || 0;
      return Array.from({ length: days }, (_, d) => ({
        day: `Day ${d}`,
        [`${base.bank_name} (Baseline)`]: base.trajectory[d],
        [`${base.bank_name} (Stressed)`]: stressed.trajectory[d],
        threshold: base.min_balance_threshold,
      }));
    }) || [];

  const firstComparison = stressChartData[0] || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-base font-semibold text-ink">Risk & Stress Testing</h1>
        <div className="flex items-center gap-3">
          {(alertsData?.critical_count || 0) > 0 && (
            <PulseIndicator status="critical" label={`${alertsData.critical_count} critical alerts`} />
          )}
          {(alertsData?.critical_count || 0) === 0 && (
            <PulseIndicator status="ok" label="All clear" />
          )}
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Left: Alert Summary + Heatmap */}
        <div className="col-span-4 space-y-3">
          <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
            <h3 className="text-xs font-semibold text-ink uppercase tracking-wider mb-3">Risk Summary</h3>
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="text-center p-2 bg-accent-red/5 rounded-sm border border-accent-red/15">
                <div className="text-xl font-bold font-mono text-accent-red">{alertsData?.critical_count || 0}</div>
                <div className="text-2xs text-ink-3">Critical</div>
              </div>
              <div className="text-center p-2 bg-yellow-500/5 rounded-sm border border-yellow-500/15">
                <div className="text-xl font-bold font-mono text-yellow-600">{alertsData?.warning_count || 0}</div>
                <div className="text-2xs text-ink-3">Warning</div>
              </div>
              <div className="text-center p-2 bg-blue-500/5 rounded-sm border border-blue-500/15">
                <div className="text-xl font-bold font-mono text-blue-600">{alertsData?.advisory_count || 0}</div>
                <div className="text-2xs text-ink-3">Advisory</div>
              </div>
            </div>

            {radarData.length > 0 && (
              <ResponsiveContainer width="100%" height={180}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="rgba(0,0,0,0.06)" />
                  <PolarAngleAxis dataKey="type" stroke="#999999" fontSize={9} />
                  <PolarRadiusAxis stroke="rgba(0,0,0,0.1)" fontSize={8} />
                  <Radar name="Alerts" dataKey="count" stroke="#111111" fill="#c8f03a" fillOpacity={0.3} />
                </RadarChart>
              </ResponsiveContainer>
            )}
          </div>

          {alertHeatmap.length > 0 && (
            <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
              <HeatmapGrid cells={alertHeatmap} cols={2} title="Alert Impact Heatmap" colorScale="risk" />
            </div>
          )}

          <div className="bg-surface rounded-md border border-black/[0.07] shadow-card overflow-hidden">
            <div className="p-3.5 border-b border-black/[0.07]">
              <h3 className="text-xs font-semibold text-ink uppercase tracking-wider">Active Alerts</h3>
            </div>
            <div className="divide-y divide-black/[0.05] max-h-[250px] overflow-y-auto">
              {alerts.length === 0 ? (
                <div className="p-4 text-ink-3 text-xs flex items-center gap-2">
                  <span className="w-2 h-2 bg-accent-green rounded-full" />
                  No active alerts. All clear.
                </div>
              ) : (
                alerts.map((alert: any) => (
                  <div key={alert.id} className="p-3 hover:bg-surface2 transition-colors">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={clsx("px-2 py-0.5 rounded-pill text-2xs font-medium", {
                          "bg-accent-red/10 text-accent-red": alert.severity === "critical",
                          "bg-yellow-500/10 text-yellow-600": alert.severity === "warning",
                          "bg-blue-500/10 text-blue-600": alert.severity === "advisory",
                        })}
                      >
                        {alert.severity}
                      </span>
                      <span className="text-2xs text-ink-4">{alert.alert_type?.replace(/_/g, " ")}</span>
                    </div>
                    <p className="text-xs text-ink-2">{alert.title}</p>
                    <p className="text-2xs text-ink-3 mt-0.5 line-clamp-2">{alert.description}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right: Stress Testing */}
        <div className="col-span-8 space-y-3">
          <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
            <h3 className="text-xs font-semibold text-ink uppercase tracking-wider mb-4">Stress Test Scenarios</h3>
            <div className="grid grid-cols-3 gap-3">
              {scenarios.map((s: any) => (
                <button
                  key={s.id}
                  onClick={() => {
                    setSelectedScenario(s.id);
                    stressMut.mutate(s.id);
                  }}
                  className={clsx(
                    "p-3 rounded-sm border text-left transition-all hover:scale-[1.02]",
                    selectedScenario === s.id
                      ? "border-ink bg-ink/5 shadow-card-md"
                      : "border-black/[0.07] bg-surface2 hover:border-black/[0.15]"
                  )}
                >
                  <div className="text-xs font-medium text-ink">{s.name}</div>
                  <div className="text-2xs text-ink-3 mt-1 line-clamp-2">{s.description}</div>
                  {stressMut.isPending && selectedScenario === s.id && (
                    <div className="flex items-center gap-2 mt-2">
                      <div className="w-3 h-3 border border-ink-3 border-t-transparent rounded-full animate-spin" />
                      <span className="text-2xs text-ink-3">Running...</span>
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Stress Test Results */}
          {stressResult && (
            <>
              <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
                <h3 className="text-xs font-semibold text-ink uppercase tracking-wider mb-3">
                  Impact Summary: <span className="text-ink-2 font-normal">{stressResult.scenario}</span>
                </h3>
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-surface2 rounded-sm p-4 border border-black/[0.07]">
                    <div className="text-2xs text-ink-3 mb-1">Baseline Breaches</div>
                    <div className="text-xl font-bold font-mono text-ink">
                      {stressResult.impact_summary?.baseline_threshold_breaches || 0}
                    </div>
                    <div className="text-[10px] text-ink-4 mt-1">accounts below minimum</div>
                  </div>
                  <div className="bg-accent-red/5 rounded-sm p-4 border border-accent-red/15">
                    <div className="text-2xs text-ink-3 mb-1">Stressed Breaches</div>
                    <div className="text-xl font-bold font-mono text-accent-red">
                      {stressResult.impact_summary?.stressed_threshold_breaches || 0}
                    </div>
                    <div className="text-[10px] text-accent-red/60 mt-1">additional failures under stress</div>
                  </div>
                  <div className="bg-surface2 rounded-sm p-4 border border-black/[0.07]">
                    <div className="text-2xs text-ink-3 mb-1">Total Balance Impact</div>
                    <div className="text-xl font-bold font-mono text-accent-red">
                      {formatCurrency(stressResult.impact_summary?.total_balance_impact || 0)}
                    </div>
                    <div className="text-[10px] text-ink-4 mt-1">aggregate position change</div>
                  </div>
                </div>
              </div>

              {firstComparison.length > 0 && (
                <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
                  <h3 className="text-xs font-semibold text-ink uppercase tracking-wider mb-4">
                    Balance Projection: Baseline vs Stressed
                  </h3>
                  <ResponsiveContainer width="100%" height={280}>
                    <LineChart data={firstComparison}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                      <XAxis dataKey="day" stroke="#999999" fontSize={11} />
                      <YAxis stroke="#999999" fontSize={11} tickFormatter={(v) => formatCurrency(v)} />
                      <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => [formatCurrency(v), ""]} />
                      <Legend />
                      {Object.keys(firstComparison[0] || {})
                        .filter((k) => k !== "day" && k !== "threshold")
                        .map((key) => (
                          <Line
                            key={key}
                            type="monotone"
                            dataKey={key}
                            stroke={key.includes("Stressed") ? "#e03030" : "#111111"}
                            strokeWidth={2}
                            strokeDasharray={key.includes("Stressed") ? "5 5" : undefined}
                            dot={false}
                          />
                        ))}
                      <ReferenceLine
                        y={firstComparison[0]?.threshold || 0}
                        stroke="#e03030"
                        strokeDasharray="10 5"
                        label={{ value: "Min Balance", fill: "#e03030", fontSize: 10 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              <div className="bg-surface rounded-md border border-black/[0.07] shadow-card overflow-hidden">
                <div className="p-4 border-b border-black/[0.07]">
                  <h3 className="text-xs font-semibold text-ink uppercase tracking-wider">Per-Account Stress Results</h3>
                </div>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-ink-3 text-2xs uppercase tracking-wider border-b border-black/[0.07]">
                      <th className="text-left p-3">Account</th>
                      <th className="text-left p-3">Currency</th>
                      <th className="text-center p-3">Baseline</th>
                      <th className="text-center p-3">Stressed</th>
                      <th className="text-right p-3">Min Baseline</th>
                      <th className="text-right p-3">Min Stressed</th>
                      <th className="text-right p-3">Impact</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-black/[0.05]">
                    {stressResult.baseline?.map((base: any, i: number) => {
                      const stressed = stressResult.stressed[i];
                      const minBase = Math.min(...(base.trajectory || [base.min_balance_threshold]));
                      const minStressed = Math.min(...(stressed.trajectory || [0]));
                      const impact = minStressed - minBase;
                      return (
                        <tr key={i} className="hover:bg-surface2 transition-colors">
                          <td className="p-3 text-ink-2">{base.bank_name}</td>
                          <td className="p-3 text-ink-3">{base.currency}</td>
                          <td className="p-3 text-center">
                            {base.breaches_threshold ? (
                              <span className="px-1.5 py-0.5 bg-accent-red/10 text-accent-red text-2xs rounded-pill font-medium">BREACH</span>
                            ) : (
                              <span className="px-1.5 py-0.5 bg-accent-green/10 text-accent-green text-2xs rounded-pill">OK</span>
                            )}
                          </td>
                          <td className="p-3 text-center">
                            {stressed.breaches_threshold ? (
                              <span className="px-1.5 py-0.5 bg-accent-red/10 text-accent-red text-2xs rounded-pill font-medium">BREACH</span>
                            ) : (
                              <span className="px-1.5 py-0.5 bg-accent-green/10 text-accent-green text-2xs rounded-pill">OK</span>
                            )}
                          </td>
                          <td className="p-3 text-right font-mono text-ink-2 text-2xs">
                            {formatCurrency(minBase)}
                          </td>
                          <td className="p-3 text-right font-mono text-ink-2 text-2xs">
                            {formatCurrency(minStressed)}
                          </td>
                          <td className={clsx("p-3 text-right font-mono text-2xs", impact < 0 ? "text-accent-red" : "text-accent-green")}>
                            {impact < 0 ? "" : "+"}{formatCurrency(impact)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {!stressResult && (
            <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-16 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-surface2 flex items-center justify-center">
                <svg className="w-8 h-8 text-ink-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <p className="text-ink-2 text-sm">Select a scenario to run stress test</p>
              <p className="text-ink-3 text-2xs mt-2">Simulates adverse conditions on current positions and forecasted flows</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
