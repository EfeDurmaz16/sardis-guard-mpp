import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import type { MandateNode } from "../../types";

interface MandatesViewProps {
  mandates: MandateNode[];
  onFreeze: (id: string, reason: string, children: boolean) => void;
  onResume: (id: string) => void;
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

export function MandatesView({ mandates, onFreeze, onResume }: MandatesViewProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selectedNode = mandates.find((m) => m.mandate_id === selectedId) || null;
  const roots = mandates.filter((m) => m.parent_id === null);
  const getChildren = (parentId: string) => mandates.filter((m) => m.parent_id === parentId);

  const renderNode = (node: MandateNode, depth: number = 0) => {
    const children = getChildren(node.mandate_id);
    const isSelected = selectedId === node.mandate_id;

    return (
      <div key={node.mandate_id} className={depth > 0 ? "ml-6 border-l border-border pl-4" : ""}>
        <div
          onClick={() => setSelectedId(isSelected ? null : node.mandate_id)}
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
        </div>
      </div>

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
                  <div className="flex items-center justify-center h-48 text-sardis-text-muted text-xs">
                    No mandates — create one via POST /mandates/root
                  </div>
                ) : (
                  roots.map((root) => renderNode(root))
                )}
              </CardContent>
            </ScrollArea>
          </Card>
        </div>

        {/* Detail panel */}
        <div className="col-span-1 min-h-0">
          <Card className="bg-sardis-surface border-border h-full">
            <CardHeader className="py-3 px-4 border-b border-border">
              <CardTitle className="text-xs font-medium text-sardis-text-secondary">
                {selectedNode ? selectedNode.agent_id : "Select a mandate"}
              </CardTitle>
            </CardHeader>
            <ScrollArea className="h-[calc(100%-44px)]">
              <CardContent className="p-4">
                {!selectedNode ? (
                  <p className="text-xs text-sardis-text-muted">Click a mandate node to view details</p>
                ) : (
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

                    <div className="flex gap-2">
                      {selectedNode.status === "active" && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-[10px] font-mono border-sardis-red/30 text-sardis-red hover:bg-sardis-red-glow"
                          onClick={() => onFreeze(selectedNode.mandate_id, "Manual freeze from dashboard", false)}
                        >
                          Freeze
                        </Button>
                      )}
                      {selectedNode.status === "frozen" && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-[10px] font-mono border-sardis-green/30 text-sardis-green hover:bg-sardis-green-glow"
                          onClick={() => onResume(selectedNode.mandate_id)}
                        >
                          Resume
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
