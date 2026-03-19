import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { KillSwitchState } from "../../types";

interface KillSwitchViewProps {
  killSwitches: KillSwitchState[];
  onActivate: (body: {
    scope: string;
    target: string;
    reason: string;
    duration_seconds?: number;
    activated_by?: string;
  }) => Promise<unknown>;
  onDeactivate: (scope: string, target: string) => Promise<unknown>;
}

function formatTimestamp(ts: number): string {
  if (!ts) return "N/A";
  return new Date(ts * 1000).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function scopeColor(scope: string): string {
  switch (scope) {
    case "global":
      return "border-sardis-red/30 text-sardis-red bg-sardis-red-glow";
    case "org":
      return "border-sardis-amber/30 text-sardis-amber bg-sardis-amber-glow";
    case "agent":
      return "border-sardis-cyan text-sardis-cyan bg-sardis-cyan-dim/20";
    case "chain":
      return "border-sardis-text-muted text-sardis-text-secondary bg-sardis-surface-3";
    default:
      return "border-border text-sardis-text-muted";
  }
}

export function KillSwitchView({ killSwitches, onActivate, onDeactivate }: KillSwitchViewProps) {
  const [scope, setScope] = useState("global");
  const [target, setTarget] = useState("*");
  const [reason, setReason] = useState("");
  const [duration, setDuration] = useState("");
  const [activatedBy, setActivatedBy] = useState("dashboard-operator");

  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const showFeedback = (type: "success" | "error", message: string) => {
    setFeedback({ type, message });
    setTimeout(() => setFeedback(null), 4000);
  };

  const handleActivate = async () => {
    if (!reason.trim()) return;
    setLoading(true);
    setFeedback(null);
    try {
      const body: {
        scope: string;
        target: string;
        reason: string;
        duration_seconds?: number;
        activated_by?: string;
      } = {
        scope,
        target: target || "*",
        reason: reason.trim(),
        activated_by: activatedBy || "dashboard",
      };
      if (duration.trim()) {
        body.duration_seconds = parseInt(duration);
      }
      await onActivate(body);
      showFeedback("success", `Kill switch activated: ${scope}/${target}`);
      setReason("");
      setDuration("");
    } catch (e) {
      showFeedback("error", e instanceof Error ? e.message : "Failed to activate kill switch");
    }
    setLoading(false);
  };

  const handleDeactivate = async (sw: KillSwitchState) => {
    setLoading(true);
    setFeedback(null);
    try {
      await onDeactivate(sw.scope, sw.target);
      showFeedback("success", `Kill switch deactivated: ${sw.scope}/${sw.target}`);
    } catch (e) {
      showFeedback("error", e instanceof Error ? e.message : "Failed to deactivate kill switch");
    }
    setLoading(false);
  };

  return (
    <div className="h-full flex flex-col p-5 gap-4 fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-sardis-text tracking-tight">Kill Switch</h1>
          <p className="text-xs text-sardis-text-muted">Emergency circuit breaker for agent payments</p>
        </div>
        <div className="flex items-center gap-2">
          {killSwitches.length > 0 ? (
            <Badge variant="destructive" className="text-[10px] font-mono">
              {killSwitches.length} ACTIVE
            </Badge>
          ) : (
            <Badge variant="outline" className="text-[10px] font-mono border-sardis-green/30 text-sardis-green">
              ALL CLEAR
            </Badge>
          )}
        </div>
      </div>

      {/* Feedback banner */}
      {feedback && (
        <div
          className={`rounded-lg border px-4 py-2.5 text-[11px] font-mono flex items-center justify-between slide-in ${
            feedback.type === "success"
              ? "border-sardis-green/30 bg-sardis-green-glow text-sardis-green"
              : "border-sardis-red/30 bg-sardis-red-glow text-sardis-red"
          }`}
        >
          <span>{feedback.message}</span>
          <button onClick={() => setFeedback(null)} className="opacity-60 hover:opacity-100 ml-3">
            dismiss
          </button>
        </div>
      )}

      <div className="flex-1 grid grid-cols-2 gap-4 min-h-0">
        {/* Left: Activate form */}
        <div className="flex flex-col gap-4 min-h-0">
          <Card className="bg-sardis-surface border-border">
            <CardHeader className="py-3 px-4 border-b border-border">
              <CardTitle className="text-xs font-medium text-sardis-text-secondary">Activate Kill Switch</CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-[11px] text-sardis-text-muted">Scope</Label>
                  <Select value={scope} onValueChange={(v) => {
                    setScope(v);
                    if (v === "global") setTarget("*");
                    else setTarget("");
                  }}>
                    <SelectTrigger className="font-mono text-sm bg-sardis-surface-2 border-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="global">Global</SelectItem>
                      <SelectItem value="org">Organization</SelectItem>
                      <SelectItem value="agent">Agent</SelectItem>
                      <SelectItem value="chain">Chain</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[11px] text-sardis-text-muted">Target</Label>
                  <Input
                    value={target}
                    onChange={(e) => setTarget(e.target.value)}
                    placeholder={scope === "global" ? "*" : scope === "agent" ? "agent-id" : scope === "chain" ? "base" : "org-id"}
                    className="font-mono text-sm bg-sardis-surface-2 border-border"
                    disabled={scope === "global"}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-[11px] text-sardis-text-muted">Reason</Label>
                <Input
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Suspicious activity detected"
                  className="font-mono text-sm bg-sardis-surface-2 border-border"
                  onKeyDown={(e) => e.key === "Enter" && handleActivate()}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-[11px] text-sardis-text-muted">Duration (seconds, optional)</Label>
                  <Input
                    value={duration}
                    onChange={(e) => setDuration(e.target.value)}
                    placeholder="3600 (1 hour)"
                    className="font-mono text-sm bg-sardis-surface-2 border-border"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[11px] text-sardis-text-muted">Activated By</Label>
                  <Input
                    value={activatedBy}
                    onChange={(e) => setActivatedBy(e.target.value)}
                    placeholder="dashboard-operator"
                    className="font-mono text-sm bg-sardis-surface-2 border-border"
                  />
                </div>
              </div>

              <Button
                onClick={handleActivate}
                disabled={loading || !reason.trim()}
                variant="outline"
                className="w-full font-mono text-sm border-sardis-red/30 text-sardis-red hover:bg-sardis-red-glow"
              >
                {loading ? "Activating..." : "Activate Kill Switch"}
              </Button>
            </CardContent>
          </Card>

          {/* Scope explanation */}
          <Card className="bg-sardis-surface border-border">
            <CardHeader className="py-3 px-4 border-b border-border">
              <CardTitle className="text-xs font-medium text-sardis-text-secondary">Scope Reference</CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-2.5">
              <ScopeRow scope="global" description="Halts ALL agent payments across the entire system" />
              <ScopeRow scope="org" description="Halts all payments for a specific organization" />
              <ScopeRow scope="agent" description="Halts payments for a single agent" />
              <ScopeRow scope="chain" description="Halts payments on a specific blockchain" />
            </CardContent>
          </Card>
        </div>

        {/* Right: Active kill switches */}
        <Card className="bg-sardis-surface border-border min-h-0">
          <CardHeader className="py-3 px-4 border-b border-border">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-medium text-sardis-text-secondary">Active Kill Switches</CardTitle>
              <span className="text-[10px] font-mono text-sardis-text-muted">{killSwitches.length} active</span>
            </div>
          </CardHeader>
          <CardContent className="p-0 overflow-y-auto h-[calc(100%-44px)]">
            {killSwitches.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 text-sardis-text-muted">
                <p className="text-xs">No active kill switches</p>
                <p className="text-[10px] text-sardis-text-faint mt-1">All agent payments are operational</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {killSwitches.map((sw, i) => (
                  <div key={`${sw.scope}-${sw.target}-${i}`} className="px-4 py-4 hover:bg-sardis-surface-2/40 transition-colors">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className={`text-[9px] font-mono font-bold px-1.5 py-0 uppercase ${scopeColor(sw.scope)}`}
                        >
                          {sw.scope}
                        </Badge>
                        <span className="text-[11px] font-mono text-sardis-text-secondary">
                          {sw.target}
                        </span>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-[9px] font-mono h-6 px-2 border-sardis-green/30 text-sardis-green hover:bg-sardis-green-glow"
                        onClick={() => handleDeactivate(sw)}
                        disabled={loading}
                      >
                        Deactivate
                      </Button>
                    </div>
                    <p className="text-[11px] text-sardis-text-muted mb-2">{sw.reason}</p>
                    <div className="flex items-center gap-4 text-[10px] font-mono text-sardis-text-muted">
                      <span>Activated: {formatTimestamp(sw.activated_at)}</span>
                      {sw.auto_lift_at && (
                        <span>Auto-lift: {formatTimestamp(sw.auto_lift_at)}</span>
                      )}
                    </div>
                    {sw.activated_by && (
                      <div className="mt-1 text-[10px] font-mono text-sardis-text-faint">
                        by {sw.activated_by}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function ScopeRow({ scope, description }: { scope: string; description: string }) {
  return (
    <div className="flex items-start gap-3">
      <Badge
        variant="outline"
        className={`text-[9px] font-mono font-bold px-1.5 py-0 uppercase shrink-0 mt-0.5 ${scopeColor(scope)}`}
      >
        {scope}
      </Badge>
      <span className="text-[10px] text-sardis-text-muted">{description}</span>
    </div>
  );
}
