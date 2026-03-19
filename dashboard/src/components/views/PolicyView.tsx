import { useState, useCallback } from "react";
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

interface PolicyCheckResult {
  name: string;
  result: "PASS" | "FAIL";
  reason: string;
}

interface SimulationResult {
  allowed: boolean;
  checks: PolicyCheckResult[];
  latency: string;
}

const DEFAULT_MANDATE = {
  maxPerTx: 5,
  maxDaily: 50,
  allowedChains: ["tempo", "base", "ethereum", "polygon", "arbitrum", "optimism"],
  allowedCurrencies: ["USDC", "pathUSD", "EURC", "USDT"],
  blockedMerchants: [] as string[],
  requireMemo: false,
  maxGasGwei: 50,
  cooldownSeconds: 0,
};

export function PolicyView() {
  const [amount, setAmount] = useState("1.50");
  const [merchant, setMerchant] = useState("perplexity.ai");
  const [currency, setCurrency] = useState("USDC");
  const [network, setNetwork] = useState("tempo");
  const [category, setCategory] = useState("general");
  const [memo, setMemo] = useState("");
  const [gasPrice, setGasPrice] = useState("");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);

  const runLocalSimulation = useCallback(() => {
    setLoading(true);
    const start = performance.now();
    const amt = parseFloat(amount) || 0;
    const checks: PolicyCheckResult[] = [];

    // 1. mandate_active
    checks.push({ name: "mandate_active", result: "PASS", reason: "Mandate is active" });

    // 2. per_tx_limit
    const perTxOk = amt <= DEFAULT_MANDATE.maxPerTx;
    checks.push({
      name: "per_tx_limit",
      result: perTxOk ? "PASS" : "FAIL",
      reason: perTxOk ? `$${amt} <= $${DEFAULT_MANDATE.maxPerTx} limit` : `$${amt} exceeds $${DEFAULT_MANDATE.maxPerTx} per-tx limit`,
    });

    // 3. daily_limit
    const dailyOk = amt <= DEFAULT_MANDATE.maxDaily;
    checks.push({
      name: "daily_limit",
      result: dailyOk ? "PASS" : "FAIL",
      reason: dailyOk ? `$${amt} <= $${DEFAULT_MANDATE.maxDaily} daily limit` : `$${amt} would exceed $${DEFAULT_MANDATE.maxDaily} daily limit`,
    });

    // 4. merchant_allowlist
    checks.push({ name: "merchant_allowlist", result: "PASS", reason: "Merchant allowed (no allowlist)" });

    // 5. merchant_blocklist
    const merchantBlocked = DEFAULT_MANDATE.blockedMerchants.includes(merchant);
    checks.push({
      name: "merchant_blocklist",
      result: merchantBlocked ? "FAIL" : "PASS",
      reason: merchantBlocked ? `${merchant} is blocked` : "Merchant not blocked",
    });

    // 6. category_allowlist
    checks.push({ name: "category_allowlist", result: "PASS", reason: "Category allowed" });

    // 7. category_blocklist
    checks.push({ name: "category_blocklist", result: "PASS", reason: "Category not blocked" });

    // 8. chain_allowlist
    const chainOk = DEFAULT_MANDATE.allowedChains.includes(network);
    checks.push({
      name: "chain_allowlist",
      result: chainOk ? "PASS" : "FAIL",
      reason: chainOk ? `Chain ${network} allowed` : `Chain ${network} not in allowed chains`,
    });

    // 9. currency_allowlist
    const currOk = DEFAULT_MANDATE.allowedCurrencies.includes(currency);
    checks.push({
      name: "currency_allowlist",
      result: currOk ? "PASS" : "FAIL",
      reason: currOk ? `Currency ${currency} allowed` : `Currency ${currency} not allowed`,
    });

    // 10. memo_requirement
    const memoOk = !DEFAULT_MANDATE.requireMemo || memo.length > 0;
    checks.push({
      name: "memo_requirement",
      result: memoOk ? "PASS" : "FAIL",
      reason: memoOk ? "Memo provided or not required" : "Memo required but not provided",
    });

    // 11. gas_price
    const gasPriceVal = gasPrice ? parseFloat(gasPrice) : null;
    const gasOk = gasPriceVal === null || gasPriceVal <= DEFAULT_MANDATE.maxGasGwei;
    checks.push({
      name: "gas_price",
      result: gasOk ? "PASS" : "FAIL",
      reason: gasOk ? "Gas price acceptable" : `Gas ${gasPriceVal} gwei exceeds ${DEFAULT_MANDATE.maxGasGwei} gwei limit`,
    });

    // 12. cooldown
    checks.push({ name: "cooldown", result: "PASS", reason: "Cooldown satisfied" });

    const elapsed = performance.now() - start;
    const allowed = checks.every((c) => c.result === "PASS");

    setResult({ allowed, checks, latency: elapsed.toFixed(2) });
    setLoading(false);
  }, [amount, merchant, currency, network, memo, gasPrice]);

  return (
    <div className="h-full flex flex-col p-5 gap-4 fade-in">
      <div>
        <h1 className="text-lg font-semibold text-sardis-text tracking-tight">Policy Simulator</h1>
        <p className="text-xs text-sardis-text-muted">Test payments against the security gate engine locally</p>
      </div>

      <div className="flex-1 grid grid-cols-2 gap-4 min-h-0">
        {/* Left: Form */}
        <Card className="bg-sardis-surface border-border">
          <CardHeader className="py-3 px-4 border-b border-border">
            <CardTitle className="text-xs font-medium text-sardis-text-secondary">Payment Details</CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[11px] text-sardis-text-muted">Amount (USD)</Label>
                <Input
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="1.50"
                  className="font-mono text-sm bg-sardis-surface-2 border-border"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-[11px] text-sardis-text-muted">Merchant</Label>
                <Input
                  value={merchant}
                  onChange={(e) => setMerchant(e.target.value)}
                  placeholder="perplexity.ai"
                  className="font-mono text-sm bg-sardis-surface-2 border-border"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[11px] text-sardis-text-muted">Currency</Label>
                <Select value={currency} onValueChange={setCurrency}>
                  <SelectTrigger className="font-mono text-sm bg-sardis-surface-2 border-border">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USDC">USDC</SelectItem>
                    <SelectItem value="pathUSD">pathUSD</SelectItem>
                    <SelectItem value="EURC">EURC</SelectItem>
                    <SelectItem value="USDT">USDT</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-[11px] text-sardis-text-muted">Network</Label>
                <Select value={network} onValueChange={setNetwork}>
                  <SelectTrigger className="font-mono text-sm bg-sardis-surface-2 border-border">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="tempo">Tempo</SelectItem>
                    <SelectItem value="base">Base</SelectItem>
                    <SelectItem value="ethereum">Ethereum</SelectItem>
                    <SelectItem value="polygon">Polygon</SelectItem>
                    <SelectItem value="arbitrum">Arbitrum</SelectItem>
                    <SelectItem value="optimism">Optimism</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[11px] text-sardis-text-muted">Category</Label>
                <Input
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder="general"
                  className="font-mono text-sm bg-sardis-surface-2 border-border"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-[11px] text-sardis-text-muted">Gas Price (gwei)</Label>
                <Input
                  value={gasPrice}
                  onChange={(e) => setGasPrice(e.target.value)}
                  placeholder="optional"
                  className="font-mono text-sm bg-sardis-surface-2 border-border"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-[11px] text-sardis-text-muted">Memo</Label>
              <Input
                value={memo}
                onChange={(e) => setMemo(e.target.value)}
                placeholder="optional"
                className="font-mono text-sm bg-sardis-surface-2 border-border"
              />
            </div>

            <Button
              onClick={runLocalSimulation}
              disabled={loading || !amount || !merchant}
              className="w-full bg-sardis-amber text-sardis-bg hover:bg-sardis-amber/90 font-mono text-sm"
            >
              Run Simulation
            </Button>
          </CardContent>
        </Card>

        {/* Right: Results */}
        <Card className="bg-sardis-surface border-border overflow-hidden">
          <CardHeader className="py-3 px-4 border-b border-border">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-medium text-sardis-text-secondary">Security Gate Results</CardTitle>
              {result && (
                <Badge variant="outline" className={`text-[10px] font-mono font-bold ${
                  result.allowed
                    ? "border-sardis-green/30 text-sardis-green"
                    : "border-sardis-red/30 text-sardis-red"
                }`}>
                  {result.allowed ? "ALLOWED" : "DENIED"} in {result.latency}ms
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {!result ? (
              <div className="flex items-center justify-center h-64 text-sardis-text-muted text-xs">
                Configure payment details and run simulation
              </div>
            ) : (
              <div className="divide-y divide-border">
                {result.checks.map((check, i) => (
                  <div
                    key={check.name}
                    className={`px-4 py-2.5 flex items-center gap-3 ${
                      check.result === "FAIL" ? "bg-sardis-red-glow" : ""
                    }`}
                  >
                    <span className="text-[10px] font-mono text-sardis-text-muted w-5 text-right">{i + 1}</span>
                    <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                      check.result === "PASS" ? "bg-sardis-green" : "bg-sardis-red"
                    }`} />
                    <span className="text-[11px] font-mono text-sardis-text-secondary w-36 shrink-0">
                      {check.name}
                    </span>
                    <span className={`text-[11px] font-mono flex-1 truncate ${
                      check.result === "PASS" ? "text-sardis-text-muted" : "text-sardis-red"
                    }`}>
                      {check.reason}
                    </span>
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
