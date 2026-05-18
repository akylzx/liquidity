import { Routes, Route, NavLink } from "react-router-dom";
import CommandCenter from "./pages/CommandCenter";
import Forecasts from "./pages/Forecasts";
import Rebalancing from "./pages/Rebalancing";
import RiskStress from "./pages/RiskStress";
import clsx from "clsx";

const navItems = [
  { path: "/", label: "Command Center" },
  { path: "/forecasts", label: "Forecasts" },
  { path: "/rebalancing", label: "Rebalancing" },
  { path: "/risk", label: "Risk & Stress" },
];

export default function App() {
  const today = new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="min-h-screen bg-bg flex flex-col">
      {/* Header */}
      <header className="flex-shrink-0 h-14 flex items-center px-6 gap-1.5">
        <div className="w-[34px] h-[34px] bg-ink rounded-[10px] flex items-center justify-center text-lime font-bold text-base mr-1 flex-shrink-0">
          ◈
        </div>
        <span className="text-sm font-semibold text-ink tracking-tight mr-5">
          LiquidMind
        </span>

        <nav className="flex gap-1.5">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                clsx(
                  "h-[34px] px-4 rounded-pill flex items-center text-xs font-medium cursor-pointer whitespace-nowrap transition-all",
                  isActive
                    ? "bg-ink text-lime"
                    : "text-ink-3 hover:bg-black/5 hover:text-ink"
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2.5">
          <div className="h-[34px] px-3.5 rounded-pill bg-surface border border-black/[0.12] flex items-center gap-2 text-xs text-ink-2 shadow-card">
            {today}
          </div>
          <div className="h-[34px] px-3.5 rounded-pill bg-surface border border-black/[0.12] flex items-center gap-[7px] text-xs text-ink-2 shadow-card">
            <span className="w-[7px] h-[7px] rounded-full bg-accent-green animate-blink" />
            Live
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 px-4 pb-4 min-h-0">
        <Routes>
          <Route path="/" element={<CommandCenter />} />
          <Route path="/forecasts" element={<Forecasts />} />
          <Route path="/rebalancing" element={<Rebalancing />} />
          <Route path="/risk" element={<RiskStress />} />
        </Routes>
      </main>
    </div>
  );
}
