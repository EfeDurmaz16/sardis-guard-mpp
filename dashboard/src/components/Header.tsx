import type { DashboardStats } from "../types";

interface HeaderProps {
  stats: DashboardStats;
  connected: boolean;
}

export function Header({ stats, connected }: HeaderProps) {
  return (
    <header className="border-b border-sardis-border bg-sardis-surface px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          {/* Shield icon */}
          <div className="w-9 h-9 rounded-lg bg-sardis-blue/20 border border-sardis-blue/30 flex items-center justify-center">
            <svg
              className="w-5 h-5 text-sardis-blue"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white tracking-tight">
              Sardis Guard Intelligence Plane
            </h1>
            <p className="text-xs text-sardis-text-dim">
              MPP Policy Firewall &middot; Real-time Monitoring
            </p>
          </div>
        </div>
        {/* Connection status */}
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
            connected
              ? "bg-sardis-green/15 text-sardis-green border border-sardis-green/30"
              : "bg-sardis-red/15 text-sardis-red border border-sardis-red/30"
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              connected ? "bg-sardis-green pulse-dot" : "bg-sardis-red"
            }`}
          />
          {connected ? "LIVE" : "DISCONNECTED"}
        </div>
      </div>

      <div className="flex items-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-sardis-text-dim">Agents</span>
          <span className="font-mono font-semibold text-white">
            {stats.agentsTracked}
          </span>
        </div>
        <div className="w-px h-5 bg-sardis-border" />
        <div className="flex items-center gap-2">
          <span className="text-sardis-text-dim">Events</span>
          <span className="font-mono font-semibold text-white">
            {stats.totalEvents.toLocaleString()}
          </span>
        </div>
        <div className="w-px h-5 bg-sardis-border" />
        <div className="flex items-center gap-2">
          <span className="text-sardis-text-dim">Mandates</span>
          <span className="font-mono font-semibold text-white">
            {stats.activeMandates}
          </span>
        </div>
      </div>
    </header>
  );
}
