import { useState } from "react";
import { useWallet } from "../hooks/useWallet";

function truncateAddress(address: string): string {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

export function WalletBar() {
  const { address, isConnected, signUp, signIn, signOut } = useWallet();
  const [showFull, setShowFull] = useState(false);

  if (isConnected && address) {
    return (
      <div className="border-b border-border bg-sardis-surface px-5 py-2.5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-sardis-amber/8 border border-sardis-amber/20">
            <span className="w-2 h-2 rounded-full bg-sardis-amber" />
            <span className="text-[10px] font-medium text-sardis-text-muted uppercase tracking-wider mr-1">
              Tempo Wallet
            </span>
            <button
              onClick={() => setShowFull(!showFull)}
              className="font-mono text-xs text-sardis-amber font-medium hover:text-sardis-amber/80 transition-colors"
              title="Click to toggle full address"
            >
              {showFull ? address : truncateAddress(address)}
            </button>
          </div>
        </div>
        <button
          onClick={signOut}
          className="text-[11px] font-mono text-sardis-text-muted hover:text-sardis-red transition-colors px-2 py-1 rounded hover:bg-sardis-red/5"
        >
          Sign out
        </button>
      </div>
    );
  }

  return (
    <div className="border-b border-border bg-sardis-surface px-5 py-2.5 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-medium text-sardis-text-muted uppercase tracking-wider">
          Tempo Wallet
        </span>
        <span className="text-[11px] text-sardis-text-muted">
          Sign in with your passkey to filter data by your wallet
        </span>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={signUp}
          className="px-3 py-1 rounded-md text-[11px] font-mono font-medium bg-sardis-amber text-sardis-bg hover:bg-sardis-amber/90 transition-colors"
        >
          Sign up
        </button>
        <button
          onClick={signIn}
          className="px-3 py-1 rounded-md text-[11px] font-mono font-medium border border-sardis-amber/30 text-sardis-amber hover:bg-sardis-amber/10 transition-colors"
        >
          Sign in
        </button>
      </div>
    </div>
  );
}
