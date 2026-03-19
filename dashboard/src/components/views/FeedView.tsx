import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { AuditEvent } from "../../types";

interface FeedViewProps {
  events: AuditEvent[];
  connected: boolean;
}

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString("en-US", {
    hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

function actionBadge(event: AuditEvent) {
  const action = event.action || (event.verdict?.allowed ? "ALLOW" : "DENY");
  const styles: Record<string, string> = {
    ALLOW: "bg-sardis-green-glow text-sardis-green border-sardis-green/20",
    FLAG: "bg-sardis-amber-glow text-sardis-amber border-sardis-amber/20",
    HOLD: "bg-sardis-amber-glow text-sardis-amber border-sardis-amber/20",
    DENY: "bg-sardis-red-glow text-sardis-red border-sardis-red/20",
    FREEZE_CHILD: "bg-sardis-red-glow text-sardis-red border-sardis-red/20",
    FREEZE_TREE: "bg-sardis-red-glow text-sardis-red border-sardis-red/20",
  };
  return (
    <Badge variant="outline" className={`text-[9px] font-mono font-bold px-1.5 py-0 ${styles[action] || styles.DENY}`}>
      {action === "FREEZE_CHILD" ? "FREEZE" : action === "FREEZE_TREE" ? "FREEZE" : action}
    </Badge>
  );
}

export function FeedView({ events, connected }: FeedViewProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="h-full flex flex-col p-5 gap-4 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-sardis-text tracking-tight">Live Feed</h1>
          <p className="text-xs text-sardis-text-muted">Real-time policy evaluations via SSE</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-sardis-text-muted">{events.length} events</span>
          <Badge variant="outline" className={`text-[10px] font-mono ${connected ? "border-sardis-green/30 text-sardis-green" : "border-sardis-red/30 text-sardis-red"}`}>
            <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${connected ? "bg-sardis-green pulse-dot" : "bg-sardis-red"}`} />
            {connected ? "STREAMING" : "DISCONNECTED"}
          </Badge>
        </div>
      </div>

      {/* Event list */}
      <Card className="bg-sardis-surface border-border flex-1 min-h-0">
        <ScrollArea className="h-full">
          {events.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-sardis-text-muted">
              <p className="text-sm">Waiting for events...</p>
              <p className="text-xs mt-1">Events appear here when agents make policy evaluations</p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {events.map((event, i) => {
                const key = `${event.timestamp}-${i}`;
                const isExpanded = expandedId === key;
                const failedChecks = event.verdict?.checks?.filter((c) => c.result === "FAIL") || [];
                const riskScore = event.risk_assessment?.final_score;

                return (
                  <div
                    key={key}
                    className={`px-5 py-3 cursor-pointer transition-colors slide-in ${
                      isExpanded ? "bg-sardis-surface-2" : "hover:bg-sardis-surface-2/40"
                    }`}
                    onClick={() => setExpandedId(isExpanded ? null : key)}
                  >
                    {/* Main row */}
                    <div className="flex items-center gap-4">
                      <span className="text-[10px] font-mono text-sardis-text-muted w-16 shrink-0">
                        {formatTime(event.timestamp)}
                      </span>
                      <span className="text-[11px] font-mono text-sardis-cyan w-32 truncate shrink-0">
                        {event.agent || event.agent_id || "anonymous"}
                      </span>
                      <span className="text-[11px] text-sardis-text-secondary flex-1 truncate">
                        {event.merchant}
                      </span>
                      <span className="text-[11px] font-mono font-semibold text-sardis-text w-16 text-right shrink-0">
                        ${event.amount}
                      </span>
                      <span className="text-[10px] font-mono text-sardis-text-muted w-12 shrink-0">
                        {event.currency}
                      </span>
                      {riskScore !== undefined && (
                        <span className={`text-[10px] font-mono w-10 text-right shrink-0 ${
                          riskScore < 0.45 ? "text-sardis-green" : riskScore < 0.70 ? "text-sardis-amber" : "text-sardis-red"
                        }`}>
                          {riskScore.toFixed(2)}
                        </span>
                      )}
                      <span className="w-14 shrink-0 flex justify-end">
                        {actionBadge(event)}
                      </span>
                      <span className="text-[10px] font-mono text-sardis-text-muted w-14 text-right shrink-0">
                        {event.verdict?.total_latency_ms?.toFixed(1) ?? "—"}ms
                      </span>
                    </div>

                    {/* Failed checks summary (always shown for denied) */}
                    {failedChecks.length > 0 && !isExpanded && (
                      <div className="mt-1 ml-16 text-[10px] font-mono text-sardis-red/70 truncate">
                        {failedChecks.map((c) => c.name).join(", ")}
                      </div>
                    )}

                    {/* Expanded detail */}
                    {isExpanded && event.verdict?.checks && (
                      <div className="mt-3 ml-16 border-t border-border pt-3">
                        <div className="grid grid-cols-3 gap-x-6 gap-y-1">
                          {event.verdict.checks.map((check) => (
                            <div key={check.name} className="flex items-center gap-2">
                              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                                check.result === "PASS" ? "bg-sardis-green" : "bg-sardis-red"
                              }`} />
                              <span className="text-[10px] font-mono text-sardis-text-muted truncate">
                                {check.name}
                              </span>
                            </div>
                          ))}
                        </div>
                        {event.risk_assessment && (
                          <div className="mt-2 pt-2 border-t border-border flex items-center gap-4 text-[10px] font-mono text-sardis-text-muted">
                            <span>ML: {event.risk_assessment.ml_score.toFixed(3)}</span>
                            <span>Seq: {event.risk_assessment.sequence_score.toFixed(3)}</span>
                            <span>Corr: {event.risk_assessment.correlation_score.toFixed(3)}</span>
                            <span>Sanctions: {event.risk_assessment.sanctions_score.toFixed(3)}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </ScrollArea>
      </Card>
    </div>
  );
}
