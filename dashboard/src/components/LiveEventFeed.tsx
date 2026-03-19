import type { AuditEvent } from "../types";

interface LiveEventFeedProps {
  events: AuditEvent[];
}

function actionBadge(verdict: AuditEvent["verdict"]) {
  if (verdict.allowed) {
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-sardis-green/15 text-sardis-green border border-sardis-green/30">
        ALLOW
      </span>
    );
  }

  const failedCount = verdict.checks.filter((c) => c.result === "FAIL").length;

  if (failedCount >= 4) {
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-sardis-red/15 text-sardis-red border border-sardis-red/30 glow-alert">
        FREEZE
      </span>
    );
  }
  if (failedCount >= 2) {
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-sardis-orange/15 text-sardis-orange border border-sardis-orange/30">
        HOLD
      </span>
    );
  }
  if (failedCount >= 1) {
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-sardis-yellow/15 text-sardis-yellow border border-sardis-yellow/30">
        DENY
      </span>
    );
  }
  return (
    <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-sardis-yellow/15 text-sardis-yellow border border-sardis-yellow/30">
      FLAG
    </span>
  );
}

function borderColor(verdict: AuditEvent["verdict"]): string {
  if (verdict.allowed) return "border-l-sardis-green";
  const failedCount = verdict.checks.filter((c) => c.result === "FAIL").length;
  if (failedCount >= 4) return "border-l-sardis-red";
  if (failedCount >= 2) return "border-l-sardis-orange";
  return "border-l-sardis-yellow";
}

function formatTimestamp(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function truncate(s: string, len: number): string {
  if (s.length <= len) return s;
  return s.slice(0, len - 2) + "..";
}

export function LiveEventFeed({ events }: LiveEventFeedProps) {
  return (
    <div className="bg-sardis-surface border border-sardis-border rounded-xl flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-sardis-border">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-sardis-green pulse-dot" />
          <h2 className="text-sm font-semibold text-white">
            Live Event Feed
          </h2>
        </div>
        <span className="text-xs font-mono text-sardis-text-dim">
          {events.length} events
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-sardis-text-dim">
            <svg className="w-10 h-10 mb-3 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <p className="text-sm">Waiting for events...</p>
            <p className="text-xs mt-1">Run the demo agent to generate traffic</p>
          </div>
        ) : (
          events.map((event, i) => (
            <div
              key={`${event.timestamp}-${event.agent}-${i}`}
              className={`slide-in border-l-2 ${borderColor(event.verdict)} bg-sardis-surface-2 rounded-r-lg px-3 py-2 hover:bg-sardis-border/30 transition-colors cursor-default`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-[10px] font-mono text-sardis-text-dim shrink-0">
                    {formatTimestamp(event.timestamp)}
                  </span>
                  <span
                    className="text-xs font-mono text-sardis-cyan truncate"
                    title={event.agent}
                  >
                    {truncate(event.agent, 16)}
                  </span>
                </div>
                {actionBadge(event.verdict)}
              </div>
              <div className="flex items-center justify-between mt-1">
                <span
                  className="text-xs text-sardis-text-dim truncate"
                  title={event.merchant}
                >
                  {truncate(event.merchant, 28)}
                </span>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-xs font-mono font-semibold text-white">
                    ${event.amount}
                  </span>
                  <span className="text-[10px] text-sardis-text-dim">
                    {event.currency}
                  </span>
                </div>
              </div>
              {!event.verdict.allowed && (
                <div className="mt-1.5 text-[10px] text-sardis-red/80 font-mono truncate">
                  {event.verdict.checks
                    .filter((c) => c.result === "FAIL")
                    .map((c) => c.name)
                    .join(", ")}
                </div>
              )}
              <div className="mt-1 text-[10px] text-sardis-text-dim font-mono">
                {event.verdict.total_latency_ms.toFixed(1)}ms &middot;{" "}
                {event.verdict.checks.length} checks &middot;{" "}
                {event.network}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
