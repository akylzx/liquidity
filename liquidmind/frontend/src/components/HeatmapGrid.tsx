import clsx from "clsx";

interface HeatmapCell {
  label: string;
  value: number;
  maxValue: number;
  sublabel?: string;
}

interface HeatmapGridProps {
  cells: HeatmapCell[];
  cols?: number;
  title?: string;
  colorScale?: "risk" | "volume" | "divergence";
}

function getColor(ratio: number, scale: string): string {
  if (scale === "risk") {
    if (ratio > 0.8) return "bg-accent-red/10 border-accent-red/30";
    if (ratio > 0.5) return "bg-orange-500/10 border-orange-500/25";
    if (ratio > 0.25) return "bg-yellow-500/10 border-yellow-500/25";
    return "bg-accent-green/5 border-accent-green/15";
  }
  if (scale === "divergence") {
    if (ratio > 0.7) return "bg-purple-500/10 border-purple-500/25";
    if (ratio > 0.4) return "bg-blue-500/10 border-blue-500/25";
    return "bg-black/[0.03] border-black/[0.07]";
  }
  // volume
  if (ratio > 0.8) return "bg-blue-500/10 border-blue-500/25";
  if (ratio > 0.5) return "bg-blue-500/7 border-blue-500/20";
  if (ratio > 0.25) return "bg-blue-500/5 border-blue-500/15";
  return "bg-black/[0.03] border-black/[0.07]";
}

export default function HeatmapGrid({
  cells,
  cols = 4,
  title,
  colorScale = "risk",
}: HeatmapGridProps) {
  return (
    <div>
      {title && (
        <h4 className="text-xs font-semibold text-ink-3 uppercase tracking-wider mb-2">
          {title}
        </h4>
      )}
      <div className={`grid gap-2`} style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
        {cells.map((cell, i) => {
          const ratio = cell.maxValue > 0 ? cell.value / cell.maxValue : 0;
          const colorClass = getColor(ratio, colorScale);
          return (
            <div
              key={i}
              className={clsx(
                "rounded-sm p-2.5 border transition-all hover:scale-105 cursor-default",
                colorClass
              )}
            >
              <div className="text-xs text-ink-2 truncate">{cell.label}</div>
              <div className="text-sm font-mono font-bold text-ink mt-0.5">
                {cell.value >= 1000 ? `${(cell.value / 1000).toFixed(1)}K` : cell.value.toFixed(0)}
              </div>
              {cell.sublabel && (
                <div className="text-[10px] text-ink-3 mt-0.5">{cell.sublabel}</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
