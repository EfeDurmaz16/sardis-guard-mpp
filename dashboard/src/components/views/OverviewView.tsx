import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
} from "recharts";
import type {
  DashboardSummary,
  DashboardStats,
  ServiceInfo,
  KillSwitchState,
  AuditEvent,
  RiskDataPoint,
} from "../../types";

interface OverviewViewProps {
  summary: DashboardSummary | null;
  stats: DashboardStats;
  serviceInfo: ServiceInfo | null;
  killSwitches: KillSwitchState[];
  events: AuditEvent[];
  riskData: RiskDataPoint[];
  connected: boolean;
}

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <Card className="bg-sardis-surface border-border">
      <CardContent className="p-4">
        <p className="text-[11px] font-medium text-sardis-text-muted uppercase tracking-wider mb-2">
          {label}
        </p>
        <p className={`text-2xl font-bold font-mono ${accent ? "text-sardis-amber" : "text-sardis-text"}`}>
          {typeof value === "number" ? value.toLocaleString() : value}
        </p>
        {sub && <p className="text-[11px] text-sardis-text-muted mt-1">{sub}</p>}
      </CardContent>
    </Card>
  );
}

function ActionBar({ label, count, total, color }: { label: string; count: number; total: number; color: string }) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-[11px] font-mono text-sardis-text-muted w-12 text-right">{label}</span>
      <div className="flex-1 h-1.5 bg-sardis-surface-3 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-300 ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] font-mono text-sardis-text-secondary w-8 text-right">{count}</span>
    </div>
  );
}

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function actionColor(event: AuditEvent): string {
  if (event.action === "DENY" || (!event.verdict?.allowed && !event.action)) return "text-sardis-red";
  if (event.action === "FLAG") return "text-sardis-amber";
  if (event.action === "HOLD") return "text-sardis-amber";
  if (event.action === "FREEZE_CHILD" || event.action === "FREEZE_TREE") return "text-sardis-red";
  return "text-sardis-green";
}

function actionLabel(event: AuditEvent): string {
  if (event.action) return event.action;
  return event.verdict?.allowed ? "ALLOW" : "DENY";
}

function RiskTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: RiskDataPoint }> }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="bg-sardis-surface-2 border border-border rounded-md px-3 py-2 shadow-xl">
      <p className="text-[10px] font-mono text-sardis-text-muted">{p.timeLabel}</p>
      <p className="text-xs font-bold font-mono text-sardis-text mt-0.5">
        {p.score.toFixed(4)}
      </p>
      <p className="text-[10px] font-mono text-sardis-cyan">{p.agent}</p>
    </div>
  );
}

