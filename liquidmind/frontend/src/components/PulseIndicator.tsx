import clsx from "clsx";

interface PulseIndicatorProps {
  status: "ok" | "warning" | "critical";
  size?: "sm" | "md" | "lg";
  label?: string;
}

export default function PulseIndicator({ status, size = "md", label }: PulseIndicatorProps) {
  const sizeClasses = {
    sm: "w-2 h-2",
    md: "w-3 h-3",
    lg: "w-4 h-4",
  };

  const colorClasses = {
    ok: "bg-accent-green",
    warning: "bg-yellow-500",
    critical: "bg-accent-red",
  };

  const pulseClasses = {
    ok: "bg-accent-green",
    warning: "bg-yellow-400",
    critical: "bg-accent-red",
  };

  return (
    <div className="flex items-center gap-2">
      <span className="relative flex">
        <span
          className={clsx(
            "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
            pulseClasses[status],
            sizeClasses[size]
          )}
        />
        <span
          className={clsx(
            "relative inline-flex rounded-full",
            colorClasses[status],
            sizeClasses[size]
          )}
        />
      </span>
      {label && <span className="text-xs text-ink-3">{label}</span>}
    </div>
  );
}
