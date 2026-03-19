interface Alert {
  id: string;
  agent: string;
  reason: string;
  timestamp: number;
}

interface AlertBannerProps {
  alerts: Alert[];
  onDismiss: (id: string) => void;
}

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function truncateAgent(s: string, len: number): string {
  if (s.length <= len) return s;
  return s.slice(0, len - 2) + "..";
}

export function AlertBanner({ alerts, onDismiss }: AlertBannerProps) {
  if (alerts.length === 0) return null;

  return (
    <div className="space-y-2">
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className="glow-alert bg-sardis-red/10 border border-sardis-red/40 rounded-xl px-5 py-3 flex items-center justify-between slide-in"
        >
          <div className="flex items-center gap-3 min-w-0">
            {/* Alert icon */}
            <div className="w-8 h-8 rounded-full bg-sardis-red/20 border border-sardis-red/40 flex items-center justify-center shrink-0">
              <svg
                className="w-4 h-4 text-sardis-red"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-sardis-red">
                ALERT: Agent{" "}
                <span className="font-mono text-white">
                  {truncateAgent(alert.agent, 20)}
                </span>{" "}
                flagged
              </p>
              <p className="text-xs text-sardis-red/80 font-mono truncate mt-0.5">
                {alert.reason}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span className="text-[10px] font-mono text-sardis-text-dim">
              {formatTime(alert.timestamp)}
            </span>
            <button
              onClick={() => onDismiss(alert.id)}
              className="w-6 h-6 rounded-md bg-sardis-red/20 hover:bg-sardis-red/40 flex items-center justify-center transition-colors"
            >
              <svg
                className="w-3 h-3 text-sardis-red"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
