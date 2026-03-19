import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import type { AuditEvent } from "../../types";

interface AuditViewProps {
  events: AuditEvent[];
}

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString("en-US", {
    hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

function actionLabel(event: AuditEvent): string {
  if (event.action) return event.action;
  return event.verdict?.allowed ? "ALLOW" : "DENY";
}

function actionStyle(event: AuditEvent): string {
  const action = actionLabel(event);
  if (action === "ALLOW") return "border-sardis-green/30 text-sardis-green";
  if (action === "FLAG") return "border-sardis-amber/30 text-sardis-amber";
  if (action === "HOLD") return "border-sardis-amber/30 text-sardis-amber";
  return "border-sardis-red/30 text-sardis-red";
}

export function AuditView({ events }: AuditViewProps) {
  const [filter, setFilter] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filteredEvents = filter
    ? events.filter((e) => {
        const q = filter.toLowerCase();
        return (
          (e.agent || e.agent_id || "").toLowerCase().includes(q) ||
          e.merchant.toLowerCase().includes(q) ||
          actionLabel(e).toLowerCase().includes(q)
        );
      })
    : events;

  const allowCount = events.filter((e) => actionLabel(e) === "ALLOW").length;
  const denyCount = events.filter((e) => ["DENY", "FREEZE_CHILD", "FREEZE_TREE"].includes(actionLabel(e))).length;

  // Check hash chain validity
  const hashEvents = events.filter((e) => e.entry_hash);
  const chainValid = hashEvents.length === 0 || hashEvents.every((e, i) => {
    if (i === 0) return true;
    return e.prev_hash === hashEvents[i - 1].entry_hash;
  });

  return (
    <div className="h-full flex flex-col p-5 gap-4 fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-sardis-text tracking-tight">Audit Trail</h1>
          <p className="text-xs text-sardis-text-muted">Hash-chained event log with evidence-grade integrity</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="text-[10px] font-mono border-sardis-green/30 text-sardis-green">
            {allowCount} allowed
          </Badge>
          <Badge variant="outline" className="text-[10px] font-mono border-sardis-red/30 text-sardis-red">
            {denyCount} denied
          </Badge>
          {hashEvents.length > 0 && (
            <Badge
              variant="outline"
              className={`text-[10px] font-mono ${
                chainValid
                  ? "border-sardis-green/30 text-sardis-green"
                  : "border-sardis-red/30 text-sardis-red"
              }`}
            >
              chain {chainValid ? "valid" : "broken"}
            </Badge>
          )}
        </div>
      </div>

      {/* Search */}
      <Input
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder="Filter by agent, merchant, or action..."
        className="font-mono text-sm bg-sardis-surface border-border max-w-md"
      />

      {/* Event table */}
      <Card className="bg-sardis-surface border-border flex-1 min-h-0">
        {/* Table header */}
        <div className="flex items-center gap-4 px-5 py-2.5 border-b border-border text-[10px] font-mono text-sardis-text-muted uppercase tracking-wider">
          <span className="w-16">Time</span>
          <span className="w-32">Agent</span>
          <span className="flex-1">Merchant</span>
          <span className="w-16 text-right">Amount</span>
          <span className="w-12">Chain</span>
          <span className="w-14 text-right">Latency</span>
          <span className="w-14 text-right">Action</span>
        </div>

        <ScrollArea className="h-[calc(100%-40px)]">
          {filteredEvents.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-sardis-text-muted text-xs">
              {events.length === 0 ? "No events recorded yet" : "No events match filter"}
            </div>
          ) : (
            <div className="divide-y divide-border">
              {filteredEvents.map((event, i) => {
                const key = `${event.timestamp}-${i}`;
                const isExpanded = expandedId === key;

                return (
                  <div key={key}>
                    <div
                      className={`flex items-center gap-4 px-5 py-2.5 cursor-pointer transition-colors ${
                        isExpanded ? "bg-sardis-surface-2" : "hover:bg-sardis-surface-2/30"
                      }`}
                      onClick={() => setExpandedId(isExpanded ? null : key)}
                    >
                      <span className="text-[10px] font-mono text-sardis-text-muted w-16">
                        {formatTime(event.timestamp)}
                      </span>
                      <span className="text-[11px] font-mono text-sardis-cyan w-32 truncate">
                        {event.agent || event.agent_id || "anon"}
                      </span>
                      <span className="text-[11px] text-sardis-text-secondary flex-1 truncate">
                        {event.merchant}
                      </span>
                      <span className="text-[11px] font-mono font-semibold text-sardis-text w-16 text-right">
                        ${event.amount}
                      </span>
                      <span className="text-[10px] font-mono text-sardis-text-muted w-12">
                        {event.network}
                      </span>
                      <span className="text-[10px] font-mono text-sardis-text-muted w-14 text-right">
                        {event.verdict?.total_latency_ms?.toFixed(1) ?? "—"}ms
                      </span>
                      <span className="w-14 flex justify-end">
                        <Badge variant="outline" className={`text-[9px] font-mono font-bold px-1.5 py-0 ${actionStyle(event)}`}>
                          {actionLabel(event)}
                        </Badge>
                      </span>
                    </div>

                    {/* Expanded details */}
                    {isExpanded && (
                      <div className="bg-sardis-surface-2 px-5 py-4 border-t border-border">
                        {/* Check results */}
                        {event.verdict?.checks && (
                          <div className="mb-3">
                            <p className="text-[10px] font-medium text-sardis-text-muted uppercase tracking-wider mb-2">
                              Security Gate Results
                            </p>
                            <div className="grid grid-cols-4 gap-1.5">
                              {event.verdict.checks.map((check) => (
                                <div key={check.name} className="flex items-center gap-1.5">
                                  <span className={`w-1.5 h-1.5 rounded-full ${
                                    check.result === "PASS" ? "bg-sardis-green" : "bg-sardis-red"
                                  }`} />
                                  <span className="text-[10px] font-mono text-sardis-text-muted">
                                    {check.name}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Risk assessment */}
                        {event.risk_assessment && (
                          <>
                            <Separator className="bg-border my-3" />
                            <div>
                              <p className="text-[10px] font-medium text-sardis-text-muted uppercase tracking-wider mb-2">
                                Risk Assessment
                              </p>
                              <div className="flex items-center gap-6 text-[10px] font-mono text-sardis-text-muted">
                                <span>Final: <strong className={event.risk_assessment.final_score < 0.45 ? "text-sardis-green" : event.risk_assessment.final_score < 0.70 ? "text-sardis-amber" : "text-sardis-red"}>{event.risk_assessment.final_score.toFixed(4)}</strong></span>
                                <span>ML: {event.risk_assessment.ml_score.toFixed(3)}</span>
                                <span>Seq: {event.risk_assessment.sequence_score.toFixed(3)}</span>
                                <span>Corr: {event.risk_assessment.correlation_score.toFixed(3)}</span>
                                <span>Sanctions: {event.risk_assessment.sanctions_score.toFixed(3)}</span>
                              </div>
                            </div>
                          </>
                        )}

                        {/* Hash chain */}
                        {event.entry_hash && (
                          <>
                            <Separator className="bg-border my-3" />
                            <div className="flex items-center gap-4 text-[10px] font-mono text-sardis-text-muted">
                              <span>Hash: <span className="text-sardis-text-secondary">{event.entry_hash?.slice(0, 16)}...</span></span>
                              {event.prev_hash && (
                                <span>Prev: <span className="text-sardis-text-secondary">{event.prev_hash?.slice(0, 16)}...</span></span>
                              )}
                            </div>
                          </>
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
