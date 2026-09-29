import { NavLink, Outlet } from "react-router-dom";
import {
  FileBarChart2,
  GaugeCircle,
  History,
  LayoutDashboard,
  LibraryBig,
  ScanSearch,
} from "lucide-react";
import { cn } from "@/utils/cn";
import { useApi } from "@/hooks/useApi";
import { api } from "@/services/api";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/analyze", label: "Analyze Tender", icon: ScanSearch, end: false },
  { to: "/standards", label: "Standards Explorer", icon: LibraryBig, end: false },
  { to: "/history", label: "Recommendation History", icon: History, end: false },
  { to: "/reports", label: "Reports", icon: FileBarChart2, end: false },
];

function BrandMark() {
  return (
    <span className="flex items-center gap-2.5" aria-hidden="true">
      <span className="flex h-8 w-8 items-center justify-center rounded bg-white/10 ring-1 ring-white/25">
        <GaugeCircle className="h-4.5 w-4.5 text-white" />
      </span>
      <span className="flex flex-col leading-none">
        <span className="text-base font-bold tracking-[0.14em] text-white">SISAP</span>
        <span className="mt-0.5 text-[9px] tracking-[0.1em] text-navy-200 uppercase">
          Standards Advisor
        </span>
      </span>
    </span>
  );
}

export default function AppLayout() {
  const { data: health } = useApi(() => api.health(), []);

  return (
    <div className="flex min-h-screen flex-col bg-ink-50">
      <a href="#main-content" className="skip-link no-print">
        Skip to main content
      </a>

      <header className="no-print sticky top-0 z-30 border-b border-navy-800 bg-navy-900">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between gap-4 px-4 lg:px-6">
          <NavLink to="/" className="flex items-center" aria-label="SISAP home">
            <BrandMark />
          </NavLink>

          <div className="hidden items-center gap-1 lg:flex">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 rounded px-3 py-2 text-[13px] font-medium transition-colors",
                    isActive
                      ? "bg-white/12 text-white"
                      : "text-navy-200 hover:bg-white/8 hover:text-white",
                  )
                }
              >
                <item.icon className="h-4 w-4" aria-hidden="true" />
                {item.label}
              </NavLink>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden rounded border border-white/20 px-2 py-1 text-[10px] font-semibold tracking-wider text-navy-100 uppercase sm:inline">
              {health?.demo_mode ? "Demo mode" : "Live mode"}
            </span>
            <span className="hidden text-[10px] text-navy-300 md:inline">
              {health ? `${health.standards_loaded} standards` : "connecting…"}
            </span>
          </div>
        </div>

        {/* Mobile / tablet navigation */}
        <nav className="flex gap-1 overflow-x-auto border-t border-navy-800 px-2 py-1.5 lg:hidden" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "flex shrink-0 items-center gap-1.5 rounded px-2.5 py-1.5 text-xs font-medium",
                  isActive ? "bg-white/12 text-white" : "text-navy-200",
                )
              }
            >
              <item.icon className="h-3.5 w-3.5" aria-hidden="true" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main id="main-content" className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 lg:px-6">
        <Outlet />
      </main>

      <footer className="no-print border-t border-ink-200 bg-white px-4 py-4 lg:px-6">
        <div className="mx-auto flex max-w-[1400px] flex-col gap-1.5 text-[11px] leading-relaxed text-ink-500 sm:flex-row sm:items-center sm:justify-between">
          <p>
            SISAP - Smart Indian Standards Advisor for Procurement &middot; SIH26108 &middot; Smart Automation
          </p>
          <p className="text-ink-400">
            Curated demo dataset - not verified against the live BIS catalogue. Recommendations require
            review by the responsible procurement/technical authority.
          </p>
        </div>
      </footer>
    </div>
  );
}
