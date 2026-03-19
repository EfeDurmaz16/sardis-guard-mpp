import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import type { MandateNode } from "../../types";

interface MandatesViewProps {
  mandates: MandateNode[];
  onFreeze: (id: string, reason: string, children: boolean) => Promise<unknown>;
  onResume: (id: string) => Promise<unknown>;
  onCreateMandate: (body: Record<string, unknown>) => Promise<unknown>;
  onDelegateMandate: (body: Record<string, unknown>) => Promise<unknown>;
}

function statusBadge(status: MandateNode["status"]) {
  const map: Record<string, string> = {
    active: "bg-sardis-green-glow text-sardis-green border-sardis-green/20",
    frozen: "bg-sardis-red-glow text-sardis-red border-sardis-red/20",
    exhausted: "bg-sardis-amber-glow text-sardis-amber border-sardis-amber/20",
    expired: "bg-sardis-surface-3 text-sardis-text-muted border-sardis-text-faint",
  };
  return (
    <Badge variant="outline" className={`text-[9px] font-mono font-bold px-1.5 py-0 uppercase ${map[status] || ""}`}>
      {status}
    </Badge>
  );
}

function BudgetBar({ spent, total }: { spent: string; total: string }) {
  const s = parseFloat(spent);
  const t = parseFloat(total);
  const pct = t > 0 ? (s / t) * 100 : 0;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[10px] font-mono">
        <span className="text-sardis-text-muted">${spent} / ${total}</span>
        <span className={pct > 80 ? "text-sardis-red" : pct > 50 ? "text-sardis-amber" : "text-sardis-text-muted"}>
          {pct.toFixed(0)}%
        </span>
      </div>
      <Progress value={pct} className="h-1 bg-sardis-surface-2" />
    </div>
  );
}

type PanelMode = "detail" | "create" | "delegate" | "freeze";

