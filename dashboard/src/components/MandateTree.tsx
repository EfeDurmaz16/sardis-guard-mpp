import { useState, useEffect, useCallback } from "react";
import type { MandateNode } from "../types";

// Hardcoded demo mandate tree for visual effect during hackathon
// In production this would come from API
const DEMO_TREE: MandateNode[] = [
  {
    mandate_id: "mnd_root_001",
    parent_id: null,
    principal_id: "principal_admin",
    agent_id: "root-orchestrator",
    max_total: "500.00",
    max_per_tx: "50.00",
    spent: "127.50",
    remaining: "372.50",
    allowed_services: [],
    allowed_merchants: [],
    blocked_merchants: [],
    allowed_chains: ["tempo", "base", "ethereum"],
    allowed_currencies: ["USDC", "pathUSD", "EURC"],
    status: "active",
    approval_threshold: "100",
    delegation_depth: 0,
    max_delegation_depth: 3,
    created_at: Date.now() / 1000 - 3600,
    expires_at: 0,
    frozen_at: 0,
    frozen_reason: "",
    is_active: true,
  },
  {
    mandate_id: "mnd_child_001",
    parent_id: "mnd_root_001",
    principal_id: "principal_admin",
    agent_id: "research-agent",
    max_total: "100.00",
    max_per_tx: "5.00",
    spent: "42.30",
    remaining: "57.70",
    allowed_services: ["exa", "stableenrich"],
    allowed_merchants: ["stableenrich.dev", "exa.ai"],
    blocked_merchants: [],
    allowed_chains: ["tempo", "base"],
    allowed_currencies: ["USDC", "pathUSD"],
    status: "active",
    approval_threshold: "0",
    delegation_depth: 1,
    max_delegation_depth: 3,
    created_at: Date.now() / 1000 - 3000,
    expires_at: 0,
    frozen_at: 0,
    frozen_reason: "",
    is_active: true,
  },
  {
    mandate_id: "mnd_child_002",
    parent_id: "mnd_root_001",
    principal_id: "principal_admin",
    agent_id: "trading-agent",
    max_total: "200.00",
    max_per_tx: "25.00",
    spent: "85.20",
    remaining: "114.80",
    allowed_services: ["dex", "bridge"],
    allowed_merchants: [],
    blocked_merchants: ["suspicious-dex.xyz"],
    allowed_chains: ["tempo", "base", "ethereum"],
    allowed_currencies: ["USDC", "EURC"],
    status: "active",
    approval_threshold: "50",
    delegation_depth: 1,
    max_delegation_depth: 3,
    created_at: Date.now() / 1000 - 2800,
    expires_at: 0,
    frozen_at: 0,
    frozen_reason: "",
    is_active: true,
  },
  {
    mandate_id: "mnd_child_003",
    parent_id: "mnd_root_001",
    principal_id: "principal_admin",
    agent_id: "outreach-agent",
    max_total: "50.00",
    max_per_tx: "2.00",
    spent: "50.00",
    remaining: "0.00",
    allowed_services: ["email", "social"],
    allowed_merchants: [],
    blocked_merchants: [],
    allowed_chains: ["tempo"],
    allowed_currencies: ["USDC", "pathUSD"],
    status: "exhausted",
    approval_threshold: "0",
    delegation_depth: 1,
    max_delegation_depth: 3,
    created_at: Date.now() / 1000 - 2600,
    expires_at: 0,
    frozen_at: 0,
    frozen_reason: "",
    is_active: false,
  },
  {
    mandate_id: "mnd_grandchild_001",
    parent_id: "mnd_child_002",
    principal_id: "principal_admin",
    agent_id: "sub-trader-alpha",
    max_total: "50.00",
    max_per_tx: "10.00",
    spent: "12.00",
    remaining: "38.00",
    allowed_services: ["dex"],
    allowed_merchants: [],
    blocked_merchants: ["suspicious-dex.xyz"],
    allowed_chains: ["tempo", "base"],
    allowed_currencies: ["USDC"],
    status: "frozen",
    approval_threshold: "0",
    delegation_depth: 2,
    max_delegation_depth: 3,
    created_at: Date.now() / 1000 - 2000,
    expires_at: 0,
    frozen_at: Date.now() / 1000 - 600,
    frozen_reason: "Anomalous trading pattern detected",
    is_active: false,
  },
];

interface MandateTreeProps {
  _unused?: never;
}

function statusBadge(node: MandateNode) {
  switch (node.status) {
    case "active":
      return (
        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold font-mono bg-sardis-green/15 text-sardis-green border border-sardis-green/30">
          ACTIVE
        </span>
      );
    case "frozen":
      return (
        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold font-mono bg-sardis-red/15 text-sardis-red border border-sardis-red/30">
          FROZEN
        </span>
      );
    case "exhausted":
      return (
        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold font-mono bg-sardis-orange/15 text-sardis-orange border border-sardis-orange/30">
          EXHAUSTED
        </span>
      );
    case "expired":
      return (
        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold font-mono bg-sardis-text-dim/30 text-sardis-text-dim border border-sardis-text-dim/30">
          EXPIRED
        </span>
      );
  }
}

