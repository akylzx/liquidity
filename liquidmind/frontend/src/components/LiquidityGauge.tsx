interface LiquidityGaugeProps {
  value: number;
  min: number;
  max: number;
  label: string;
  currency?: string;
  size?: number;
}

export default function LiquidityGauge({
  value,
  min,
  max,
  label,
  currency = "USD",
  size = 120,
}: LiquidityGaugeProps) {
  const percentage = Math.min(1, Math.max(0, (value - 0) / (max - 0)));
  const minPercentage = min / max;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * Math.PI; // half circle
  const offset = circumference * (1 - percentage);
  const minOffset = circumference * (1 - minPercentage);

  // Color based on position relative to min
  let color = "#28a828"; // green
  if (value < min) color = "#e03030"; // red
  else if (value < min * 1.2) color = "#eab308"; // yellow

  const formatVal = (v: number) => {
    if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
    if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
    return v.toFixed(0);
  };

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size / 2 + 10} viewBox={`0 0 ${size} ${size / 2 + 10}`}>
        {/* Background arc */}
        <path
          d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none"
          stroke="rgba(0,0,0,0.06)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Min threshold marker */}
        <path
          d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none"
          stroke="rgba(0,0,0,0.12)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${circumference}`}
          strokeDashoffset={minOffset}
          opacity={0.5}
        />
        {/* Value arc */}
        <path
          d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${circumference}`}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.8s ease-out, stroke 0.3s ease" }}
        />
      </svg>
      <div className="text-center -mt-2">
        <div className="text-sm font-bold font-mono text-ink">{currency} {formatVal(value)}</div>
        <div className="text-xs text-ink-3">{label}</div>
      </div>
    </div>
  );
}
