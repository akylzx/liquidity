import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { getAccounts, getAlerts, getRecommendations, approveRecommendation, getAccountHistory, getStressScenarios, runStressTest } from "../api/client";
import { AnimatedNumber, LiquidityGauge, Sparkline, PulseIndicator } from "../components";
import clsx from "clsx";

function formatCurrency(val: number, ccy = "USD") {
  if (Math.abs(val) >= 1_000_000) return `${ccy} ${(val / 1_000_000).toFixed(2)}M`;
  if (Math.abs(val) >= 1_000) return `${ccy} ${(val / 1_000).toFixed(0)}K`;
  return `${ccy} ${val.toFixed(0)}`;
}

const currencyFormatter = (val: number) => {
  if (Math.abs(val) >= 1_000_000) return `$${(val / 1_000_000).toFixed(2)}M`;
  if (Math.abs(val) >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
  return `$${val.toFixed(0)}`;
};

const TOOLTIP_STYLE = {
  backgroundColor: "#ffffff",
  border: "1px solid rgba(0,0,0,0.1)",
  borderRadius: "10px",
  boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
  color: "#111111",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={clsx("inline-block w-2.5 h-2.5 rounded-full", {
        "bg-accent-green": status === "green",
        "bg-yellow-500": status === "yellow",
        "bg-accent-red": status === "red",
      })}
    />
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      className={clsx("px-2 py-0.5 rounded-pill text-2xs font-medium", {
        "bg-accent-red/10 text-accent-red": severity === "critical",
        "bg-yellow-500/10 text-yellow-600": severity === "warning",
        "bg-blue-500/10 text-blue-600": severity === "advisory",
      })}
    >
      {severity.toUpperCase()}
    </span>
  );
}