function budgetBar(node: MandateNode) {
  const total = parseFloat(node.max_total);
  const spent = parseFloat(node.spent);
  const pct = total > 0 ? (spent / total) * 100 : 0;

  let barColor = "bg-sardis-green";
  if (pct > 80) barColor = "bg-sardis-red";
  else if (pct > 50) barColor = "bg-sardis-yellow";

  return (
    <div className="mt-1.5">
      <div className="flex items-center justify-between text-[10px] font-mono mb-0.5">
        <span className="text-sardis-text-dim">
          ${node.spent} / ${node.max_total}
        </span>
        <span className="text-sardis-text-dim">{pct.toFixed(0)}%</span>
      </div>
      <div className="h-1 bg-sardis-surface rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function MandateNodeCard({
  node,
  selected,
  onClick,
}: {
  node: MandateNode;
  selected: boolean;
  onClick: () => void;
}) {
  const isFrozen = node.status === "frozen";
  const isExhausted = node.status === "exhausted";
  const isInactive = isFrozen || isExhausted;

  return (
    <div
      onClick={onClick}
      className={`rounded-lg border px-3 py-2 cursor-pointer transition-all duration-200 ${
        selected
          ? "border-sardis-blue bg-sardis-blue/10 shadow-lg shadow-sardis-blue/10"
          : isInactive
            ? "border-sardis-border/50 bg-sardis-surface-2/50 opacity-60"
            : "border-sardis-border bg-sardis-surface-2 hover:border-sardis-blue/50"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span
          className={`text-xs font-mono font-semibold truncate ${
            isFrozen
              ? "text-sardis-red"
              : isExhausted
                ? "text-sardis-orange"
                : "text-sardis-cyan"
          }`}
        >
          {node.agent_id}
        </span>
        {statusBadge(node)}
      </div>
      {budgetBar(node)}
      <div className="mt-1 text-[10px] font-mono text-sardis-text-dim">
        ${node.remaining} remaining &middot; ${node.max_per_tx}/tx
      </div>
    </div>
  );
}

function MandateDetails({ node }: { node: MandateNode }) {
  return (
    <div className="mt-3 border-t border-sardis-border pt-3 space-y-2 text-xs">
      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
        <div>
          <span className="text-sardis-text-dim">Mandate ID</span>
          <p className="font-mono text-white text-[10px]">{node.mandate_id}</p>
        </div>
        <div>
          <span className="text-sardis-text-dim">Depth</span>
          <p className="font-mono text-white">
            {node.delegation_depth} / {node.max_delegation_depth}
          </p>
        </div>
        <div>
          <span className="text-sardis-text-dim">Chains</span>
          <p className="font-mono text-sardis-cyan text-[10px]">
            {node.allowed_chains.join(", ")}
          </p>
        </div>
        <div>
          <span className="text-sardis-text-dim">Currencies</span>
          <p className="font-mono text-sardis-cyan text-[10px]">
            {node.allowed_currencies.join(", ")}
          </p>
        </div>
        {node.allowed_merchants.length > 0 && (
          <div className="col-span-2">
            <span className="text-sardis-text-dim">Allowed Merchants</span>
            <p className="font-mono text-sardis-green text-[10px]">
              {node.allowed_merchants.join(", ")}
            </p>
          </div>
        )}
        {node.blocked_merchants.length > 0 && (
          <div className="col-span-2">
            <span className="text-sardis-text-dim">Blocked Merchants</span>
            <p className="font-mono text-sardis-red text-[10px]">
              {node.blocked_merchants.join(", ")}
            </p>
          </div>
        )}
        {node.frozen_reason && (
          <div className="col-span-2">
            <span className="text-sardis-text-dim">Freeze Reason</span>
            <p className="font-mono text-sardis-red text-[10px]">
              {node.frozen_reason}
            </p>
          </div>
        )}
        {parseFloat(node.approval_threshold) > 0 && (
          <div>
            <span className="text-sardis-text-dim">Approval Threshold</span>
            <p className="font-mono text-sardis-yellow">
              ${node.approval_threshold}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export function MandateTree({}: MandateTreeProps) {
  const [tree, setTree] = useState<MandateNode[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    // Use demo data; in production, fetch from API
    setTree(DEMO_TREE);
  }, []);

  const roots = tree.filter((n) => n.parent_id === null);
  const getChildren = useCallback(
    (parentId: string) => tree.filter((n) => n.parent_id === parentId),
    [tree]
  );
  const selectedNode = tree.find((n) => n.mandate_id === selectedId) ?? null;

  const renderNode = (node: MandateNode, depth: number = 0) => {
    const children = getChildren(node.mandate_id);
    return (
      <div
        key={node.mandate_id}
        className={depth > 0 ? "ml-4 mt-1 border-l border-sardis-border/40 pl-3" : ""}
      >
        <MandateNodeCard
          node={node}
          selected={selectedId === node.mandate_id}
          onClick={() =>
            setSelectedId(
              selectedId === node.mandate_id ? null : node.mandate_id
            )
          }
        />
        {children.length > 0 && (
          <div className="mt-1 space-y-1">
            {children.map((child) => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-sardis-surface border border-sardis-border rounded-xl flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-sardis-border">
        <h2 className="text-sm font-semibold text-white">Mandate Tree</h2>
        <span className="text-xs font-mono text-sardis-text-dim">
          {tree.length} nodes &middot;{" "}
          {tree.filter((n) => n.status === "frozen").length} frozen
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {roots.map((root) => renderNode(root))}
      </div>

      {selectedNode && (
        <div className="border-t border-sardis-border px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-white">
              {selectedNode.agent_id}
            </span>
            <button
              onClick={() => setSelectedId(null)}
              className="text-xs text-sardis-text-dim hover:text-white transition-colors"
            >
              Close
            </button>
          </div>
          <MandateDetails node={selectedNode} />
        </div>
      )}
    </div>
  );
}