export function MandatesView({ mandates, onFreeze, onResume, onCreateMandate, onDelegateMandate }: MandatesViewProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [panelMode, setPanelMode] = useState<PanelMode>("detail");

  // Create form state
  const [createForm, setCreateForm] = useState({
    principal_id: "org-demo",
    agent_id: "",
    max_total: "100.00",
    max_per_tx: "10.00",
    allowed_services: "",
    allowed_chains: "base, tempo",
    allowed_currencies: "USDC",
  });

  // Delegate form state
  const [delegateForm, setDelegateForm] = useState({
    agent_id: "",
    max_total: "50.00",
    max_per_tx: "5.00",
    allowed_services: "",
  });

  // Freeze form state
  const [freezeReason, setFreezeReason] = useState("Manual freeze from dashboard");
  const [freezeChildren, setFreezeChildren] = useState(false);

  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const selectedNode = mandates.find((m) => m.mandate_id === selectedId) || null;
  const roots = mandates.filter((m) => m.parent_id === null);
  const getChildren = (parentId: string) => mandates.filter((m) => m.parent_id === parentId);

  const showFeedback = (type: "success" | "error", message: string) => {
    setFeedback({ type, message });
    setTimeout(() => setFeedback(null), 4000);
  };

  const handleCreate = async () => {
    setLoading(true);
    setFeedback(null);
    try {
      const body: Record<string, unknown> = {
        principal_id: createForm.principal_id,
        agent_id: createForm.agent_id,
        max_total: createForm.max_total,
        max_per_tx: createForm.max_per_tx,
      };
      if (createForm.allowed_services.trim()) {
        body.allowed_services = createForm.allowed_services.split(",").map((s) => s.trim()).filter(Boolean);
      }
      if (createForm.allowed_chains.trim()) {
        body.allowed_chains = createForm.allowed_chains.split(",").map((s) => s.trim()).filter(Boolean);
      }
      if (createForm.allowed_currencies.trim()) {
        body.allowed_currencies = createForm.allowed_currencies.split(",").map((s) => s.trim()).filter(Boolean);
      }
      await onCreateMandate(body);
      showFeedback("success", `Mandate created for ${createForm.agent_id}`);
      setCreateForm({ ...createForm, agent_id: "" });
      setPanelMode("detail");
    } catch (e) {
      showFeedback("error", e instanceof Error ? e.message : "Failed to create mandate");
    }
    setLoading(false);
  };

  const handleDelegate = async () => {
    if (!selectedId) return;
    setLoading(true);
    setFeedback(null);
    try {
      const body: Record<string, unknown> = {
        parent_mandate_id: selectedId,
        agent_id: delegateForm.agent_id,
        max_total: delegateForm.max_total,
        max_per_tx: delegateForm.max_per_tx,
      };
      if (delegateForm.allowed_services.trim()) {
        body.allowed_services = delegateForm.allowed_services.split(",").map((s) => s.trim()).filter(Boolean);
      }
      await onDelegateMandate(body);
      showFeedback("success", `Delegated to ${delegateForm.agent_id}`);
      setDelegateForm({ ...delegateForm, agent_id: "" });
      setPanelMode("detail");
    } catch (e) {
      showFeedback("error", e instanceof Error ? e.message : "Failed to delegate mandate");
    }
    setLoading(false);
  };

  const handleFreeze = async () => {
    if (!selectedId) return;
    setLoading(true);
    setFeedback(null);
    try {
      await onFreeze(selectedId, freezeReason, freezeChildren);
      showFeedback("success", `Mandate frozen: ${selectedId.slice(0, 12)}...`);
      setPanelMode("detail");
    } catch (e) {
      showFeedback("error", e instanceof Error ? e.message : "Failed to freeze mandate");
    }
    setLoading(false);
  };

  const handleResume = async (id: string) => {
    setLoading(true);
    setFeedback(null);
    try {
      await onResume(id);
      showFeedback("success", `Mandate resumed: ${id.slice(0, 12)}...`);
    } catch (e) {
      showFeedback("error", e instanceof Error ? e.message : "Failed to resume mandate");
    }
    setLoading(false);
  };

  const renderNode = (node: MandateNode, depth: number = 0) => {
    const children = getChildren(node.mandate_id);
    const isSelected = selectedId === node.mandate_id;

    return (
      <div key={node.mandate_id} className={depth > 0 ? "ml-6 border-l border-border pl-4" : ""}>
        <div
          onClick={() => {
            setSelectedId(isSelected ? null : node.mandate_id);
            setPanelMode("detail");
          }}
          className={`rounded-lg border px-4 py-3 cursor-pointer transition-all duration-150 mb-1.5 ${
            isSelected
              ? "border-sardis-amber/30 bg-sardis-amber-glow"
              : node.status !== "active"
                ? "border-border/50 bg-sardis-surface-2/50 opacity-60 hover:opacity-80"
                : "border-border bg-sardis-surface-2 hover:border-sardis-amber/20"
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className={`text-xs font-mono font-semibold ${
              node.status === "frozen" ? "text-sardis-red" :
              node.status === "exhausted" ? "text-sardis-amber" :
              "text-sardis-text"
            }`}>
              {node.agent_id}
            </span>
            {statusBadge(node.status)}
          </div>
          <BudgetBar spent={node.spent} total={node.max_total} />
          <div className="mt-1.5 text-[10px] font-mono text-sardis-text-muted">
            ${node.remaining} remaining / ${node.max_per_tx} per-tx / depth {node.delegation_depth}
          </div>
        </div>
        {children.length > 0 && (
          <div className="space-y-1.5 mt-1.5">
            {children.map((child) => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col p-5 gap-4 fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-sardis-text tracking-tight">Mandates</h1>
          <p className="text-xs text-sardis-text-muted">Delegation tree and budget governance</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-sardis-text-muted">
            {mandates.length} nodes / {mandates.filter((m) => m.status === "frozen").length} frozen
          </span>
          <Button
            variant="outline"
            size="sm"
            className="text-[10px] font-mono border-sardis-amber/30 text-sardis-amber hover:bg-sardis-amber-glow"
            onClick={() => {
              setSelectedId(null);
              setPanelMode("create");
            }}
          >
            + New Root Mandate
          </Button>
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

      <div className="flex-1 grid grid-cols-3 gap-4 min-h-0">
        {/* Tree */}
        <div className="col-span-2 min-h-0">
          <Card className="bg-sardis-surface border-border h-full">
            <CardHeader className="py-3 px-4 border-b border-border">
              <CardTitle className="text-xs font-medium text-sardis-text-secondary">Mandate Tree</CardTitle>
            </CardHeader>
            <ScrollArea className="h-[calc(100%-44px)]">
              <CardContent className="p-4 space-y-1.5">
                {mandates.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-48 text-sardis-text-muted">
                    <p className="text-xs">No mandates yet</p>
                    <p className="text-[10px] text-sardis-text-faint mt-1">
                      Click "New Root Mandate" to create one
                    </p>
                  </div>
                ) : (
                  roots.map((root) => renderNode(root))
                )}
              </CardContent>
            </ScrollArea>
          </Card>
        </div>

        {/* Detail / Create / Delegate panel */}
        <div className="col-span-1 min-h-0">
          <Card className="bg-sardis-surface border-border h-full">
            <CardHeader className="py-3 px-4 border-b border-border">
              <CardTitle className="text-xs font-medium text-sardis-text-secondary">
                {panelMode === "create"
                  ? "Create Root Mandate"
                  : panelMode === "delegate"
                    ? "Delegate Mandate"
                    : panelMode === "freeze"
                      ? "Freeze Mandate"
                      : selectedNode
                        ? selectedNode.agent_id
                        : "Select a mandate"}
              </CardTitle>
            </CardHeader>
            <ScrollArea className="h-[calc(100%-44px)]">
              <CardContent className="p-4">
                {/* CREATE FORM */}
                {panelMode === "create" && (
                  <div className="space-y-4">
                    <div className="space-y-3">
                      <div className="space-y-1.5">
                        <Label className="text-[11px] text-sardis-text-muted">Principal ID</Label>
                        <Input
                          value={createForm.principal_id}
                          onChange={(e) => setCreateForm({ ...createForm, principal_id: e.target.value })}
                          placeholder="org-demo"
                          className="font-mono text-sm bg-sardis-surface-2 border-border"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-[11px] text-sardis-text-muted">Agent ID</Label>
                        <Input
                          value={createForm.agent_id}
                          onChange={(e) => setCreateForm({ ...createForm, agent_id: e.target.value })}
                          placeholder="agent-shopping-01"
                          className="font-mono text-sm bg-sardis-surface-2 border-border"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="space-y-1.5">
                          <Label className="text-[11px] text-sardis-text-muted">Max Total ($)</Label>
                          <Input
                            value={createForm.max_total}
                            onChange={(e) => setCreateForm({ ...createForm, max_total: e.target.value })}
                            placeholder="100.00"
                            className="font-mono text-sm bg-sardis-surface-2 border-border"
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label className="text-[11px] text-sardis-text-muted">Max Per TX ($)</Label>
                          <Input
                            value={createForm.max_per_tx}
                            onChange={(e) => setCreateForm({ ...createForm, max_per_tx: e.target.value })}
                            placeholder="10.00"
                            className="font-mono text-sm bg-sardis-surface-2 border-border"
                          />
                        </div>
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-[11px] text-sardis-text-muted">Allowed Services (comma-separated)</Label>
                        <Input
                          value={createForm.allowed_services}
                          onChange={(e) => setCreateForm({ ...createForm, allowed_services: e.target.value })}
                          placeholder="perplexity.ai, openai.com"
                          className="font-mono text-sm bg-sardis-surface-2 border-border"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-[11px] text-sardis-text-muted">Allowed Chains (comma-separated)</Label>
                        <Input
                          value={createForm.allowed_chains}
                          onChange={(e) => setCreateForm({ ...createForm, allowed_chains: e.target.value })}
                          placeholder="base, tempo"
                          className="font-mono text-sm bg-sardis-surface-2 border-border"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-[11px] text-sardis-text-muted">Allowed Currencies (comma-separated)</Label>
                        <Input
                          value={createForm.allowed_currencies}
                          onChange={(e) => setCreateForm({ ...createForm, allowed_currencies: e.target.value })}
                          placeholder="USDC, EURC"
                          className="font-mono text-sm bg-sardis-surface-2 border-border"
                        />
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <Button
                        onClick={handleCreate}
                        disabled={loading || !createForm.agent_id.trim() || !createForm.principal_id.trim()}
                        className="flex-1 bg-sardis-amber text-sardis-bg hover:bg-sardis-amber/90 font-mono text-xs"
                      >
                        {loading ? "Creating..." : "Create Mandate"}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-[10px] font-mono border-border text-sardis-text-muted hover:bg-sardis-surface-2"
                        onClick={() => setPanelMode("detail")}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}

                {/* DELEGATE FORM */}
                {panelMode === "delegate" && selectedNode && (
                  <div className="space-y-4">
                    <div className="rounded-md bg-sardis-surface-2 px-3 py-2 text-[10px] font-mono text-sardis-text-muted">
                      Delegating from: <span className="text-sardis-amber">{selectedNode.agent_id}</span>
                      <br />
                      Parent budget: <span className="text-sardis-text-secondary">${selectedNode.remaining} remaining</span>
                    </div>

                    <div className="space-y-3">
                      <div className="space-y-1.5">
                        <Label className="text-[11px] text-sardis-text-muted">Sub-Agent ID</Label>
                        <Input
                          value={delegateForm.agent_id}
                          onChange={(e) => setDelegateForm({ ...delegateForm, agent_id: e.target.value })}
                          placeholder="sub-agent-01"
                          className="font-mono text-sm bg-sardis-surface-2 border-border"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="space-y-1.5">
                          <Label className="text-[11px] text-sardis-text-muted">Max Total ($)</Label>
                          <Input
                            value={delegateForm.max_total}
                            onChange={(e) => setDelegateForm({ ...delegateForm, max_total: e.target.value })}
                            placeholder="50.00"
                            className="font-mono text-sm bg-sardis-surface-2 border-border"
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label className="text-[11px] text-sardis-text-muted">Max Per TX ($)</Label>
                          <Input
                            value={delegateForm.max_per_tx}
                            onChange={(e) => setDelegateForm({ ...delegateForm, max_per_tx: e.target.value })}
                            placeholder="5.00"
                            className="font-mono text-sm bg-sardis-surface-2 border-border"
                          />
                        </div>
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-[11px] text-sardis-text-muted">Allowed Services (comma-separated)</Label>
                        <Input
                          value={delegateForm.allowed_services}
                          onChange={(e) => setDelegateForm({ ...delegateForm, allowed_services: e.target.value })}
                          placeholder="perplexity.ai"
                          className="font-mono text-sm bg-sardis-surface-2 border-border"
                        />
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <Button
                        onClick={handleDelegate}
                        disabled={loading || !delegateForm.agent_id.trim()}
                        className="flex-1 bg-sardis-amber text-sardis-bg hover:bg-sardis-amber/90 font-mono text-xs"
                      >
                        {loading ? "Delegating..." : "Delegate"}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-[10px] font-mono border-border text-sardis-text-muted hover:bg-sardis-surface-2"
                        onClick={() => setPanelMode("detail")}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}

                {/* FREEZE FORM */}
                {panelMode === "freeze" && selectedNode && (
                  <div className="space-y-4">
                    <div className="rounded-md bg-sardis-red-glow border border-sardis-red/20 px-3 py-2 text-[10px] font-mono text-sardis-red">
                      Freezing mandate for: <span className="font-bold">{selectedNode.agent_id}</span>
                    </div>

                    <div className="space-y-3">
                      <div className="space-y-1.5">
                        <Label className="text-[11px] text-sardis-text-muted">Reason</Label>
                        <Input
                          value={freezeReason}
                          onChange={(e) => setFreezeReason(e.target.value)}
                          placeholder="Suspicious activity detected"
                          className="font-mono text-sm bg-sardis-surface-2 border-border"
                        />
                      </div>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={freezeChildren}
                          onChange={(e) => setFreezeChildren(e.target.checked)}
                          className="rounded border-border bg-sardis-surface-2 accent-sardis-red"
                        />
                        <span className="text-[11px] text-sardis-text-muted">Also freeze child mandates</span>
                      </label>
                    </div>

                    <div className="flex gap-2">
                      <Button
                        onClick={handleFreeze}
                        disabled={loading || !freezeReason.trim()}
                        variant="outline"
                        className="flex-1 text-xs font-mono border-sardis-red/30 text-sardis-red hover:bg-sardis-red-glow"
                      >
                        {loading ? "Freezing..." : "Confirm Freeze"}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-[10px] font-mono border-border text-sardis-text-muted hover:bg-sardis-surface-2"
                        onClick={() => setPanelMode("detail")}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}

                {/* DETAIL VIEW */}
                {panelMode === "detail" && !selectedNode && (
                  <p className="text-xs text-sardis-text-muted">Click a mandate node to view details, or create a new one</p>
                )}

                {panelMode === "detail" && selectedNode && (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <DetailRow label="Mandate ID" value={selectedNode.mandate_id} mono />
                      <DetailRow label="Principal" value={selectedNode.principal_id} />
                      <DetailRow label="Status" value={selectedNode.status.toUpperCase()} />
                      <DetailRow label="Depth" value={`${selectedNode.delegation_depth} / ${selectedNode.max_delegation_depth}`} />
                    </div>

                    <Separator className="bg-border" />

                    <div className="space-y-2">
                      <p className="text-[10px] font-medium text-sardis-text-muted uppercase tracking-wider">Budget</p>
                      <BudgetBar spent={selectedNode.spent} total={selectedNode.max_total} />
                      <DetailRow label="Per-TX Limit" value={`$${selectedNode.max_per_tx}`} />
                      <DetailRow label="Remaining" value={`$${selectedNode.remaining}`} />
                      {parseFloat(selectedNode.approval_threshold) > 0 && (
                        <DetailRow label="Approval Above" value={`$${selectedNode.approval_threshold}`} />
                      )}
                    </div>

                    <Separator className="bg-border" />

                    <div className="space-y-2">
                      <p className="text-[10px] font-medium text-sardis-text-muted uppercase tracking-wider">Scope</p>
                      <DetailRow label="Chains" value={selectedNode.allowed_chains.join(", ") || "any"} />
                      <DetailRow label="Currencies" value={selectedNode.allowed_currencies.join(", ") || "any"} />
                      {selectedNode.allowed_services.length > 0 && (
                        <DetailRow label="Services" value={selectedNode.allowed_services.join(", ")} color="text-sardis-cyan" />
                      )}
                      {selectedNode.allowed_merchants.length > 0 && (
                        <DetailRow label="Merchants" value={selectedNode.allowed_merchants.join(", ")} color="text-sardis-green" />
                      )}
                      {selectedNode.blocked_merchants.length > 0 && (
                        <DetailRow label="Blocked" value={selectedNode.blocked_merchants.join(", ")} color="text-sardis-red" />
                      )}
                    </div>

                    {selectedNode.frozen_reason && (
                      <>
                        <Separator className="bg-border" />
                        <div className="space-y-1">
                          <p className="text-[10px] font-medium text-sardis-red uppercase tracking-wider">Freeze Reason</p>
                          <p className="text-[11px] font-mono text-sardis-red">{selectedNode.frozen_reason}</p>
                        </div>
                      </>
                    )}

                    <Separator className="bg-border" />

                    <div className="flex flex-col gap-2">
                      {selectedNode.status === "active" && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full text-[10px] font-mono border-sardis-amber/30 text-sardis-amber hover:bg-sardis-amber-glow"
                            onClick={() => {
                              setDelegateForm({
                                agent_id: "",
                                max_total: (parseFloat(selectedNode.remaining) / 2).toFixed(2),
                                max_per_tx: selectedNode.max_per_tx,
                                allowed_services: selectedNode.allowed_services.join(", "),
                              });
                              setPanelMode("delegate");
                            }}
                            disabled={selectedNode.delegation_depth >= selectedNode.max_delegation_depth}
                          >
                            Delegate Sub-Mandate
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full text-[10px] font-mono border-sardis-red/30 text-sardis-red hover:bg-sardis-red-glow"
                            onClick={() => {
                              setFreezeReason("Manual freeze from dashboard");
                              setFreezeChildren(false);
                              setPanelMode("freeze");
                            }}
                          >
                            Freeze Mandate
                          </Button>
                        </>
                      )}
                      {selectedNode.status === "frozen" && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full text-[10px] font-mono border-sardis-green/30 text-sardis-green hover:bg-sardis-green-glow"
                          onClick={() => handleResume(selectedNode.mandate_id)}
                          disabled={loading}
                        >
                          {loading ? "Resuming..." : "Resume Mandate"}
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </ScrollArea>
          </Card>
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value, mono, color }: { label: string; value: string; mono?: boolean; color?: string }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <span className="text-[10px] text-sardis-text-muted shrink-0">{label}</span>
      <span className={`text-[11px] text-right truncate ${mono ? "font-mono" : ""} ${color || "text-sardis-text-secondary"}`}>
        {value}
      </span>
    </div>
  );
}
