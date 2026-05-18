interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  showArea?: boolean;
}

export default function Sparkline({
  data,
  width = 80,
  height = 24,
  color = "#111111",
  showArea = true,
}: SparklineProps) {
  if (data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const padding = 2;

  const points = data.map((val, i) => {
    const x = padding + (i / (data.length - 1)) * (width - padding * 2);
    const y = padding + (1 - (val - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  });

  const pathD = `M ${points.join(" L ")}`;
  const areaD = `${pathD} L ${width - padding},${height - padding} L ${padding},${height - padding} Z`;

  // Determine trend
  const lastVal = data[data.length - 1];
  const firstVal = data[0];
  const trending = lastVal > firstVal ? "up" : lastVal < firstVal ? "down" : "flat";

  return (
    <div className="inline-flex items-center gap-1.5">
      <svg width={width} height={height} className="overflow-visible">
        {showArea && (
          <path d={areaD} fill={color} fillOpacity={0.08} />
        )}
        <path
          d={pathD}
          fill="none"
          stroke={color}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* End dot */}
        <circle
          cx={width - padding}
          cy={padding + (1 - (lastVal - min) / range) * (height - padding * 2)}
          r={2}
          fill={color}
        />
      </svg>
      <span className={`text-xs font-medium ${trending === "up" ? "text-accent-green" : trending === "down" ? "text-accent-red" : "text-ink-3"}`}>
        {trending === "up" ? "+" : ""}{((lastVal - firstVal) / (Math.abs(firstVal) || 1) * 100).toFixed(1)}%
      </span>
    </div>
  );
}
