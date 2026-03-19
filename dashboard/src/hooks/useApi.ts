import { useEffect, useState, useCallback } from "react";
import type {
  DashboardSummary,
  HealthData,
  ServiceInfo,
  MandateNode,
  KillSwitchState,
  ScreeningResult,
} from "../types";

const API_BASE = "http://localhost:8402";

export function useApi() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [serviceInfo, setServiceInfo] = useState<ServiceInfo | null>(null);
  const [mandates, setMandates] = useState<MandateNode[]>([]);
  const [killSwitches, setKillSwitches] = useState<KillSwitchState[]>([]);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) setHealth(await res.json());
    } catch { /* server offline */ }
  }, []);

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/dashboard/summary`);
      if (res.ok) setSummary(await res.json());
    } catch { /* */ }
  }, []);

  const fetchServiceInfo = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/`);
      if (res.ok) setServiceInfo(await res.json());
    } catch { /* */ }
  }, []);

  const fetchMandates = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/mandates`);
      if (res.ok) {
        const data = await res.json();
        setMandates(data.mandates || []);
      }
    } catch { /* */ }
  }, []);

  const fetchKillSwitches = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/kill-switch/status`);
      if (res.ok) {
        const data = await res.json();
        setKillSwitches(data.switches || []);
      }
    } catch { /* */ }
  }, []);

  const screenEntity = useCallback(async (name: string): Promise<ScreeningResult | null> => {
    try {
      const res = await fetch(`${API_BASE}/screen/entity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (res.ok) return await res.json();
    } catch { /* */ }
    return null;
  }, []);

  const screenAddress = useCallback(async (address: string): Promise<ScreeningResult | null> => {
    try {
      const res = await fetch(`${API_BASE}/screen/address`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address }),
      });
      if (res.ok) return await res.json();
    } catch { /* */ }
    return null;
  }, []);

  const createMandate = useCallback(async (body: Record<string, unknown>) => {
    try {
      const res = await fetch(`${API_BASE}/mandates/root`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        await fetchMandates();
        return await res.json();
      }
    } catch { /* */ }
    return null;
  }, [fetchMandates]);

  const freezeMandate = useCallback(async (mandateId: string, reason: string, freezeChildren: boolean) => {
    try {
      const res = await fetch(`${API_BASE}/mandates/freeze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mandate_id: mandateId, reason, freeze_children: freezeChildren }),
      });
      if (res.ok) {
        await fetchMandates();
        return await res.json();
      }
    } catch { /* */ }
    return null;
  }, [fetchMandates]);

  const resumeMandate = useCallback(async (mandateId: string) => {
    try {
      const res = await fetch(`${API_BASE}/mandates/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mandate_id: mandateId }),
      });
      if (res.ok) {
        await fetchMandates();
        return await res.json();
      }
    } catch { /* */ }
    return null;
  }, [fetchMandates]);

  // Initial fetch + polling
  useEffect(() => {
    fetchHealth();
    fetchSummary();
    fetchServiceInfo();
    fetchMandates();
    fetchKillSwitches();

    const interval = setInterval(() => {
      fetchHealth();
      fetchSummary();
      fetchKillSwitches();
    }, 5000);

    const mandateInterval = setInterval(fetchMandates, 10000);

    return () => {
      clearInterval(interval);
      clearInterval(mandateInterval);
    };
  }, [fetchHealth, fetchSummary, fetchServiceInfo, fetchMandates, fetchKillSwitches]);

  return {
    health,
    summary,
    serviceInfo,
    mandates,
    killSwitches,
    screenEntity,
    screenAddress,
    createMandate,
    freezeMandate,
    resumeMandate,
    refetchMandates: fetchMandates,
  };
}
