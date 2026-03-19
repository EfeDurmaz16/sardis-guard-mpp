import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { ScreeningResult } from "../../types";

interface ScreeningViewProps {
  onScreenEntity: (name: string) => Promise<ScreeningResult | null>;
  onScreenAddress: (address: string) => Promise<ScreeningResult | null>;
}

interface ScreeningEntry {
  query: string;
  type: "entity" | "address";
  result: ScreeningResult;
  timestamp: number;
}

const EXAMPLE_ADDRESSES = [
  {
    label: "Tornado Cash (sanctioned)",
    address: "0x8589427373D6D84E98730D7795D8f6f8731FDA16",
    expected: "HIT",
  },
  {
    label: "Clean address",
    address: "0x742d35Cc6634C0532925a3b844Bc9e7595F8fE00",
    expected: "CLEAN",
  },
];

const EXAMPLE_ENTITIES = [
  { label: "Tornado Cash", name: "Tornado Cash", expected: "HIT" },
  { label: "Lazarus Group", name: "Lazarus Group", expected: "HIT" },
  { label: "Perplexity AI (clean)", name: "Perplexity AI", expected: "CLEAN" },
];

export function ScreeningView({ onScreenEntity, onScreenAddress }: ScreeningViewProps) {
  const [entityQuery, setEntityQuery] = useState("");
  const [addressQuery, setAddressQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<ScreeningEntry[]>([]);

  const handleEntityScreen = async (name?: string) => {
    const query = name || entityQuery.trim();
    if (!query) return;
    setLoading(true);
    setError(null);
    try {
      const result = await onScreenEntity(query);
      if (result) {
        setHistory((prev) => [
          { query, type: "entity", result, timestamp: Date.now() / 1000 },
          ...prev,
        ]);
        if (!name) setEntityQuery("");
      } else {
        setError("No response from server");
      }
    } catch {
      setError("Failed to connect to screening service");
    }
    setLoading(false);
  };

  const handleAddressScreen = async (addr?: string) => {
    const query = addr || addressQuery.trim();
    if (!query) return;
    setLoading(true);
    setError(null);
    try {
      const result = await onScreenAddress(query);
      if (result) {
        setHistory((prev) => [
          { query, type: "address", result, timestamp: Date.now() / 1000 },
          ...prev,
        ]);
        if (!addr) setAddressQuery("");
      } else {
        setError("No response from server");
      }
    } catch {
      setError("Failed to connect to screening service");
    }
    setLoading(false);
  };

  return (
    <div className="h-full flex flex-col p-5 gap-4 fade-in">
      <div>
        <h1 className="text-lg font-semibold text-sardis-text tracking-tight">Screening</h1>
        <p className="text-xs text-sardis-text-muted">OFAC sanctions screening for entities and wallet addresses</p>
      </div>

      {error && (
        <div className="rounded-lg border border-sardis-red/30 bg-sardis-red-glow px-4 py-2.5 text-[11px] font-mono text-sardis-red flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-sardis-red/60 hover:text-sardis-red ml-3">
            dismiss
          </button>
        </div>
      )}

      <div className="flex-1 grid grid-cols-2 gap-4 min-h-0">
        {/* Left: Input + Examples */}
        <div className="flex flex-col gap-4 min-h-0 overflow-y-auto">
          <Card className="bg-sardis-surface border-border">
            <Tabs defaultValue="entity">
              <CardHeader className="py-0 px-4 border-b border-border">
                <TabsList className="bg-transparent border-0 h-10 gap-4">
                  <TabsTrigger
                    value="entity"
                    className="text-[11px] font-mono data-[state=active]:text-sardis-amber data-[state=active]:border-b-2 data-[state=active]:border-sardis-amber rounded-none bg-transparent px-0 pb-2.5 pt-3"
                  >
                    Entity
                  </TabsTrigger>
                  <TabsTrigger
                    value="address"
                    className="text-[11px] font-mono data-[state=active]:text-sardis-amber data-[state=active]:border-b-2 data-[state=active]:border-sardis-amber rounded-none bg-transparent px-0 pb-2.5 pt-3"
                  >
                    Address
                  </TabsTrigger>
                </TabsList>
              </CardHeader>
              <CardContent className="p-4">
                <TabsContent value="entity" className="mt-0 space-y-3">
                  <p className="text-[11px] text-sardis-text-muted">
                    Screen a name or organization against OFAC SDN list
                  </p>
                  <div className="flex gap-2">
                    <Input
                      value={entityQuery}
                      onChange={(e) => setEntityQuery(e.target.value)}
                      placeholder="e.g. Tornado Cash"
                      className="font-mono text-sm bg-sardis-surface-2 border-border"
                      onKeyDown={(e) => e.key === "Enter" && handleEntityScreen()}
                      disabled={loading}
                    />
                    <Button
                      onClick={() => handleEntityScreen()}
                      disabled={loading || !entityQuery.trim()}
                      className="bg-sardis-amber text-sardis-bg hover:bg-sardis-amber/90 font-mono text-xs shrink-0"
                    >
                      {loading ? "Screening..." : "Screen"}
                    </Button>
                  </div>

                  {/* Try these examples */}
                  <div className="pt-2 border-t border-border">
                    <p className="text-[10px] font-medium text-sardis-text-muted uppercase tracking-wider mb-2">
                      Try these
                    </p>
                    <div className="space-y-1.5">
                      {EXAMPLE_ENTITIES.map((ex) => (
                        <button
                          key={ex.name}
                          onClick={() => handleEntityScreen(ex.name)}
                          disabled={loading}
                          className="w-full flex items-center justify-between rounded-md border border-border bg-sardis-surface-2 px-3 py-2 text-left transition-colors hover:border-sardis-amber/30 hover:bg-sardis-surface-3 disabled:opacity-50"
                        >
                          <span className="text-[11px] font-mono text-sardis-text-secondary">
                            {ex.label}
                          </span>
                          <Badge
                            variant="outline"
                            className={`text-[9px] font-mono font-bold px-1.5 py-0 ${
                              ex.expected === "HIT"
                                ? "border-sardis-red/30 text-sardis-red"
                                : "border-sardis-green/30 text-sardis-green"
                            }`}
                          >
                            {ex.expected}
                          </Badge>
                        </button>
                      ))}
                    </div>
                  </div>
                </TabsContent>
                <TabsContent value="address" className="mt-0 space-y-3">
                  <p className="text-[11px] text-sardis-text-muted">
                    Screen a wallet address against OFAC sanctioned addresses
                  </p>
                  <div className="flex gap-2">
                    <Input
                      value={addressQuery}
                      onChange={(e) => setAddressQuery(e.target.value)}
                      placeholder="0x..."
                      className="font-mono text-sm bg-sardis-surface-2 border-border"
                      onKeyDown={(e) => e.key === "Enter" && handleAddressScreen()}
                      disabled={loading}
                    />
                    <Button
                      onClick={() => handleAddressScreen()}
                      disabled={loading || !addressQuery.trim()}
                      className="bg-sardis-amber text-sardis-bg hover:bg-sardis-amber/90 font-mono text-xs shrink-0"
                    >
                      {loading ? "Screening..." : "Screen"}
                    </Button>
                  </div>

                  {/* Try these examples */}
                  <div className="pt-2 border-t border-border">
                    <p className="text-[10px] font-medium text-sardis-text-muted uppercase tracking-wider mb-2">
                      Try these
                    </p>
                    <div className="space-y-1.5">
                      {EXAMPLE_ADDRESSES.map((ex) => (
                        <button
                          key={ex.address}
                          onClick={() => handleAddressScreen(ex.address)}
                          disabled={loading}
                          className="w-full flex items-center justify-between rounded-md border border-border bg-sardis-surface-2 px-3 py-2 text-left transition-colors hover:border-sardis-amber/30 hover:bg-sardis-surface-3 disabled:opacity-50"
                        >
                          <div className="min-w-0 flex-1 mr-3">
                            <span className="text-[11px] text-sardis-text-secondary block">
                              {ex.label}
                            </span>
                            <span className="text-[9px] font-mono text-sardis-text-muted block truncate">
                              {ex.address}
                            </span>
                          </div>
                          <Badge
                            variant="outline"
                            className={`text-[9px] font-mono font-bold px-1.5 py-0 shrink-0 ${
                              ex.expected === "HIT"
                                ? "border-sardis-red/30 text-sardis-red"
                                : "border-sardis-green/30 text-sardis-green"
                            }`}
                          >
                            {ex.expected}
                          </Badge>
                        </button>
                      ))}
                    </div>
                  </div>
                </TabsContent>
              </CardContent>
            </Tabs>
          </Card>

          {/* Latest result card */}
          {history.length > 0 && (
            <Card className={`bg-sardis-surface border-border ${history[0].result.hit ? "glow-alert border-sardis-red/30" : ""}`}>
              <CardHeader className="py-3 px-4 border-b border-border">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xs font-medium text-sardis-text-secondary">Latest Result</CardTitle>
                  <Badge
                    variant="outline"
                    className={`text-[10px] font-mono font-bold ${
                      history[0].result.hit
                        ? "border-sardis-red/30 text-sardis-red bg-sardis-red-glow"
                        : "border-sardis-green/30 text-sardis-green bg-sardis-green-glow"
                    }`}
                  >
                    {history[0].result.hit ? "SANCTIONED" : "CLEAR"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-4 space-y-2">
                <DetailRow label="Query" value={history[0].query} mono />
                <DetailRow label="Type" value={history[0].type} />
                {history[0].result.hit ? (
                  <>
                    <Separator className="bg-border" />
                    <DetailRow label="Match Type" value={history[0].result.match_type} />
                    <DetailRow label="Matched" value={history[0].result.matched_entry} color="text-sardis-red" />
                    <DetailRow label="Source" value={history[0].result.list_source} />
                    <DetailRow label="Confidence" value={history[0].result.confidence.toFixed(3)} />
                  </>
                ) : (
                  <>
                    <Separator className="bg-border" />
                    <div className="flex items-center gap-2 py-1">
                      <span className="w-2 h-2 rounded-full bg-sardis-green" />
                      <span className="text-[11px] text-sardis-green font-mono">
                        No sanctions match found
                      </span>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right: History */}
        <Card className="bg-sardis-surface border-border min-h-0">
          <CardHeader className="py-3 px-4 border-b border-border">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-medium text-sardis-text-secondary">Screening History</CardTitle>
              <span className="text-[10px] font-mono text-sardis-text-muted">{history.length} checks</span>
            </div>
          </CardHeader>
          <CardContent className="p-0 overflow-y-auto h-[calc(100%-44px)]">
            {history.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 text-sardis-text-muted">
                <p className="text-xs">No screenings yet</p>
                <p className="text-[10px] text-sardis-text-faint mt-1">
                  Use the form or click an example to get started
                </p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {history.map((entry, i) => (
                  <div key={i} className="px-4 py-3 hover:bg-sardis-surface-2/40 transition-colors">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-mono text-sardis-text-secondary truncate max-w-48">
                        {entry.query}
                      </span>
                      <Badge
                        variant="outline"
                        className={`text-[9px] font-mono font-bold px-1.5 py-0 ${
                          entry.result.hit
                            ? "border-sardis-red/30 text-sardis-red"
                            : "border-sardis-green/30 text-sardis-green"
                        }`}
                      >
                        {entry.result.hit ? "HIT" : "CLEAR"}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-[10px] text-sardis-text-muted font-mono">
                      <span>{entry.type}</span>
                      {entry.result.hit && (
                        <>
                          <span>/</span>
                          <span className="text-sardis-red">{entry.result.matched_entry}</span>
                        </>
                      )}
                    </div>
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
