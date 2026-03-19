import { useEffect, useRef, useState, useCallback } from "react";
import type { AuditEvent, RiskDataPoint, DashboardStats, Action } from "../types";

const API_BASE = "http://localhost:8402";
const MAX_EVENTS = 50;
const MAX_RISK_POINTS = 100;

function resolveAction(verdict: AuditEvent["verdict"]): Action {
  if (!verdict.allowed) {
    // Determine severity from failed checks
    const failedChecks = verdict.checks.filter((c) => c.result === "FAIL");
    if (failedChecks.length >= 4) return "FREEZE_TREE";
    if (failedChecks.length >= 2) return "FREEZE_CHILD";
    if (failedChecks.some((c) => c.name === "daily_limit")) return "HOLD";
    return "DENY";
  }
  // For allowed, compute a pseudo-risk score from latency & check margins
  const latency = verdict.total_latency_ms;
  if (latency > 50) return "FLAG";
  return "ALLOW";
}

function computeRiskScore(event: AuditEvent): number {
  if (!event.verdict.allowed) {
    const failedCount = event.verdict.checks.filter(
      (c) => c.result === "FAIL"
    ).length;
    const total = event.verdict.checks.length;
    // Failed checks produce higher risk scores
    return Math.min(0.4 + (failedCount / total) * 0.6, 1.0);
  }
  // Allowed - base risk on latency and amount
  const amount = parseFloat(event.amount) || 0;
  const baseRisk = Math.min(amount / 10, 0.3);
  return Math.max(0.05, baseRisk + Math.random() * 0.15);
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
  });
  const [connected, setConnected] = useState(false);
  const [alerts, setAlerts] = useState<
    { id: string; agent: string; reason: string; timestamp: number }[]
  >([]);

  const eventSourceRef = useRef<EventSource | null>(null);
  const riskScoresRef = useRef<number[]>([]);

  // Dismiss an alert
  const dismissAlert = useCallback((id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  }, []);

  // Process incoming event
  const processEvent = useCallback((event: AuditEvent) => {
    const action = resolveAction(event.verdict);
    const riskScore = computeRiskScore(event);

    // Add to events (newest first, cap at MAX)
    setEvents((prev) => [event, ...prev].slice(0, MAX_EVENTS));

    // Add risk data point
    const riskPoint: RiskDataPoint = {
      time: event.timestamp,
      timeLabel: formatTime(event.timestamp),
      score: riskScore,
      action,
      agent: event.agent,
    };
    setRiskData((prev) => [...prev, riskPoint].slice(-MAX_RISK_POINTS));

    // Update risk scores tracking
    riskScoresRef.current.push(riskScore);
    if (riskScoresRef.current.length > 200) {
      riskScoresRef.current = riskScoresRef.current.slice(-200);
    }

    // Update stats
    setStats((prev) => {
      const newActions = { ...prev.actions };
      if (action === "ALLOW") newActions.ALLOW++;
      else if (action === "FLAG") newActions.FLAG++;
      else if (action === "HOLD") newActions.HOLD++;
      else if (action === "FREEZE_CHILD" || action === "FREEZE_TREE")
        newActions.FREEZE++;
      else if (action === "DENY") newActions.DENY++;

      const allScores = riskScoresRef.current;
      const avgRisk =
        allScores.length > 0
          ? allScores.reduce((a, b) => a + b, 0) / allScores.length
          : 0;

      return {
        ...prev,
        totalEvents: prev.totalEvents + 1,
        avgRiskScore: avgRisk,
        actions: newActions,
      };
    });

    // Generate alert for FREEZE events
    if (action === "FREEZE_CHILD" || action === "FREEZE_TREE" || action === "DENY") {
      const failedChecks = event.verdict.checks
        .filter((c) => c.result === "FAIL")
        .map((c) => c.name);
      setAlerts((prev) => [
        {
          id: `${event.timestamp}-${event.agent}`,
          agent: event.agent,
          reason: `${action}: ${failedChecks.join(", ")} (${event.verdict.summary})`,
          timestamp: event.timestamp,
        },
        ...prev,
      ].slice(0, 5));
    }
  }, []);

  // Fetch health data periodically
  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`);
        if (res.ok) {
          const data = await res.json();
          setStats((prev) => ({
            ...prev,
            agentsTracked: data.agents_tracked || 0,
            activeMandates: data.mandates_active || 0,
          }));
        }
      } catch {
        // Silently ignore - server might not be running
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  // Connect to SSE stream
  useEffect(() => {
    const connect = () => {
      const es = new EventSource(`${API_BASE}/stream`);
      eventSourceRef.current = es;

      es.addEventListener("connected", () => {
        setConnected(true);
      });

      es.addEventListener("evaluation", (e) => {
        try {
          const data = JSON.parse(e.data) as AuditEvent;
          processEvent(data);
        } catch {
          // Ignore malformed events
        }
      });

      es.onerror = () => {
        setConnected(false);
        es.close();
        // Reconnect after 3s
        setTimeout(connect, 3000);
      };

      es.onopen = () => {
        setConnected(true);
      };
    };

    connect();

    return () => {
      eventSourceRef.current?.close();
    };
  }, [processEvent]);

  return { events, riskData, stats, connected, alerts, dismissAlert };
}
