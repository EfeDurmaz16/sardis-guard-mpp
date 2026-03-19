import { useState, useMemo } from "react";
import { Sidebar } from "./components/Sidebar";
import { WalletBar } from "./components/WalletBar";
import { OverviewView } from "./components/views/OverviewView";
import { FeedView } from "./components/views/FeedView";
import { PolicyView } from "./components/views/PolicyView";
import { MandatesView } from "./components/views/MandatesView";
import { ScreeningView } from "./components/views/ScreeningView";
import { AuditView } from "./components/views/AuditView";
import { KillSwitchView } from "./components/views/KillSwitchView";
import { useEventStream } from "./hooks/useEventStream";
import { useApi } from "./hooks/useApi";
import { useWallet } from "./hooks/useWallet";
import type { ViewId } from "./types";

function App() {
  const [activeView, setActiveView] = useState<ViewId>("overview");
  const { events, riskData, stats, connected } = useEventStream();
  const {
    health,
    summary,
    serviceInfo,
    mandates,
    killSwitches,
    screenEntity,
    screenAddress,
    createMandate,
    delegateMandate,
    freezeMandate,
    resumeMandate,
    activateKillSwitch,
    deactivateKillSwitch,
  } = useApi();

  const { address: walletAddress } = useWallet();

  // Filter events by connected wallet address (match against agent field which may be a wallet address)
  const filteredEvents = useMemo(() => {
    if (!walletAddress) return events;
    const addr = walletAddress.toLowerCase();
    return events.filter((e) => {
      const agent = (e.agent || e.agent_id || "").toLowerCase();
      return agent === addr || agent.includes(addr.slice(2)); // match with or without 0x prefix
    });
  }, [events, walletAddress]);

  // Filter risk data by wallet address
  const filteredRiskData = useMemo(() => {
    if (!walletAddress) return riskData;
    const addr = walletAddress.toLowerCase();
    return riskData.filter((r) => {
      const agent = (r.agent || "").toLowerCase();
      return agent === addr || agent.includes(addr.slice(2));
    });
  }, [riskData, walletAddress]);

  // Filter mandates by principal_id matching wallet address
  const filteredMandates = useMemo(() => {
    if (!walletAddress) return mandates;
    const addr = walletAddress.toLowerCase();
    return mandates.filter((m) => {
      return (
        m.principal_id.toLowerCase() === addr ||
        m.principal_id.toLowerCase().includes(addr.slice(2)) ||
        m.agent_id.toLowerCase() === addr ||
        m.agent_id.toLowerCase().includes(addr.slice(2))
      );
    });
  }, [mandates, walletAddress]);

  // Merge SSE stats with API stats
  const mergedStats = {
    ...stats,
    agentsTracked: summary?.active_agents ?? health?.agents_tracked ?? stats.agentsTracked,
    activeMandates: summary?.mandates_active ?? health?.mandates_active ?? stats.activeMandates,
    frozenMandates: summary?.mandates_frozen ?? stats.frozenMandates,
    totalVolume: summary?.total_volume ?? stats.totalVolume,
    uniqueMerchants: summary?.unique_merchants ?? stats.uniqueMerchants,
  };

  return (
    <div className="h-screen flex bg-sardis-bg overflow-hidden">
      <Sidebar
        activeView={activeView}
        onNavigate={setActiveView}
        connected={connected}
      />

      <div className="flex-1 min-w-0 overflow-hidden flex flex-col">
        <WalletBar />

        <main className="flex-1 min-h-0 overflow-hidden">
          {activeView === "overview" && (
            <OverviewView
              summary={summary}
              stats={mergedStats}
              serviceInfo={serviceInfo}
              killSwitches={killSwitches}
              events={filteredEvents}
              riskData={filteredRiskData}
              connected={connected}
            />
          )}
          {activeView === "feed" && (
            <FeedView events={filteredEvents} connected={connected} />
          )}
          {activeView === "policy" && (
            <PolicyView />
          )}
          {activeView === "mandates" && (
            <MandatesView
              mandates={filteredMandates}
              onFreeze={freezeMandate}
              onResume={resumeMandate}
              onCreateMandate={createMandate}
              onDelegateMandate={delegateMandate}
            />
          )}
          {activeView === "screening" && (
            <ScreeningView
              onScreenEntity={screenEntity}
              onScreenAddress={screenAddress}
            />
          )}
          {activeView === "killswitch" && (
            <KillSwitchView
              killSwitches={killSwitches}
              onActivate={activateKillSwitch}
              onDeactivate={deactivateKillSwitch}
            />
          )}
          {activeView === "audit" && (
            <AuditView events={filteredEvents} />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
