import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  getAccounts,
  getRecommendations,
  approveRecommendation,
  rejectRecommendation,
  getSavingsMetrics,
} from "../api/client";
import { AnimatedNumber, FlowDiagram } from "../components";
import clsx from "clsx";

function formatCurrency(val: number, ccy = "") {
  const prefix = ccy ? `${ccy} ` : "$";
  if (Math.abs(val) >= 1_000_000) return `${prefix}${(val / 1_000_000).toFixed(2)}M`;
  if (Math.abs(val) >= 1_000) return `${prefix}${(val / 1_000).toFixed(0)}K`;
  return `${prefix}${val.toFixed(0)}`;
}

const TOOLTIP_STYLE = {
  backgroundColor: "#ffffff",
  border: "1px solid rgba(0,0,0,0.1)",
  borderRadius: "10px",
  boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
  color: "#111111",
};

const URGENCY_COLORS: Record<string, string> = {
  critical: "#e03030",
  high: "#f97316",
  medium: "#eab308",
  low: "#999999",
};

export default function Rebalancing() {
  const queryClient = useQueryClient();

  const { data: accountsData } = useQuery({
    queryKey: ["accounts"],
    queryFn: getAccounts,
  });

  const { data: recsData } = useQuery({
    queryKey: ["recommendations"],
    queryFn: getRecommendations,
  });

  const { data: savings } = useQuery({
    queryKey: ["savings"],
    queryFn: getSavingsMetrics,
  });

  const approveMut = useMutation({
    mutationFn: approveRecommendation,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["recommendations"] }),
  });

  const rejectMut = useMutation({
    mutationFn: rejectRecommendation,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["recommendations"] }),
  });

  const accounts = accountsData?.accounts || [];
  const recommendations = recsData?.recommendations || [];

  const flowNodes = accounts.map((a: any) => ({
    id: a.id, label: a.bank_name, currency: a.currency, balance: a.balance, status: a.status,
  }));

  const flowEdges = recommendations.map((r: any) => ({
    from: r.source_id, to: r.target_id, amount: r.amount, urgency: r.urgency,
  }));

  const chartData = recommendations.map((r: any) => ({
    name: `${r.source_bank?.split(" ")[0]} → ${r.target_bank?.split(" ")[0]}`,
    amount: r.amount,
    urgency: r.urgency,
  }));

  const urgencyCounts: Record<string, number> = {};
  recommendations.forEach((r: any) => {
    urgencyCounts[r.urgency] = (urgencyCounts[r.urgency] || 0) + 1;
  });
  const urgencyPie = Object.entries(urgencyCounts).map(([name, value]) => ({ name, value }));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-base font-semibold text-ink">Rebalancing Console</h1>
        <div className="flex items-center gap-2 text-xs">
          <span className="h-[34px] px-3.5 rounded-pill flex items-center bg-surface border border-black/[0.07] text-ink-3 shadow-card">
            {recommendations.length} pending transfer{recommendations.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {/* Savings metrics */}
      {savings && (
        <div className="grid grid-cols-5 gap-3">
          <div className="bg-surface rounded-md p-4 border border-black/[0.07] shadow-card">
            <div className="text-2xs text-ink-3 uppercase tracking-wider">Idle Capital Reduced</div>
            <div className="text-lg font-bold font-mono text-accent-green mt-1">
              <AnimatedNumber value={savings.idle_capital_reduced || 0} formatter={formatCurrency} />
            </div>
            <div className="text-[10px] text-ink-4 mt-1">freed from excess reserves</div>
          </div>
          <div className="bg-surface rounded-md p-4 border border-black/[0.07] shadow-card">
            <div className="text-2xs text-ink-3 uppercase tracking-wider">Avoided Overdrafts</div>
            <div className="text-lg font-bold font-mono text-ink mt-1">
              <AnimatedNumber value={savings.avoided_overdraft_cost || 0} formatter={formatCurrency} />
            </div>
            <div className="text-[10px] text-ink-4 mt-1">penalty costs prevented</div>
          </div>
          <div className="bg-surface rounded-md p-4 border border-black/[0.07] shadow-card">
            <div className="text-2xs text-ink-3 uppercase tracking-wider">Capital Returns</div>
            <div className="text-lg font-bold font-mono text-ink mt-1">
              <AnimatedNumber value={savings.freed_capital_monthly_return || 0} formatter={formatCurrency} />
            </div>
            <div className="text-[10px] text-ink-4 mt-1">monthly yield on freed capital</div>
          </div>
          <div className="bg-surface rounded-md p-4 border border-black/[0.07] shadow-card">
            <div className="text-2xs text-ink-3 uppercase tracking-wider">Transfer Costs</div>
            <div className="text-lg font-bold font-mono text-ink-2 mt-1">
              <AnimatedNumber value={savings.total_cost || 0} formatter={formatCurrency} />
            </div>
            <div className="text-[10px] text-ink-4 mt-1">fees & commissions</div>
          </div>
          <div className="bg-surface rounded-md p-4 border border-accent-green/20 shadow-card">
            <div className="text-2xs text-ink-3 uppercase tracking-wider">Net Monthly Benefit</div>
            <div className="text-lg font-bold font-mono text-accent-green mt-1">
              <AnimatedNumber value={savings.net_monthly_benefit || 0} formatter={formatCurrency} />
            </div>
            <div className="text-[10px] text-accent-green mt-1">after all costs</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-12 gap-4">
        {/* Flow Diagram */}
        <div className="col-span-5 bg-surface rounded-md border border-black/[0.07] shadow-card p-4">
          <h3 className="text-xs font-semibold text-ink uppercase tracking-wider mb-2">Transfer Flow Map</h3>
          {flowNodes.length > 0 && flowEdges.length > 0 ? (
            <div className="h-[380px]">
              <FlowDiagram nodes={flowNodes} edges={flowEdges} />
            </div>
          ) : (
            <div className="h-[380px] flex items-center justify-center">
              <div className="text-center w-full">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={chartData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                    <XAxis type="number" stroke="#999999" fontSize={10} tickFormatter={(v) => formatCurrency(v)} />
                    <YAxis type="category" dataKey="name" stroke="#999999" fontSize={10} width={120} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => [formatCurrency(v), "Amount"]} />
                    <Bar dataKey="amount" radius={[0, 4, 4, 0]}>
                      {chartData.map((entry: any, index: number) => (
                        <Cell key={index} fill={URGENCY_COLORS[entry.urgency] || "#999999"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>

        {/* Recommendations table */}
        <div className="col-span-7 bg-surface rounded-md border border-black/[0.07] shadow-card overflow-hidden">
          <div className="p-4 border-b border-black/[0.07] flex items-center justify-between">
            <h3 className="text-xs font-semibold text-ink uppercase tracking-wider">Transfer Details</h3>
            {urgencyPie.length > 0 && (
              <div className="flex gap-2">
                {urgencyPie.map((u) => (
                  <span key={u.name} className="flex items-center gap-1 text-2xs text-ink-3">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: URGENCY_COLORS[u.name] }} />
                    {u.value} {u.name}
                  </span>
                ))}
              </div>
            )}
          </div>
          {recommendations.length === 0 ? (
            <div className="p-12 text-center">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-accent-green/10 flex items-center justify-center">
                <svg className="w-6 h-6 text-accent-green" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-ink-2 text-sm">All positions are optimally balanced</p>
              <p className="text-2xs text-ink-3 mt-1">No rebalancing needed at this time</p>
            </div>
          ) : (
            <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-surface">
                  <tr className="text-ink-3 text-2xs uppercase tracking-wider border-b border-black/[0.07]">
                    <th className="text-left p-3">Priority</th>
                    <th className="text-left p-3">Source</th>
                    <th className="text-center p-3"></th>
                    <th className="text-left p-3">Target</th>
                    <th className="text-right p-3">Amount</th>
                    <th className="text-right p-3">Cost</th>
                    <th className="text-center p-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-black/[0.05]">
                  {recommendations.map((rec: any) => (
                    <tr key={rec.id} className="hover:bg-surface2 transition-colors group">
                      <td className="p-3">
                        <span
                          className={clsx("px-2 py-0.5 rounded-pill text-2xs font-medium", {
                            "bg-accent-red/10 text-accent-red": rec.urgency === "critical",
                            "bg-orange-500/10 text-orange-600": rec.urgency === "high",
                            "bg-yellow-500/10 text-yellow-600": rec.urgency === "medium",
                            "bg-black/[0.04] text-ink-3": rec.urgency === "low",
                          })}
                        >
                          {rec.urgency}
                        </span>
                      </td>
                      <td className="p-3">
                        <div className="text-ink-2 text-2xs">{rec.source_bank}</div>
                        <div className="text-[10px] text-ink-4">{rec.currency}</div>
                      </td>
                      <td className="p-3 text-center">
                        <span className="text-ink-4 group-hover:text-ink transition-colors">→</span>
                      </td>
                      <td className="p-3">
                        <div className="text-ink-2 text-2xs">{rec.target_bank}</div>
                      </td>
                      <td className="p-3 text-right font-mono text-ink text-2xs font-medium">
                        {formatCurrency(rec.amount, rec.currency)}
                      </td>
                      <td className="p-3 text-right text-ink-3 font-mono text-2xs">
                        ${rec.estimated_cost?.toFixed(2)}
                      </td>
                      <td className="p-3 text-center">
                        <div className="flex gap-1 justify-center opacity-70 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => approveMut.mutate(rec.id)}
                            disabled={approveMut.isPending}
                            className="px-2.5 py-1 bg-ink hover:bg-ink-2 disabled:opacity-50 text-lime text-2xs font-medium rounded-pill transition-colors"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => rejectMut.mutate(rec.id)}
                            disabled={rejectMut.isPending}
                            className="px-2.5 py-1 bg-surface2 hover:bg-black/[0.08] disabled:opacity-50 text-ink-2 text-2xs rounded-pill transition-colors border border-black/[0.07]"
                          >
                            Reject
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