export default function CommandCenter() {
  const queryClient = useQueryClient();
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [stressResult, setStressResult] = useState<any>(null);

  const { data: accountsData, isLoading: loadingAccounts } = useQuery({
    queryKey: ["accounts"],
    queryFn: getAccounts,
  });
  const { data: alertsData } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => getAlerts(),
  });
  const { data: recsData } = useQuery({
    queryKey: ["recommendations"],
    queryFn: getRecommendations,
  });
  const { data: historyData } = useQuery({
    queryKey: ["account-history", selectedAccountId],
    queryFn: () => getAccountHistory(selectedAccountId!, 30),
    enabled: !!selectedAccountId,
  });

  const approveMut = useMutation({
    mutationFn: approveRecommendation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recommendations"] });
    },
  });

  const { data: scenariosData } = useQuery({
    queryKey: ["scenarios"],
    queryFn: getStressScenarios,
  });
  const stressMut = useMutation({
    mutationFn: runStressTest,
    onSuccess: (data) => setStressResult(data),
  });
  const scenarios = scenariosData?.scenarios || [];

  const accounts = accountsData?.accounts || [];
  const summary = accountsData?.summary || {};
  const alerts = alertsData?.alerts || [];
  const recommendations = recsData?.recommendations || [];

  if (loadingAccounts) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-ink-4 border-t-ink rounded-full animate-spin" />
          <div className="text-ink-3 text-sm">Loading treasury positions...</div>
        </div>
      </div>
    );
  }

  const currencyDist: Record<string, number> = {};
  accounts.forEach((a: any) => {
    currencyDist[a.currency] = (currencyDist[a.currency] || 0) + a.balance;
  });
  const pieData = Object.entries(currencyDist).map(([name, value]) => ({ name, value }));
  const PIE_COLORS = ["#111111", "#c8f03a", "#28a828", "#555555", "#e03030"];

  const generateSparkline = (balance: number, seed: number) => {
    const points = [];
    let v = balance * 0.9;
    for (let i = 0; i < 14; i++) {
      v += (Math.sin(seed + i) * 0.5 - 0.24) * balance * 0.02;
      points.push(v);
    }
    points.push(balance);
    return points;
  };

  const historyChart = (historyData?.history || []).map((h: any) => ({
    date: h.date?.split("T")[0]?.slice(5),
    balance: h.balance,
    min: h.min_balance,
    max: h.max_balance,
  }));

  return (
    <div className="space-y-4">
      {/* Top Summary Bar */}
      <div className="grid grid-cols-5 gap-3">
        <div className="bg-surface rounded-md p-4 border border-black/[0.07] shadow-card">
          <div className="text-2xs text-ink-3 uppercase tracking-wider">Total Liquidity</div>
          <div className="text-xl font-bold font-mono text-ink mt-1">
            <AnimatedNumber value={summary.total_balance || 0} formatter={currencyFormatter} />
          </div>
          <Sparkline data={accounts.map((a: any) => a.balance).slice(0, 8)} color="#111111" width={100} height={20} />
        </div>
        <div className="bg-surface rounded-md p-4 border border-black/[0.07] shadow-card">
          <div className="text-2xs text-ink-3 uppercase tracking-wider">In-Flight Inbound</div>
          <div className="text-xl font-bold font-mono text-ink mt-1">
            <AnimatedNumber value={summary.total_in_flight_in || 0} formatter={currencyFormatter} />
          </div>
          <div className="mt-1 flex items-center gap-1">
            <PulseIndicator status="ok" size="sm" />
            <span className="text-2xs text-ink-3">Settlements on track</span>
          </div>
        </div>
        <div className="bg-surface rounded-md p-4 border border-black/[0.07] shadow-card">
          <div className="text-2xs text-ink-3 uppercase tracking-wider">Accounts</div>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xl font-bold font-mono text-ink">{summary.account_count || 0}</span>
            <div className="flex gap-2 text-xs font-mono">
              <span className="text-accent-green">{summary.green_count}</span>
              <span className="text-yellow-600">{summary.yellow_count}</span>
              <span className="text-accent-red">{summary.red_count}</span>
            </div>
          </div>
          <div className="mt-1.5 flex gap-0.5 h-1.5 rounded-full overflow-hidden bg-black/[0.04]">
            <div className="bg-accent-green transition-all rounded-full" style={{ flex: summary.green_count || 0 }} />
            <div className="bg-yellow-500 transition-all rounded-full" style={{ flex: summary.yellow_count || 0 }} />
            <div className="bg-accent-red transition-all rounded-full" style={{ flex: summary.red_count || 0 }} />
          </div>
        </div>
        <div className="bg-surface rounded-md p-4 border border-black/[0.07] shadow-card">
          <div className="text-2xs text-ink-3 uppercase tracking-wider">Active Alerts</div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xl font-bold font-mono text-ink">{alertsData?.count || 0}</span>
            {(alertsData?.critical_count || 0) > 0 && (
              <PulseIndicator status="critical" size="md" label={`${alertsData.critical_count} critical`} />
            )}
          </div>
        </div>
        <div className="bg-surface rounded-md p-4 border border-black/[0.07] shadow-card">
          <div className="text-2xs text-ink-3 uppercase tracking-wider">Pending Actions</div>
          <div className="text-xl font-bold font-mono text-ink mt-1">{recommendations.length}</div>
          <div className="text-2xs text-ink-3 mt-1">rebalancing transfers</div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Account List - Left Panel */}
        <div className="col-span-3 bg-surface rounded-md border border-black/[0.07] shadow-card overflow-hidden">
          <div className="p-3.5 border-b border-black/[0.07] flex items-center justify-between">
            <h2 className="text-xs font-semibold text-ink uppercase tracking-wider">Nostro Accounts</h2>
            <span className="text-2xs text-ink-4">{accounts.length} active</span>
          </div>
          <div className="divide-y divide-black/[0.05] max-h-[520px] overflow-y-auto">
            {accounts.map((acct: any, idx: number) => (
              <div
                key={acct.id}
                onClick={() => setSelectedAccountId(acct.id === selectedAccountId ? null : acct.id)}
                className={clsx(
                  "p-3 cursor-pointer transition-all",
                  selectedAccountId === acct.id
                    ? "bg-lime/10 border-l-2 border-l-lime-dark"
                    : "hover:bg-surface2 border-l-2 border-l-transparent"
                )}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={acct.status} />
                    <span className="text-xs font-medium text-ink">{acct.bank_name}</span>
                  </div>
                  <span className="text-2xs text-ink-3 font-mono">{acct.currency}</span>
                </div>
                <div className="mt-1.5 flex items-center justify-between">
                  <span className="text-xs font-mono text-ink-2">{formatCurrency(acct.balance, acct.currency)}</span>
                  <Sparkline
                    data={generateSparkline(acct.balance, idx * 7)}
                    width={60}
                    height={18}
                    color={acct.status === "red" ? "#e03030" : acct.status === "yellow" ? "#eab308" : "#28a828"}
                    showArea={false}
                  />
                </div>
                <div className="mt-1.5 h-1 bg-black/[0.04] rounded-full overflow-hidden">
                  <div
                    className={clsx("h-full rounded-full transition-all duration-700", {
                      "bg-accent-green": acct.status === "green",
                      "bg-yellow-500": acct.status === "yellow",
                      "bg-accent-red": acct.status === "red",
                    })}
                    style={{ width: `${Math.min(100, (acct.balance / (acct.max_balance || acct.balance)) * 100)}%` }}
                  />
                </div>
                <div className="mt-1 flex justify-between text-[10px] text-ink-4">
                  <span>min: {formatCurrency(acct.min_balance, "")}</span>
                  {acct.in_flight_in > 0 && (
                    <span className="text-accent-green">+{formatCurrency(acct.in_flight_in, "")} inbound</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Center - Charts */}
        <div className="col-span-6 space-y-3">
          <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-semibold text-ink uppercase tracking-wider">
                {selectedAccountId
                  ? `Balance Trend — ${accounts.find((a: any) => a.id === selectedAccountId)?.bank_name || ""}`
                  : "Portfolio Overview"}
              </h2>
              {selectedAccountId && (
                <button
                  onClick={() => setSelectedAccountId(null)}
                  className="text-2xs text-ink-3 hover:text-ink transition-colors px-2.5 py-1 rounded-pill border border-black/[0.1] hover:border-black/[0.2]"
                >
                  Show All
                </button>
              )}
            </div>

            {selectedAccountId && historyChart.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={historyChart}>
                  <defs>
                    <linearGradient id="balGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#111111" stopOpacity={0.1} />
                      <stop offset="95%" stopColor="#111111" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                  <XAxis dataKey="date" stroke="#999999" fontSize={10} />
                  <YAxis stroke="#999999" fontSize={10} tickFormatter={(v) => `${(v / 1e6).toFixed(1)}M`} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => [currencyFormatter(v), ""]} />
                  <Area type="monotone" dataKey="max" stroke="none" fill="#28a828" fillOpacity={0.04} name="Max" />
                  <Area type="monotone" dataKey="balance" stroke="#111111" fill="url(#balGrad)" strokeWidth={2} name="Avg Balance" />
                  <Area type="monotone" dataKey="min" stroke="#e03030" fill="none" strokeDasharray="4 4" strokeWidth={1} name="Min" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={accounts.map((a: any) => ({
                  name: a.bank_name.split(" ")[0],
                  balance: a.balance,
                  min_threshold: a.min_balance,
                }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                  <XAxis dataKey="name" stroke="#999999" fontSize={10} />
                  <YAxis stroke="#999999" fontSize={10} tickFormatter={(v) => `${(v / 1e6).toFixed(1)}M`} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number, name: string) => [currencyFormatter(v), name]} />
                  <Bar dataKey="balance" fill="#111111" radius={[4, 4, 0, 0]} name="Balance" />
                  <Bar dataKey="min_threshold" fill="#e03030" radius={[4, 4, 0, 0]} name="Min Threshold" opacity={0.3} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
              <h3 className="text-2xs font-semibold text-ink-3 uppercase tracking-wider mb-3">Currency Distribution</h3>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={65}
                    paddingAngle={3}
                    dataKey="value"
                    nameKey="name"
                    label={({ name, percent }: any) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                    fontSize={9}
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number, name: string) => [currencyFormatter(v), name]} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-wrap justify-center gap-3 mt-1">
                {pieData.map((item, i) => (
                  <div key={item.name} className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                    <span className="text-2xs text-ink-3">{item.name}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
              <h3 className="text-2xs font-semibold text-ink-3 uppercase tracking-wider mb-3">Liquidity Health</h3>
              <div className="grid grid-cols-2 gap-2">
                {accounts.slice(0, 4).map((acct: any) => (
                  <LiquidityGauge
                    key={acct.id}
                    value={acct.balance}
                    min={acct.min_balance}
                    max={acct.max_balance || acct.balance * 1.5}
                    label={acct.bank_name.split(" ")[0]}
                    currency={acct.currency}
                    size={80}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right - Alerts + Quick Actions */}
        <div className="col-span-3 space-y-3">
          <div className="bg-surface rounded-md border border-black/[0.07] shadow-card overflow-hidden">
            <div className="p-3.5 border-b border-black/[0.07] flex items-center justify-between">
              <h2 className="text-xs font-semibold text-ink uppercase tracking-wider">Active Alerts</h2>
              {(alertsData?.critical_count || 0) > 0 && (
                <span className="w-2 h-2 bg-accent-red rounded-full animate-pulse" />
              )}
            </div>
            <div className="divide-y divide-black/[0.05] max-h-[300px] overflow-y-auto">
              {alerts.length === 0 ? (
                <div className="p-4 text-ink-3 text-xs flex items-center gap-2">
                  <span className="w-2 h-2 bg-accent-green rounded-full" />
                  No active alerts
                </div>
              ) : (
                alerts.slice(0, 8).map((alert: any) => (
                  <div key={alert.id} className="p-3 hover:bg-surface2 transition-colors">
                    <div className="flex items-center gap-2 mb-1">
                      <SeverityBadge severity={alert.severity} />
                      <span className="text-2xs text-ink-4">
                        {alert.horizon_hours ? `T+${alert.horizon_hours}h` : "Now"}
                      </span>
                    </div>
                    <p className="text-xs text-ink-2">{alert.title}</p>
                    {alert.projected_impact && (
                      <p className="text-2xs text-ink-3 mt-0.5">
                        Impact: <span className="text-accent-red font-mono">{formatCurrency(alert.projected_impact)}</span>
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
            <h3 className="text-2xs font-semibold text-ink-3 uppercase tracking-wider mb-3">Pending Transfers</h3>
            {recommendations.length === 0 ? (
              <p className="text-xs text-ink-3">All positions balanced</p>
            ) : (
              <div className="space-y-2">
                {recommendations.slice(0, 4).map((rec: any) => (
                  <div key={rec.id} className="flex items-center justify-between p-2 bg-surface2 rounded-sm group hover:bg-black/[0.04] transition-colors">
                    <div className="flex-1 min-w-0">
                      <div className="text-2xs text-ink-3 truncate">
                        {rec.source_bank} → {rec.target_bank}
                      </div>
                      <div className="text-xs font-mono text-ink font-medium">
                        {formatCurrency(rec.amount, rec.currency)}
                      </div>
                    </div>
                    <button
                      onClick={() => approveMut.mutate(rec.id)}
                      disabled={approveMut.isPending}
                      className="px-2.5 py-1 bg-ink hover:bg-ink-2 disabled:opacity-50 text-lime text-2xs font-medium rounded-pill transition-colors"
                    >
                      Approve
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick Stress Test */}
          <div className="bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
            <h3 className="text-2xs font-semibold text-ink-3 uppercase tracking-wider mb-3">Quick Stress Test</h3>
            <div className="space-y-1.5">
              {scenarios.slice(0, 4).map((s: any) => (
                <button
                  key={s.id}
                  onClick={() => stressMut.mutate(s.id)}
                  disabled={stressMut.isPending}
                  className={clsx(
                    "w-full text-left p-2 rounded-sm border transition-all text-2xs",
                    stressResult?.scenario === s.name
                      ? "border-ink bg-ink/5"
                      : "border-black/[0.07] bg-surface2 hover:border-black/[0.15]"
                  )}
                >
                  <div className="font-medium text-ink">{s.name}</div>
                  {stressMut.isPending && stressMut.variables === s.id && (
                    <div className="flex items-center gap-1.5 mt-1">
                      <div className="w-2.5 h-2.5 border border-ink-3 border-t-transparent rounded-full animate-spin" />
                      <span className="text-ink-3">Running...</span>
                    </div>
                  )}
                </button>
              ))}
            </div>
            {stressResult && (
              <div className="mt-3 p-2.5 rounded-sm bg-surface2 border border-black/[0.07]">
                <div className="text-2xs text-ink-3 mb-1.5">{stressResult.scenario}</div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <div className="text-[10px] text-ink-4">Breaches</div>
                    <div className="text-sm font-mono font-bold text-accent-red">
                      {stressResult.impact_summary?.stressed_threshold_breaches || 0}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-ink-4">Impact</div>
                    <div className="text-sm font-mono font-bold text-accent-red">
                      {currencyFormatter(stressResult.impact_summary?.total_balance_impact || 0)}
                    </div>
                  </div>
                </div>
                <div className="mt-1.5 text-[10px] text-ink-4">
                  {stressResult.impact_summary?.additional_breaches || 0} additional breaches vs baseline
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