export function OverviewView({
  summary,
  stats,
  serviceInfo,
  killSwitches,
  events,
  riskData,
  connected,
}: OverviewViewProps) {
  const totalActions =
    stats.actions.ALLOW + stats.actions.FLAG + stats.actions.HOLD + stats.actions.FREEZE + stats.actions.DENY;

  const eventsToShow = events.slice(0, 8);

  return (
    <div className="h-full flex flex-col gap-4 p-5 overflow-hidden fade-in">
      {/* Top bar */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-sardis-text tracking-tight">
            Sardis Guard
          </h1>
          <p className="text-xs text-sardis-text-muted">
            Intelligence Plane {serviceInfo?.version ? `v${serviceInfo.version}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {killSwitches.length > 0 && (
            <Badge variant="destructive" className="text-[10px] font-mono">
              {killSwitches.length} KILL SWITCH ACTIVE
            </Badge>
          )}
          <Badge
            variant={connected ? "outline" : "destructive"}
            className={`text-[10px] font-mono ${
              connected
                ? "border-sardis-green/30 text-sardis-green"
                : "border-sardis-red/30 text-sardis-red"
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${connected ? "bg-sardis-green pulse-dot" : "bg-sardis-red"}`} />
            {connected ? "LIVE" : "OFFLINE"}
          </Badge>
        </div>
      </div>

      {/* Stat cards row */}
      <div className="grid grid-cols-5 gap-3">
        <StatCard
          label="Events"
          value={summary?.total_events ?? stats.totalEvents}
          sub="Total evaluations"
        />
        <StatCard
          label="Agents"
          value={summary?.active_agents ?? stats.agentsTracked}
          sub="Active agents"
        />
        <StatCard
          label="Volume"
          value={`$${(summary?.total_volume ?? stats.totalVolume).toFixed(2)}`}
          sub="Total spend"
          accent
        />
        <StatCard
          label="Merchants"
          value={summary?.unique_merchants ?? 0}
          sub="Unique services"
        />
        <StatCard
          label="Mandates"
          value={summary?.mandates_total ?? stats.activeMandates}
          sub={`${summary?.mandates_frozen ?? stats.frozenMandates} frozen`}
        />
      </div>

      {/* Main content: 3 columns */}
      <div className="flex-1 grid grid-cols-12 gap-3 min-h-0">
        {/* Left: Recent activity */}
        <div className="col-span-4 min-h-0">
          <Card className="bg-sardis-surface border-border h-full flex flex-col">
            <CardHeader className="py-3 px-4 border-b border-border">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs font-medium text-sardis-text-secondary">
                  Recent Activity
                </CardTitle>
                <span className="text-[10px] font-mono text-sardis-text-muted">
                  {events.length} total
                </span>
              </div>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-0">
              {eventsToShow.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-2 text-sardis-text-muted">
                  <p className="text-xs">No events yet</p>
                  <p className="text-[10px] text-sardis-text-faint">Events appear when agents make evaluations</p>
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {eventsToShow.map((event, i) => (
                    <div key={`${event.timestamp}-${i}`} className="px-4 py-2.5 hover:bg-sardis-surface-2/50 transition-colors slide-in">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-[10px] font-mono text-sardis-text-muted shrink-0">
                            {formatTime(event.timestamp)}
                          </span>
                          <span className="text-[11px] font-mono text-sardis-cyan truncate">
                            {event.agent || event.agent_id || "anon"}
                          </span>
                        </div>
                        <span className={`text-[10px] font-mono font-bold ${actionColor(event)}`}>
                          {actionLabel(event)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between mt-0.5">
                        <span className="text-[10px] text-sardis-text-muted truncate">
                          {event.merchant}
                        </span>
                        <span className="text-[11px] font-mono font-semibold text-sardis-text shrink-0">
                          ${event.amount}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Center: Risk timeline */}
        <div className="col-span-5 min-h-0">
          <Card className="bg-sardis-surface border-border h-full flex flex-col">
            <CardHeader className="py-3 px-4 border-b border-border">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs font-medium text-sardis-text-secondary">
                  Risk Score Timeline
                </CardTitle>
                <div className="flex items-center gap-2 text-[9px] font-mono text-sardis-text-muted">
                  <span className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-sardis-green" /> &lt;0.45
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-sardis-amber" /> &lt;0.70
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-sardis-red" /> &ge;0.85
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex-1 p-3 min-h-0">
              {riskData.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-2 text-sardis-text-muted">
                  <p className="text-xs">No risk data</p>
                  <p className="text-[10px] text-sardis-text-faint">Risk scores populate from SSE events</p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={riskData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                    <ReferenceArea y1={0} y2={0.45} fill="#22c55e" fillOpacity={0.03} />
                    <ReferenceArea y1={0.45} y2={0.70} fill="#f59e0b" fillOpacity={0.03} />
                    <ReferenceArea y1={0.70} y2={1.0} fill="#ef4444" fillOpacity={0.05} />
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f1f28" vertical={false} />
                    <XAxis
                      dataKey="timeLabel"
                      tick={{ fill: "#71717a", fontSize: 9 }}
                      axisLine={{ stroke: "#1f1f28" }}
                      tickLine={false}
                      interval="preserveStartEnd"
                    />
                    <YAxis
                      domain={[0, 1]}
                      ticks={[0, 0.45, 0.70, 1.0]}
                      tick={{ fill: "#71717a", fontSize: 9 }}
                      axisLine={{ stroke: "#1f1f28" }}
                      tickLine={false}
                      width={28}
                    />
                    <Tooltip content={<RiskTooltip />} />
                    <Line
                      type="monotone"
                      dataKey="score"
                      stroke="#71717a"
                      strokeWidth={1.5}
                      dot={(props: Record<string, unknown>) => {
                        const cx = props.cx as number;
                        const cy = props.cy as number;
                        const payload = props.payload as RiskDataPoint;
                        const index = props.index as number;
                        const color = payload.score < 0.45 ? "#22c55e" : payload.score < 0.70 ? "#f59e0b" : "#ef4444";
                        return <circle key={index} cx={cx} cy={cy} r={2.5} fill={color} stroke="none" />;
                      }}
                      activeDot={{ r: 4, stroke: "#f59e0b", strokeWidth: 2, fill: "#09090b" }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Actions + Modules + Risk */}
        <div className="col-span-3 flex flex-col gap-3 min-h-0">
          {/* Action breakdown */}
          <Card className="bg-sardis-surface border-border">
            <CardHeader className="py-3 px-4 border-b border-border">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs font-medium text-sardis-text-secondary">
                  Actions
                </CardTitle>
                <span className="text-[10px] font-mono text-sardis-text-muted">{totalActions} total</span>
              </div>
            </CardHeader>
            <CardContent className="p-4 space-y-2.5">
              <ActionBar label="ALLOW" count={stats.actions.ALLOW} total={totalActions} color="bg-sardis-green" />
              <ActionBar label="FLAG" count={stats.actions.FLAG} total={totalActions} color="bg-sardis-amber" />
              <ActionBar label="HOLD" count={stats.actions.HOLD} total={totalActions} color="bg-sardis-amber" />
              <ActionBar label="FREEZE" count={stats.actions.FREEZE} total={totalActions} color="bg-sardis-red" />
              <ActionBar label="DENY" count={stats.actions.DENY} total={totalActions} color="bg-sardis-red" />
            </CardContent>
          </Card>

          {/* Average risk score — compact inline */}
          <Card className="bg-sardis-surface border-border">
            <CardContent className="px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-[11px] font-medium text-sardis-text-muted uppercase tracking-wider">Avg Risk</span>
                <span className={`text-lg font-bold font-mono ${
                  stats.avgRiskScore < 0.45 ? "text-sardis-green" :
                  stats.avgRiskScore < 0.70 ? "text-sardis-amber" :
                  "text-sardis-red"
                }`}>
                  {stats.totalEvents > 0 ? stats.avgRiskScore.toFixed(3) : "—"}
                </span>
              </div>
              <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                stats.avgRiskScore < 0.45 ? "bg-sardis-green-glow text-sardis-green" :
                stats.avgRiskScore < 0.70 ? "bg-sardis-amber-glow text-sardis-amber" :
                "bg-sardis-red-glow text-sardis-red"
              }`}>
                {stats.totalEvents > 0 ? (stats.avgRiskScore < 0.45 ? "LOW" : stats.avgRiskScore < 0.70 ? "ELEVATED" : "HIGH") : "N/A"}
              </span>
            </CardContent>
          </Card>

          {/* System modules */}
          <Card className="bg-sardis-surface border-border flex-1 min-h-0">
            <CardHeader className="py-3 px-4 border-b border-border">
              <CardTitle className="text-xs font-medium text-sardis-text-secondary">
                System Modules
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-2.5">
              {serviceInfo?.modules ? (
                Object.entries(serviceInfo.modules).map(([name, active]) => (
                  <div key={name} className="flex items-center justify-between">
                    <span className="text-[11px] font-mono text-sardis-text-muted">
                      {name.replace(/_/g, " ")}
                    </span>
                    <span className={`w-2 h-2 rounded-full ${active ? "bg-sardis-green" : "bg-sardis-red"}`} />
                  </div>
                ))
              ) : (
                <p className="text-[11px] text-sardis-text-muted">Connecting...</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
