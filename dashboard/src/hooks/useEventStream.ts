import { useEffect, useRef, useState, useCallback } from "react";
import type { AuditEvent, RiskDataPoint, DashboardStats, Action } from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "https://sardis-guard-482463483786.us-central1.run.app";
const MAX_EVENTS = 200;
const MAX_RISK_POINTS = 100;

function resolveAction(event: AuditEvent): Action {
  // V2 events carry action directly from the intelligence plane
  if (event.action) return event.action;

  // V2 risk_assessment also carries an action
  if (event.risk_assessment?.action) return event.risk_assessment.action;

  // V2 governance_result carries an action
  if (event.governance_result?.action) return event.governance_result.action as Action;

  // Legacy fallback: derive from verdict boolean
  if (!event.verdict?.allowed) return "DENY";
  return "ALLOW";
}

function computeRiskScore(event: AuditEvent): number {
  // V2 events carry real risk scores from the intelligence plane
  if (event.risk_assessment?.final_score !== undefined) {
    return event.risk_assessment.final_score;
  }

  // Legacy fallback: simple pass/fail signal (no fabricated heuristics)
  if (!event.verdict?.allowed) return 0.75;
  return 0.10;
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

export function useEventStream() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [riskData, setRiskData] = useState<RiskDataPoint[]>([]);
  const [stats, setStats] = useState<DashboardStats>({
    totalEvents: 0,
    activeMandates: 0,
    frozenMandates: 0,
    avgRiskScore: 0,
    actions: { ALLOW: 0, FLAG: 0, HOLD: 0, FREEZE: 0, DENY: 0 },
    agentsTracked: 0,
    totalVolume: 0,
    uniqueMerchants: 0,
  });
  const [connected, setConnected] = useState(false);

  const eventSourceRef = useRef<EventSource | null>(null);
  const riskScoresRef = useRef<number[]>([]);

  const processEvent = useCallback((event: AuditEvent) => {
    const action = resolveAction(event);
    const riskScore = computeRiskScore(event);

    setEvents((prev) => [event, ...prev].slice(0, MAX_EVENTS));

    const riskPoint: RiskDataPoint = {
      time: event.timestamp,
      timeLabel: formatTime(event.timestamp),
      score: riskScore,
      action,
      agent: event.agent || event.agent_id || "unknown",
    };
    setRiskData((prev) => [...prev, riskPoint].slice(-MAX_RISK_POINTS));

    riskScoresRef.current.push(riskScore);
    if (riskScoresRef.current.length > 200) {
      riskScoresRef.current = riskScoresRef.current.slice(-200);
    }

    setStats((prev) => {
      const newActions = { ...prev.actions };
      if (action === "ALLOW") newActions.ALLOW++;
      else if (action === "FLAG") newActions.FLAG++;
      else if (action === "HOLD") newActions.HOLD++;
      else if (action === "FREEZE_CHILD" || action === "FREEZE_TREE") newActions.FREEZE++;
      else if (action === "DENY") newActions.DENY++;

      const allScores = riskScoresRef.current;
      const avgRisk = allScores.length > 0
        ? allScores.reduce((a, b) => a + b, 0) / allScores.length
        : 0;

      return {
        ...prev,
        totalEvents: prev.totalEvents + 1,
        avgRiskScore: avgRisk,
        actions: newActions,
        totalVolume: prev.totalVolume + (parseFloat(event.amount) || 0),
      };
    });
  }, []);

  // Connect to SSE stream
  useEffect(() => {
    const connect = () => {
      const es = new EventSource(`${API_BASE}/stream`);
      eventSourceRef.current = es;

      es.addEventListener("connected", () => setConnected(true));

      es.addEventListener("evaluation", (e) => {
        try {
          const data = JSON.parse(e.data) as AuditEvent;
          processEvent(data);
        } catch { /* malformed */ }
      });

      es.onerror = () => {
        setConnected(false);
        es.close();
        setTimeout(connect, 3000);
      };

      es.onopen = () => setConnected(true);
    };

    connect();
    return () => { eventSourceRef.current?.close(); };
  }, [processEvent]);

  return { events, riskData, stats, connected };
}
