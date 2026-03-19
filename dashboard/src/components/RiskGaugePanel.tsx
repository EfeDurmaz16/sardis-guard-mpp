import type { DashboardStats } from "../types";

interface RiskGaugePanelProps {
  stats: DashboardStats;
}

function riskColor(score: number): string {
  if (score < 0.45) return "text-sardis-green";
  if (score < 0.70) return "text-sardis-yellow";
  return "text-sardis-red";
}

function riskBg(score: number): string {
  if (score < 0.45) return "bg-sardis-green/15 border-sardis-green/30";
  if (score < 0.70) return "bg-sardis-yellow/15 border-sardis-yellow/30";
  return "bg-sardis-red/15 border-sardis-red/30";
}

function riskLabel(score: number): string {
  if (score < 0.45) return "LOW";
  if (score < 0.70) return "ELEVATED";
  return "HIGH";
}

export function RiskGaugePanel({ stats }: RiskGaugePanelProps) {
  const totalActions =
    stats.actions.ALLOW +
    stats.actions.FLAG +
    stats.actions.HOLD +
    stats.actions.FREEZE +
    stats.actions.DENY;

  return (
    <div className="grid grid-cols-4 gap-4">
      {/* Total Events */}
      <div className="bg-sardis-surface border border-sardis-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sardis-text-dim text-xs font-medium uppercase tracking-wider">
            Total Events
          </span>
          <div className="w-8 h-8 rounded-lg bg-sardis-blue/15 border border-sardis-blue/30 flex items-center justify-center">
            <svg className="w-4 h-4 text-sardis-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
        </div>
        <p className="text-3xl font-bold font-mono text-white">
          {stats.totalEvents.toLocaleString()}
        </p>
        <p className="text-xs text-sardis-text-dim mt-1">
          Policy evaluations processed
        </p>
      </div>

      {/* Active Mandates */}
      <div className="bg-sardis-surface border border-sardis-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sardis-text-dim text-xs font-medium uppercase tracking-wider">
            Active Mandates
          </span>
          <div className="w-8 h-8 rounded-lg bg-sardis-purple/15 border border-sardis-purple/30 flex items-center justify-center">
            <svg className="w-4 h-4 text-sardis-purple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <p className="text-3xl font-bold font-mono text-white">
            {stats.activeMandates}
          </p>
          {stats.frozenMandates > 0 && (
            <span className="text-xs font-mono text-sardis-red bg-sardis-red/15 px-2 py-0.5 rounded-full">
              {stats.frozenMandates} frozen
            </span>
          )}
        </div>
        <p className="text-xs text-sardis-text-dim mt-1">
          Spending mandates enforced
        </p>
      </div>

      {/* Average Risk Score */}
      <div className="bg-sardis-surface border border-sardis-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sardis-text-dim text-xs font-medium uppercase tracking-wider">
            Avg Risk Score
          </span>
          <div
            className={`px-2 py-0.5 rounded-full text-xs font-bold border ${riskBg(stats.avgRiskScore)}`}
          >
            <span className={riskColor(stats.avgRiskScore)}>
              {riskLabel(stats.avgRiskScore)}
            </span>
          </div>
        </div>
        <p className={`text-3xl font-bold font-mono ${riskColor(stats.avgRiskScore)}`}>
          {stats.totalEvents > 0 ? stats.avgRiskScore.toFixed(3) : "---"}
        </p>
        {/* Risk bar */}
        <div className="mt-2 h-1.5 bg-sardis-surface-2 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              stats.avgRiskScore < 0.45
                ? "bg-sardis-green"
                : stats.avgRiskScore < 0.70
                  ? "bg-sardis-yellow"
                  : "bg-sardis-red"
            }`}
            style={{ width: `${Math.min(stats.avgRiskScore * 100, 100)}%` }}
          />
        </div>
      </div>

      {/* Actions Breakdown */}
      <div className="bg-sardis-surface border border-sardis-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sardis-text-dim text-xs font-medium uppercase tracking-wider">
            Actions
          </span>
          <span className="text-xs font-mono text-sardis-text-dim">
            {totalActions} total
          </span>
        </div>
        <div className="space-y-2">
          <ActionBar
            label="ALLOW"
            count={stats.actions.ALLOW}
            total={totalActions}
            color="bg-sardis-green"
          />
          <ActionBar
            label="FLAG"
            count={stats.actions.FLAG}
            total={totalActions}
            color="bg-sardis-yellow"
          />
          <ActionBar
            label="HOLD"
            count={stats.actions.HOLD}
            total={totalActions}
            color="bg-sardis-orange"
          />
          <ActionBar
            label="FREEZE"
            count={stats.actions.FREEZE}
            total={totalActions}
            color="bg-sardis-red"
          />
          <ActionBar
            label="DENY"
            count={stats.actions.DENY}
            total={totalActions}
            color="bg-sardis-red/70"
          />
        </div>
      </div>
    </div>
  );
}

function ActionBar({
  label,
  count,
  total,
  color,
}: {
  label: string;
  count: number;
  total: number;
  color: string;
}) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] font-mono text-sardis-text-dim w-10 text-right">
        {label}
      </span>
      <div className="flex-1 h-1.5 bg-sardis-surface-2 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-300 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] font-mono text-sardis-text-dim w-6 text-right">
        {count}
      </span>
    </div>
  );
}
