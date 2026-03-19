import { useState, useCallback } from "react";

function truncateAddress(address: string): string {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function isValidAddress(addr: string): boolean {
  return /^0x[a-fA-F0-9]{40}$/.test(addr);
}

interface WalletBarProps {
  onAddressChange: (address: string | null) => void;
  currentAddress: string | null;
}

export function WalletBar({ onAddressChange, currentAddress }: WalletBarProps) {
  const [input, setInput] = useState("");
  const [showFull, setShowFull] = useState(false);
  const [error, setError] = useState("");

  const handleConnect = useCallback(() => {
    const addr = input.trim();
    if (!addr) {
      setError("Enter a wallet address");
      return;
    }
    if (!isValidAddress(addr)) {
      setError("Invalid address — must be 0x followed by 40 hex characters");
      return;
    }
    setError("");
    onAddressChange(addr);
  }, [input, onAddressChange]);

  const handleDisconnect = useCallback(() => {
    setInput("");
    setError("");
    onAddressChange(null);
  }, [onAddressChange]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") handleConnect();
    },
    [handleConnect]
  );

  if (currentAddress) {
    return (
      <div className="border-b border-border bg-sardis-surface px-5 py-2.5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-sardis-amber/8 border border-sardis-amber/20">
            <span className="w-2 h-2 rounded-full bg-sardis-amber" />
            <span className="text-[10px] font-medium text-sardis-text-muted uppercase tracking-wider mr-1">
              Wallet
            </span>
            <button
              onClick={() => setShowFull(!showFull)}
              className="font-mono text-xs text-sardis-amber font-medium hover:text-sardis-amber/80 transition-colors"
              title="Click to toggle full address"
            >
              {showFull ? currentAddress : truncateAddress(currentAddress)}
            </button>
          </div>
          <span className="text-[10px] text-sardis-text-muted">
            Showing data for this wallet only
          </span>
        </div>
        <button
          onClick={handleDisconnect}
          className="text-[11px] font-mono text-sardis-text-muted hover:text-sardis-red transition-colors px-2 py-1 rounded hover:bg-sardis-red/5"
        >
          Disconnect
        </button>
      </div>
    );
  }

  return (
    <div className="border-b border-border bg-sardis-surface px-5 py-2.5 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3 flex-1">
        <span className="text-[10px] font-medium text-sardis-text-muted uppercase tracking-wider shrink-0">
          Wallet
        </span>
        <input
          type="text"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            setError("");
          }}
          onKeyDown={handleKeyDown}
          placeholder="0x... enter your Tempo wallet address"
          className="flex-1 max-w-md px-3 py-1.5 rounded-md text-xs font-mono bg-sardis-bg border border-border text-sardis-text-primary placeholder:text-sardis-text-muted/40 focus:border-sardis-amber/50 focus:outline-none transition-colors"
        />
        <button
          onClick={handleConnect}
          className="px-3 py-1.5 rounded-md text-[11px] font-mono font-medium bg-sardis-amber text-sardis-bg hover:bg-sardis-amber/90 transition-colors shrink-0"
        >
          Connect
        </button>
        {error && (
          <span className="text-[10px] text-sardis-red shrink-0">{error}</span>
        )}
      </div>
      <span className="text-[10px] text-sardis-text-muted ml-3 shrink-0">
        Or view all data without connecting
      </span>
    </div>
  );
}
