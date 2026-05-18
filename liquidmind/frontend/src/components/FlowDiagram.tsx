import { useMemo } from "react";

interface FlowNode {
  id: string;
  label: string;
  currency: string;
  balance: number;
  status: string;
}

interface FlowEdge {
  from: string;
  to: string;
  amount: number;
  urgency: string;
}

interface FlowDiagramProps {
  nodes: FlowNode[];
  edges: FlowEdge[];
}

const URGENCY_COLORS: Record<string, string> = {
  critical: "#e03030",
  high: "#f97316",
  medium: "#eab308",
  low: "#999999",
};

// Deterministic pseudo-random based on seed
function seededOffset(seed: number): number {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return (x - Math.floor(x)) - 0.5; // returns -0.5 to 0.5
}

export default function FlowDiagram({ nodes, edges }: FlowDiagramProps) {
  const width = 500;
  const height = 400;
  const cx = width / 2;
  const cy = height / 2;
  const r = 150;

  const nodePositions = useMemo(() => {
    if (nodes.length === 0) return [];
    return nodes.map((_, i) => {
      const angle = (i / nodes.length) * 2 * Math.PI - Math.PI / 2;
      return {
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
      };
    });
  }, [nodes.length]);

  const edgePaths = useMemo(() => {
    return edges.map((edge, i) => {
      const fromIdx = nodes.findIndex((n) => n.id === edge.from);
      const toIdx = nodes.findIndex((n) => n.id === edge.to);
      if (fromIdx < 0 || toIdx < 0 || nodePositions.length === 0) return null;

      const from = nodePositions[fromIdx];
      const to = nodePositions[toIdx];
      const midX = (from.x + to.x) / 2 + seededOffset(i * 7 + 3) * 30;
      const midY = (from.y + to.y) / 2 + seededOffset(i * 13 + 5) * 30;
      return { from, to, midX, midY, color: URGENCY_COLORS[edge.urgency] || "#999999" };
    });
  }, [nodes, edges, nodePositions]);

  if (nodes.length === 0) return null;

  const formatVal = (v: number) => {
    if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
    if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
    return v.toFixed(0);
  };

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
      <defs>
        <marker id="arrowhead" markerWidth="6" markerHeight="4" refX="6" refY="2" orient="auto">
          <polygon points="0 0, 6 2, 0 4" fill="#999999" />
        </marker>
      </defs>

      {/* Edges */}
      {edges.map((edge, i) => {
        const ep = edgePaths[i];
        if (!ep) return null;

        return (
          <g key={`edge-${i}`}>
            <path
              d={`M ${ep.from.x} ${ep.from.y} Q ${ep.midX} ${ep.midY} ${ep.to.x} ${ep.to.y}`}
              fill="none"
              stroke={ep.color}
              strokeWidth={2}
              strokeOpacity={0.6}
              strokeDasharray="8 4"
              markerEnd="url(#arrowhead)"
            >
              <animate
                attributeName="stroke-dashoffset"
                from="24"
                to="0"
                dur="1.5s"
                repeatCount="indefinite"
              />
            </path>
            <text
              x={ep.midX}
              y={ep.midY - 8}
              textAnchor="middle"
              className="text-[9px]"
              fill="#555555"
            >
              {formatVal(edge.amount)}
            </text>
          </g>
        );
      })}

      {/* Nodes */}
      {nodes.map((node, i) => {
        const pos = nodePositions[i];
        if (!pos) return null;
        const statusColor = node.status === "green" ? "#28a828" : node.status === "yellow" ? "#eab308" : "#e03030";

        return (
          <g key={node.id}>
            <circle cx={pos.x} cy={pos.y} r={28} fill="#ffffff" stroke={statusColor} strokeWidth={2} />
            {node.status === "red" && (
              <circle cx={pos.x} cy={pos.y} r={28} fill="none" stroke="#e03030" strokeWidth={1}>
                <animate attributeName="r" from="28" to="36" dur="1.5s" repeatCount="indefinite" />
                <animate attributeName="opacity" from="0.6" to="0" dur="1.5s" repeatCount="indefinite" />
              </circle>
            )}
            <text x={pos.x} y={pos.y - 4} textAnchor="middle" className="text-[9px] font-medium" fill="#111111">
              {node.label.split(" ")[0]}
            </text>
            <text x={pos.x} y={pos.y + 10} textAnchor="middle" className="text-[8px]" fill="#999999">
              {node.currency} {formatVal(node.balance)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
